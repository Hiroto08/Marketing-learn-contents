#!/usr/bin/env python3
"""
check_style.py — 「AI が書いた／読んだ」と見抜かれる要素を、台本とテロップから機械で判定する（Issue #2 依頼4・2026-11-10）。

    python3 _tools/checks/check_style.py <回のフォルダ | shorts_build/shortN>      # 合否を表示
    python3 _tools/checks/check_style.py <dir> --json                               # quality_record.py 用
    python3 _tools/checks/check_style.py <dir> --strict                             # 旧基準の回も新基準で判定する（試行・見直し用）

対象：本編・ケースファイル（slide.html）と Shorts（stage.html）。数字の読み・英字の読み・固有名詞の読みは check_readings.py が見る。
ここで見るのは、文章とテロップ（quality-gates.md の A1〜A7・T1〜T3）。

  A1 語尾の連続      同じ語尾（です／ます／でした／ました／のです…）が4文以上続かない（本編・ケースファイル）
  A2 「のです」       「のです／んです」で終わる文は、全体の10%以下（本編・ケースファイル）
  A3 文頭の接続詞    同じ接続詞（実は・しかし・つまり・では…）で始まる文は、1本で3回まで（Shorts は1回まで）
  A4 回をまたぐ同じ文 過去の回のナレーションと同じ文（10字以上・句読点を除いて一致）を使わない。
                      例外は _tools/checks/style_fixed_lines.txt に書いた1文（チャンネル登録の案内）だけ
  A5 文の長さ        1文は80字以内。文の長さのばらつき（標準偏差÷平均）が0.35以上（長さがそろいすぎない。本編・ケースファイル）
  A6 対比の型        「〜ではなく、〜」は1本で3回まで
  A7 同じ文の繰り返し 1本の中で同じ文（10字以上）は2回まで／定型句（BANNED）は使わない
  T1 表記ゆれ        画面の文字に全角の英数字が無い。長音の有無だけが違う語（ユーザ／ユーザー）が混ざっていない
  T2 画面の数字       画面に出る「数字＋単位」が、その回のナレーションにもある（値で比べる。西暦は対象外）
  T3 画面と音声の文   テロップ同期型の Shorts は verify_shorts の検査10が判定する（ここでは結果を参照しない）

旧基準で作った回（_tools/checks/style_legacy.txt に書いたフォルダ）は、結果を「参考」として表示し、不合格にしない。
新しい回（一覧に無いフォルダ）は、すべて合格するまでビルドしない。
"""
import collections
import glob
import html as htmlmod
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "video"))
import make_video as M  # noqa: E402

ROOT = os.path.join(HERE, "..", "..")
OPENERS = ["実は", "しかし", "つまり", "では", "そこで", "だから", "ところが", "さらに", "ただ", "しかも", "それでも", "そして", "一方"]
BANNED = ["いかがでしたか", "いかがでしょうか", "と言えるでしょう", "ではないでしょうか", "していきましょう", "見ていきましょう",
          "結論から言うと", "意外な事実があります", "数字でおさらいします", "あらためて問います", "さっそく"]
ENDINGS = [(r"(のです|んです)$", "のです"), (r"でしょうか$", "でしょうか"), (r"(ますか|ですか|ませんか)$", "〜か"),
           (r"ません(でした)?$", "ません"), (r"ました$", "ました"), (r"でした$", "でした"), (r"ます$", "ます"), (r"です$", "です"),
           (r"(ください|ましょう)$", "依頼"), (r"だった$", "だった"), (r"[っいしえけれせてべめね]た$", "〜た"), (r"だ$", "だ"),
           (r"ない$", "ない"), (r"[るうくすつぬむぶぐ]$", "動詞")]
UNIT = r"(?:%|％|倍|円|ドル|人|社|店舗|店|本|枚|件|回|割|か月|日間|時間|分|秒|種類|個|位|点|ページ|クリック)"
NUM_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)(兆|億|万)?(?:(\d[\d,]*)(億|万)?)?(\d[\d,]*)?(" + UNIT[3:-1] + ")")
_MUL = {"兆": 1e12, "億": 1e8, "万": 1e4, None: 1}


def numbers(text):
    """文中の「数字＋単位」を (値, 単位) にそろえる（9.85億ドル と 9億8500万ドル を同じ値として比べるため）。年は対象外"""
    t = text.replace(",", "").replace("，", "").replace("％", "%")
    out = {}
    for m in NUM_RE.finditer(t):
        a, u1, b, u2, c, unit = m.groups()
        v = float(a) * _MUL[u1]
        if b:
            v += float(b) * _MUL[u2]
        if c:
            v += float(c)
        out[(round(v, 4), unit)] = m[0]
    return out


