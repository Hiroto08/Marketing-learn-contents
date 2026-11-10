#!/usr/bin/env python3
"""
check_readings.py — ナレーションの読みを、固有名詞の台帳（docs/proper-nouns.md）と突き合わせる。

run_episode.sh / run_shorts.sh が、ビルドの前（原稿の検査）と後（音声の照合）に呼ぶ。FAIL ならビルドも公開も進めない。

    python3 _tools/checks/check_readings.py <dir>            # ビルド前：原稿を VOICEVOX に読ませて検査
    python3 _tools/checks/check_readings.py <dir> --built    # ビルド後：実際に音声になった読み（built_readings.json）で照合
    python3 _tools/checks/check_readings.py <dir> --review   # 全文の読みを <dir>/reading_review.txt に書き出す（作業用）
    python3 _tools/checks/check_readings.py <dir> --json     # 結果を JSON で標準出力（quality_record.py 用）
    <dir> は回のフォルダ（本編＋その回の Shorts）か、shorts_build/shortN（その1本）。--main を付けると本編だけ。

検査項目（番号は quality-gates.md の R1〜R8 と同じ）:
  R1 固有名詞の網羅：原稿の固有名詞（形態素解析の「固有名詞」＋辞書に無いカタカナ語・英字）が、すべて台帳か
     一般語リスト（_tools/checks/reading_allowlist.txt）にある。無ければ FAIL（台帳に足すか、名前を使わない表現にする）。
  R2 確認ソース：使っている台帳の行に確認日がある（proper_nouns.py --verify が、ソースのページで読みを確かめた日）。
     人名・企業・団体・商品・媒体で確認日が空なら FAIL。
  R3 辞書登録：人名は make_video.py の COMPOUND_DICT に登録されている（漢字の名前は読みが何通りもあるため）。
  R4 読みの一致：台帳の表記が出る文で、音声の読みに台帳の読みが入っている。違えば FAIL（例：森岡毅＝モリオカアツシ）。
  R5 区切れ：カタカナ語が文の中で2つのアクセント句に割れていない（例：ノース／ウェスタン）。
  R6 数字：西暦は4桁で読む（下2桁読みは FAIL）。①②③ は「ひとつめ・ふたつめ・みっつめ」。
  R7 英字：英字の語は ABBR_MAP（読みの指定）か台帳にある。無ければ FAIL（VOICEVOX まかせにしない）。
  R8 既知の誤読：過去に起きた誤読の型（BAD）に当たらない。新しい誤読を見つけたら BAD に足す。
  R10 読みの食い違い：別の辞書（形態素解析 janome）の読みと VOICEVOX の読みが違う語が、確認済みリスト
     （_tools/checks/reading_confirmed.txt）にある。無ければ FAIL。読みを確かめ、正しければリストに足し、
     間違っていれば辞書（COMPOUND_DICT／READING_MAP）で直す。未知の誤読（例：行＝くだり、埋まらない＝うずまらない）を拾うための網。
  --built のときは加えて
  R9 音声が今の原稿のものである：built_readings.json の文が、今のナレーションの文と1文ずつ一致する。
"""
import glob
import json
import os
import re
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "video"))
sys.path.insert(0, HERE)
import make_video as M  # noqa: E402
import proper_nouns as P  # noqa: E402

URL = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
SPEAKER = 11

