#!/usr/bin/env python3
"""
check_readings.py — ナレーションの読み（VOICEVOX の実際の読み）を、ビルドの前に機械で確かめる。

2026-11-09 ユーザー指摘「名前の読み間違えが発生している」を受けて追加。run_episode.sh / run_shorts.sh が
ビルドの前に呼ぶ。FAIL のままではビルドしない。

    python3 _tools/checks/check_readings.py 06_case-studies/ep23_failure-cases     # 本編・ケースファイル
    python3 _tools/checks/check_readings.py s2_ura/u03_four-point-two               # Short（shorts_build/short*/）
    python3 _tools/checks/check_readings.py <dir> --review                           # 全文の読みも書き出す

検査（VOICEVOX を make_video と同じ辞書・同じ前処理で呼ぶ）:
  1) 人名は辞書に登録済みであること：「〇〇さん」「〇〇氏」の漢字の名前、と「姓名」が COMPOUND_DICT に無ければ FAIL。
     漢字の名前は読みが何通りもあるので、出典で読みを確かめてから COMPOUND_DICT に登録する（例："森岡毅": ("モリオカツヨシ", 4)）。
  2) カタカナの固有名詞・語が、途中で切れて読まれていないこと（例：×ノース／ウェスタン）。
     4文字以上のカタカナ語を単独で読ませ、アクセント句が2つ以上に割れたら FAIL → COMPOUND_DICT に1語で登録する。
  3) よくある誤読の型（過去に実際に起きたもの）に当たらないこと：
     「異を」をコト、「直し」をチョク、「人がい」をジンガイ、「今＋カタカナ」をコン、「並べ」をナベ、「シー」をスィー、など。
  --review：全文を「文 → 読み」で <dir>/reading_review.txt に書き出す（コミットしない作業用）。
     固有名詞の行には ★ を付ける。新しい回は、この ★ の行を必ず目で確かめる（episode-production / README §2）。
"""
import glob
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "video"))
import make_video as M  # noqa: E402

URL = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
SPEAKER = 11

# 過去に実際に起きた誤読（本文の型, 読みに出たらだめな文字列）
BAD = [
    (r"異を", "コトオ"), (r"異を", "コトヲ"),
    (r"直し(かた|方)", "チョクシ"),
    (r"人がい", "ジンガイ"),
    (r"今[ァ-ヶ]", "コン"),
    (r"並べ", "ナベ"),
    (r"シー", "スィ"),
    (r"行った", "イッタ"),        # 「おこなった」の意味で書いたときの注意（文脈で正しいこともあるので WARN）
]
WARN_ONLY = {"行った"}

NAME_RE = re.compile(r"([一-龥々]{2,5})(?=さん|氏|社長|会長|教授|博士)")
KATA_RE = re.compile(r"[ァ-ヶー]{4,}")
COMMON_OK = {"マーケティング", "マーケター", "チャンネル", "シリーズ", "スーパー"}  # 単独で割れても文中では問題が出ていない語


def kana(text):
    q = urllib.parse.urlencode({"text": text, "speaker": SPEAKER})
    r = json.load(urllib.request.urlopen(urllib.request.Request(f"{URL}/audio_query?{q}", method="POST"), timeout=30))
    return ["".join(m["text"] for m in ap["moras"]) for ap in r["accent_phrases"]]


def narrations(d):
    d = d.rstrip("/")
    paths = [f"{d}/slide.html"] + sorted(glob.glob(f"{d}/shorts_build/short*/stage.html"))
    out = []
    for p in paths:
        if os.path.exists(p):
            for n in M.extract_slide_data(p).narrations:
                out += M.split_sentences(n.replace("\n", " "))
    return out


def known_names():
    return {k for k in M.COMPOUND_DICT}


def check(d, review=False):
    sents = narrations(d)
    if not sents:
        sys.exit(f"{d}: ナレーションが見つからない（slide.html / shorts_build/short*/stage.html）")
    M.seed_user_dict(URL)
    fails, warns, lines = [], [], []
    registered = known_names()
    seen_kata = set()
    for s in sents:
        clean = M.clean_for_tts(s)
        k = kana(clean)
        flat = "".join(k)
        star = ""
        # 1) 人名
        for m in NAME_RE.finditer(s):
            name = m[1]
            # 「〇〇さん」の〇〇が、登録済みの見出し（姓名・呼称）のどれかに含まれていればよい
            if not any(name in r for r in registered):
                fails.append(f"人名が未登録：「{name}」（{s}）→ 読みを出典で確かめて COMPOUND_DICT に登録")
            star = "★"
        # 2) カタカナ語の分割
        for m in KATA_RE.finditer(clean):
            w = m[0]
            star = "★"
            if w in COMMON_OK:
                continue
            alone = kana(w)
            if len(alone) > 1 and w not in M.COMPOUND_DICT:
                wk = "".join(alone)
                # 文の中でも割れているときだけ不合格（文中で1つのアクセント句に収まっていればよい。例：STP分析）
                if wk in flat and not any(wk in ap for ap in k):
                    fails.append(f"カタカナ語が途中で切れて読まれる：「{w}」→ {'/'.join(alone)}（{s}）→ COMPOUND_DICT に1語で登録")
        # 3) よくある誤読
        for pat, bad in BAD:
            if re.search(pat, s) and bad in flat:
                msg = f"誤読の疑い：「{re.search(pat, s)[0]}」が {bad}… と読まれている（{s} → {'/'.join(k)}）"
                (warns if any(w in pat for w in WARN_ONLY) else fails).append(msg)
        lines.append(f"{star}{s}\n    → {'/'.join(k)}")
    if review:
        p = f"{d.rstrip('/')}/reading_review.txt"
        open(p, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print(f"  読みの一覧：{p}（★ は固有名詞を含む行。目で確かめる）")
    print(f"── 読み検査（VOICEVOX）：{d}  {len(sents)}文 ──")
    for w in warns:
        print("  ! " + w)
    for f in fails:
        print("  ✗ " + f)
    if fails:
        print(f"RESULT: FAIL（{len(fails)}件）— COMPOUND_DICT（_tools/video/make_video.py）に登録して再実行")
        return False
    print("  ✓ 人名は登録済み・カタカナ語の分割なし・既知の誤読なし")
    print("RESULT: PASS")
    return True


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    ok = all([check(a, "--review" in sys.argv) for a in args])
    sys.exit(0 if ok else 1)