def _norm(s):
    return re.sub(r"[、。，．,.！？!?「」『』\s　]", "", s)


def sents_of(path):
    out = []
    for n in M.extract_slide_data(path).narrations:
        out += [s for s in M.split_sentences(n.replace("\n", " ")) if s.strip()]
    return out


def screen_text(path):
    src = open(path, encoding="utf-8").read()
    secs = re.findall(r"<section[^>]*class=\"slide[^\"]*\"[^>]*>(.*?)</section>", src, re.S)
    t = " ".join(secs)
    t = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", t, flags=re.S)
    t = re.sub(r'<div[^>]*class="[^"]*cta-line[^"]*"[^>]*>.*?</div>', " ", t, flags=re.S)   # 次回予告は別の回の話なので対象外
    return htmlmod.unescape(re.sub(r"<[^>]+>", " ", t))


def source_of(d):
    d = d.rstrip("/")
    for p in (f"{d}/stage.html", f"{d}/slide.html"):
        if os.path.exists(p):
            return p
    return None


def is_short(path):
    return path.endswith("stage.html")


def others(path):
    """比べる相手：同じ種類（本編どうし・ケースファイルどうし・Shorts どうし）で、自分以外のナレーション"""
    me = os.path.abspath(path)
    if is_short(path):
        pool = glob.glob(os.path.join(ROOT, "s2_ura/u*/shorts_build/short*/stage.html")) + glob.glob(os.path.join(ROOT, "0*/ep*/shorts_build/short*/stage.html"))
    elif "/s2_ura/" in me:
        pool = glob.glob(os.path.join(ROOT, "s2_ura/c*/slide.html"))
    else:
        pool = glob.glob(os.path.join(ROOT, "0*/ep*/slide.html"))
    return [p for p in pool if os.path.abspath(p) != me]


def legacy(d):
    p = os.path.join(HERE, "style_legacy.txt")
    if not os.path.exists(p):
        return False
    key = os.path.relpath(os.path.abspath(d), ROOT)
    names = [x.strip().rstrip("/") for x in open(p, encoding="utf-8") if x.strip() and not x.startswith("#")]
    return any(key == n or key.startswith(n + "/") for n in names)


def fixed_lines():
    p = os.path.join(HERE, "style_fixed_lines.txt")
    if not os.path.exists(p):
        return set()
    return {_norm(x) for x in open(p, encoding="utf-8") if x.strip() and not x.startswith("#")}