# 過去に実際に起きた誤読（本文の型, 読みに出たらだめな文字列, 説明）
BAD = [
    (r"異を", "コトオ", "異（い）を"),
    (r"直し(かた|方)", "チョクシ", "直（なお）しかた"),
    (r"人がい", "ジンガイ", "人（ひと）がい…"),
    (r"今[ァ-ヶ]", "コン", "今（いま）＋カタカナ語"),
    (r"並べ", "ナベ", "並（なら）べ"),
    (r"シー", "スィ", "シー"),
    (r"当てはめ", "アテワメ", "当（あ）てはめ"),
    (r"何(でしょう|です|の|だっ|なの)", "ナニ(デショ|デス|ノ|ダッ|ナノ)", "何（なん）でしょう・何の"),
    (r"①", "イチツメ", "①＝ひとつめ"),
    (r"TOP\s*5|トップ5", "トップゴ", "TOP5＝トップファイブ"),
    # ── 公開済み EP01〜22 の音声を再現して見つけた型（差し替えはしない。今後のための記録。2026-11-10）──
    (r"仕掛け人", "シカケジン", "仕掛け人（しかけにん）"),
    (r"高品質", "タカシナ", "高品質（こうひんしつ）が人名読みになる"),
    (r"(?<![一-龥])行(?![一-龥っきくけこいうえ])", "クダリ|ナイユキ", "行（ぎょう）。辞書では直らない。ナレーションは「ぎょう」とかなで書くか「欄」に言い換える"),
    (r"埋まら", "ウズマラ", "埋（う）まらない"),
    (r"一光", "カズミツ", "田中一光（いっこう）"),
    (r"生の声", "セエノコエ", "生（なま）の声"),
    (r"細けれ", "コマカケレ", "細（ほそ）ければ"),
    (r"前と後", "ゼント", "前（まえ）と後（あと）"),
]
KATA_RE = re.compile(r"[ァ-ヶー]{4,}")
LATIN_RE = re.compile(r"[A-Za-z][A-Za-z0-9&'.]*")
YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})年")


def kana(text):
    q = urllib.parse.urlencode({"text": text, "speaker": SPEAKER})
    r = json.load(urllib.request.urlopen(urllib.request.Request(f"{URL}/audio_query?{q}", method="POST"), timeout=30))
    return ["".join(m["text"] for m in ap["moras"]) for ap in r["accent_phrases"]]


def sources(d, main_only=False):
    """<回のフォルダ>（本編＋その回の Shorts）か、<shorts_build/shortN>（その1本だけ）。main_only=True なら本編だけ"""
    d = d.rstrip("/")
    if os.path.exists(f"{d}/stage.html"):
        return [f"{d}/stage.html"]
    cand = [f"{d}/slide.html"] + ([] if main_only else sorted(glob.glob(f"{d}/shorts_build/short*/stage.html")))
    return [p for p in cand if os.path.exists(p)]


def narr_sentences(path):
    out = []
    for n in M.extract_slide_data(path).narrations:
        out += [s for s in M.split_sentences(n.replace("\n", " ")) if M.clean_for_tts(s)]
    return out


def built_path(src):
    """slide.html → video_build/out/built_readings.json、stage.html → 同じフォルダ"""
    d = os.path.dirname(src)
    return f"{d}/video_build/out/built_readings.json" if src.endswith("slide.html") else f"{d}/built_readings.json"


_TOK = None


def confirmed():
    """確認済みの読み {表記: {読み（照合用）}}"""
    p = os.path.join(HERE, "reading_confirmed.txt")
    out = {}
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if line.strip() and not line.startswith("#") and "\t" in line:
                a, b = line.rstrip("\n").split("\t")[:2]
                out.setdefault(a, set()).update({P.norm_kana(b), P.norm_kana(b, merge=True)})
    return out


def _jread(clean):
    """janome の読み（トークンごと）→ [(表記, {読みの候補}) | (表記, None)]。数字・助数詞・記号・読み不明は照合しない"""
    global _TOK
    if _TOK is None:
        from janome.tokenizer import Tokenizer
        _TOK = Tokenizer()
    out, prev_num = [], False
    for t in _TOK.tokenize(clean):
        pos, r, surf = t.part_of_speech, t.reading, t.surface
        isnum = bool(re.fullmatch(r"[\d,.%０-９]+", surf)) or "名詞,数" in pos
        if isnum or pos.startswith("記号") or "助数詞" in pos or prev_num:
            out.append((surf, None))
            prev_num = isnum
            continue
        prev_num = False
        if r == "*":
            r = surf if re.fullmatch(r"[ァ-ヶーぁ-ゖ]+", surf) else None
        if not r:
            out.append((surf, None))
            continue
        c = {P.norm_kana(r), P.norm_kana(r, merge=True)}
        if pos.startswith("助詞") and surf.endswith("は"):
            c |= {x[:-1] + "ワ" for x in list(c)}
        if pos.startswith("助詞") and surf == "へ":
            c.add("エ")
        if surf in ("う", "よう", "ましょう", "でしょう", "だろう"):
            c |= {x[:-1] + "オ" for x in list(c)}
        if surf in ("実は", "それでは", "では", "には", "とは", "のは", "ては", "または", "あるいは", "まずは", "かたは"):
            c |= {x[:-1] + "ワ" for x in list(c)}
        out.append((surf, c))
    return out