def check(d):
    path = source_of(d)
    if not path:
        sys.exit(f"{d}: slide.html / stage.html が無い")
    short = is_short(path)
    ss = sents_of(path)
    F = collections.OrderedDict((k, []) for k in ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "T1", "T2"))
    stats = {}

    # A1 語尾の連続
    def cls(s):
        s = re.sub(r"[。！？!?」』\s]+$", "", s)
        for pat, c in ENDINGS:
            if re.search(pat, s):
                return c
        return "体言止め"
    cs = [cls(s) for s in ss]
    run = best = 1
    bc, at = (cs[0] if cs else ""), 0
    for i in range(1, len(cs)):
        run = run + 1 if cs[i] == cs[i - 1] else 1
        if run > best:
            best, bc, at = run, cs[i], i
    stats["語尾の最長連続"] = f"{best}文（{bc}）"
    if not short and best >= 4:
        F["A1"].append(f"語尾「{bc}」が{best}文続く（…{ss[at][-16:]}）")
    # A2 のです
    r = cs.count("のです") / max(len(cs), 1)
    stats["のです・んです"] = f"{100 * r:.0f}%"
    if not short and r > 0.10:
        F["A2"].append(f"「のです／んです」で終わる文が {100 * r:.0f}%（10%以下にする）")
    # A3 文頭の接続詞
    op = collections.Counter(o for s in ss for o in OPENERS if s.startswith(o))
    lim = 1 if short else 3
    stats["文頭の接続詞（最多）"] = "・".join(f"{k}{v}" for k, v in op.most_common(3)) or "なし"
    for k, v in op.items():
        if v > lim:
            F["A3"].append(f"「{k}」で始まる文が{v}回（{lim}回まで）")
    # A4 回をまたぐ同じ文
    fixed = fixed_lines()
    mine = {_norm(s): s for s in ss if len(_norm(s)) >= 10}
    seen = collections.defaultdict(list)
    for p in others(path):
        try:
            for s in sents_of(p):
                n = _norm(s)
                if n in mine and n not in fixed:
                    seen[n].append(os.path.relpath(p, ROOT).split("/")[1][:4])
        except Exception:
            continue
    stats["過去の回と同じ文"] = f"{len(seen)}文"
    for n, where in seen.items():
        F["A4"].append(f"過去の回と同じ文：「{mine[n][:30]}」（{'・'.join(sorted(set(where))[:4])}）")
    # A5 文の長さ
    L = [len(s) for s in ss]
    cv = statistics.pstdev(L) / statistics.mean(L) if L else 0
    stats["最長の文"] = f"{max(L) if L else 0}字"
    stats["文の長さのばらつき"] = f"{cv:.2f}"
    for s in ss:
        if len(s) > 80:
            F["A5"].append(f"1文が{len(s)}字（80字以内に分ける）：{s[:24]}…")
    if not short and cv < 0.35:
        F["A5"].append(f"文の長さがそろいすぎている（ばらつき {cv:.2f}。0.35以上にする：短い文と長い文を混ぜる）")
    # A6 対比の型
    n6 = sum(s.count("ではなく") for s in ss)
    stats["「ではなく」"] = f"{n6}回"
    if n6 > 3:
        F["A6"].append(f"「〜ではなく、〜」が{n6}回（3回まで）")
    # A7 同じ文の繰り返し・定型句
    dup = collections.Counter(_norm(s) for s in ss if len(_norm(s)) >= 10)
    for n, c in dup.items():
        if c > 2:
            F["A7"].append(f"同じ文が{c}回：「{mine[n][:30]}」")
    whole = "".join(ss)
    for b in BANNED:
        if b in whole:
            F["A7"].append(f"定型句「{b}」を使っている")
    # T1 表記ゆれ
    scr = screen_text(path)
    zen = sorted(set(re.findall(r"[０-９Ａ-Ｚａ-ｚ]+", scr)))
    if zen:
        F["T1"].append(f"画面に全角の英数字：{zen[:5]}")
    words = set(re.findall(r"[ァ-ヶー]{3,}", scr + whole))
    for w in sorted(words):
        if w.endswith("ー") and w[:-1] in words and len(w) >= 4:
            F["T1"].append(f"表記ゆれ：「{w[:-1]}」と「{w}」")
    # T2 画面の数字がナレーションにもある（値で比べる。西暦は出典の表記に使うので対象外）
    nn = numbers(whole)
    miss = sorted(v for k, v in numbers(scr).items() if k not in nn)
    stats["画面の数字（ナレーションに無いもの）"] = f"{len(miss)}個"
    for x in miss:
        F["T2"].append(f"画面の「{x}」がナレーションに無い（数字を合わせるか、画面から外す）")

    leg = legacy(d) and "--strict" not in sys.argv
    hard = [k for k, v in F.items() if v and not leg]
    return {"dir": d.rstrip("/"), "kind": "short" if short else "long", "sentences": len(ss), "legacy": leg,
            "fails": F, "stats": stats, "pass": not hard}


NAMES = {"A1": "語尾の連続", "A2": "「のです」の割合", "A3": "文頭の接続詞", "A4": "回をまたぐ同じ文", "A5": "文の長さ",
         "A6": "対比の型", "A7": "同じ文・定型句", "T1": "表記ゆれ", "T2": "画面の数字"}


def report(res):
    print(f"── AI臭さ検査（文章・テロップ）：{res['dir']}  {res['sentences']}文" + ("  ※旧基準の回（参考表示）" if res["legacy"] else "") + " ──")
    for k, v in res["fails"].items():
        soft = res["legacy"]
        if v:
            for x in v[:6]:
                print(f"  {'!' if soft else '✗'} {k} {NAMES[k]}：{x}")
            if len(v) > 6:
                print(f"    …ほか{len(v) - 6}件")
        else:
            print(f"  ✓ {k} {NAMES[k]}")
    print("  実測：" + "／".join(f"{k} {v}" for k, v in res["stats"].items()))
    print("RESULT: PASS" if res["pass"] else "RESULT: FAIL")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    out = [check(a) for a in args]
    if "--json" in sys.argv:
        print(json.dumps(out, ensure_ascii=False))
    else:
        for r in out:
            report(r)
    sys.exit(0 if all(r["pass"] for r in out) else 1)