def cross_check(sent, k):
    """[(表記, 別辞書の読み, VOICEVOX の読み)]：2つの辞書で読みが食い違う語"""
    eng = P.norm_kana("".join(k))
    toks = _jread(M.clean_for_tts(sent))
    pos, bad = 0, []

    def seek(i):
        nxt = next((x for _, x in toks[i + 1:] if x), None)
        js = [j for j in (eng.find(v, pos) for v in (nxt or ())) if j >= 0]
        return min(js) if js else None
    loose = False                 # 直前が数字など（照合しない語）なら、位置の制限をゆるめる
    for i, (surf, c) in enumerate(toks):
        if c is None:
            j = seek(i)
            pos = j if j is not None else pos
            loose = True
            continue
        if loose and max(len(v) for v in c) <= 1:
            continue              # 数字の直後の1文字の語（に・は・を）は位置が定まらないので照合しない
        hit = [(j, v) for j, v in ((eng.find(v, pos), v) for v in c) if j >= pos and (loose or j - pos <= 4)]
        loose = False
        if hit:
            j, v = min(hit)
            pos = j + len(v)
            continue
        j = seek(i)
        got = eng[pos:j] if j is not None and j > pos else eng[pos:pos + len(sorted(c)[0]) + 2]
        bad.append((surf, sorted(c)[0], got))
        pos = j if j is not None else pos
    return bad


def candidates(text):
    """固有名詞らしい語（形態素解析の固有名詞／辞書に無いカタカナ語・英字）"""
    global _TOK
    if _TOK is None:
        from janome.tokenizer import Tokenizer
        _TOK = Tokenizer()
    out = []
    for tk in _TOK.tokenize(text):
        s, pos = tk.surface, tk.part_of_speech
        if len(s) < 2:
            continue
        if "固有名詞" in pos:
            out.append(s)
        elif tk.node_type == "UNKNOWN" and re.fullmatch(r"[ァ-ヶー]{2,}|[A-Za-z][A-Za-z0-9&'.]*", s):
            out.append(s)
    return out


def check(d, built=False, review=False, main_only=False):
    srcs = sources(d, main_only)
    if not srcs:
        sys.exit(f"{d}: ナレーションが見つからない（slide.html / shorts_build/short*/stage.html）")
    ledger, allow = P.load(), P.allowlist()
    forms = [(f, r) for r in ledger for f in r["forms"]]
    forms.sort(key=lambda x: -len(x[0]))
    abbr = set(M.ABBR_MAP)
    if not built:
        M.seed_user_dict(URL)
    F = {k: [] for k in ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10")}
    conf = confirmed()
    used, lines, nsent = {}, [], 0

    for src in srcs:
        sents = narr_sentences(src)
        if built:
            bp = built_path(src)
            if not os.path.exists(bp):
                F["R9"].append(f"{bp} が無い（この版の make_video でビルドし直す）")
                continue
            got = [x for sl in json.load(open(bp, encoding="utf-8"))["slides"] for x in sl["sentences"]]
            if [g["text"] for g in got] != sents:
                F["R9"].append(f"{os.path.relpath(bp)}: 音声の文（{len(got)}文）が今のナレーション（{len(sents)}文）と一致しない → ビルドし直す")
                continue
            pairs = [(g["text"], g["kana"]) for g in got]
        else:
            pairs = [(s, kana(M.clean_for_tts(s))) for s in sents]
        nsent += len(pairs)

        for s, k in pairs:
            flat, nflat = "".join(k), "".join(P.norm_kana(ap) for ap in k)
            star = ""
            # R1 網羅
            for c in candidates(s):
                if c in allow or any(c in a for a in abbr) or any(c in f for f, _ in forms):
                    continue
                F["R1"].append(f"「{c}」が台帳（docs/proper-nouns.md）にも一般語リストにも無い")
            # R4 読みの一致（長い表記から。同じ位置を短い表記で二重に数えない）
            rest = s
            for f, r in forms:
                if f not in rest:
                    continue
                rest = rest.replace(f, "＿")
                star = "★"
                used[r["表記"]] = r
                if not any(w in nflat for w in P.reading_variants(r["読み"])):
                    F["R4"].append(f"「{f}」の読みが台帳（{r['読み']}）と違う：{'/'.join(k)}（{s[:28]}…）")
            # R5 区切れ
            clean = M.clean_for_tts(s)
            for m in KATA_RE.finditer(clean):
                w = P.norm_kana(m[0])
                if w in nflat and not any(w in P.norm_kana(ap) for ap in k):
                    F["R5"].append(f"「{m[0]}」が途中で切れて読まれる：{'/'.join(k)}（COMPOUND_DICT に1語で登録）")
            # R6 数字
            for m in YEAR_RE.finditer(s):
                head = "セン" if m[1].startswith("19") else "ニセン"
                if head not in flat:
                    F["R6"].append(f"西暦「{m[1]}年」が4桁で読まれていない：{'/'.join(k)}")
            # R7 英字
            for m in LATIN_RE.finditer(s):
                w = m[0].rstrip(".")
                if len(w) >= 2 and w not in abbr and not any(w in f for f, _ in forms) and w not in allow:
                    F["R7"].append(f"英字「{w}」の読みが決まっていない（ABBR_MAP か台帳に登録）：{s[:28]}…")
            # R8 既知の誤読
            for pat, bad, label in BAD:
                if re.search(pat, s) and re.search(bad, flat):
                    F["R8"].append(f"誤読：{label} → {'/'.join(k)}（{s[:28]}…）")
            # R10 読みの食い違い（別辞書との照合）
            for surf, jr, got in cross_check(s, k):
                if got and any(x and x in got for x in conf.get(surf, ())):
                    continue
                if any(surf in f for f, _ in forms) or surf in M.COMPOUND_DICT:
                    continue      # 台帳・辞書で読みを決めてある語
                F["R10"].append(f"「{surf}」：別の辞書は {jr}、VOICEVOX は {got or '（対応なし）'}（{s[:22]}…）→ 読みを確かめて reading_confirmed.txt に足すか、辞書で直す")
            lines.append(f"{star}{s}\n    → {'/'.join(k)}")

    # R2 確認ソース・R3 辞書登録
    for name, r in used.items():
        if P.needs_url(r["種別"]) and not r["確認日"]:
            F["R2"].append(f"「{name}」の確認日が無い（proper_nouns.py --verify で確認ソースを確かめる）")
        if r["種別"].startswith("人名") and not any(f in M.COMPOUND_DICT or any(f in k for k in M.COMPOUND_DICT) for f in r["forms"]):
            if re.search(r"[一-龥]", name):
                F["R3"].append(f"人名「{name}」が COMPOUND_DICT に未登録")

    F = {k: sorted(set(v)) for k, v in F.items()}
    nfail = sum(len(v) for v in F.values())
    res = {"dir": d.rstrip("/"), "mode": "built" if built else "script", "sentences": nsent, "fails": F, "pass": nfail == 0,
           "nouns": [{"表記": r["表記"], "読み": r["読み"], "種別": r["種別"], "確認ソース": r["確認ソース"],
                      "確認日": r["確認日"]} for r in used.values()]}
    if review:
        p = f"{d.rstrip('/')}/reading_review.txt"
        open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return res


def report(res):
    mode = "ビルド後・音声の読み" if res["mode"] == "built" else "ビルド前・原稿"
    print(f"── 読み検査（{mode}）：{res['dir']}  {res['sentences']}文・固有名詞 {len(res['nouns'])}件 ──")
    names = {"R1": "固有名詞の網羅", "R2": "確認ソース", "R3": "辞書登録", "R4": "読みの一致", "R5": "区切れ",
             "R6": "数字の読み", "R7": "英字の読み", "R8": "既知の誤読", "R9": "音声と原稿の一致", "R10": "読みの食い違い"}
    for k, v in res["fails"].items():
        if res["mode"] != "built" and k == "R9":
            continue
        if v:
            for x in v:
                print(f"  ✗ {k} {names[k]}：{x}")
        else:
            print(f"  ✓ {k} {names[k]}")
    print("RESULT: PASS" if res["pass"] else f"RESULT: FAIL（{sum(len(v) for v in res['fails'].values())}件）")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    ok = True
    out = []
    for a in args:
        r = check(a, built="--built" in sys.argv, review="--review" in sys.argv, main_only="--main" in sys.argv)
        out.append(r)
        ok = ok and r["pass"]
        if "--json" not in sys.argv:
            report(r)
    if "--json" in sys.argv:
        print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if ok else 1)
