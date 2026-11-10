#!/usr/bin/env python3
"""
proper_nouns.py — 固有名詞の台帳（docs/proper-nouns.md）を読む・確かめる。

台帳は「表記・読み・種別・確認ソース・確認文字列・確認日・初出」の表。原稿に出る人名・企業名・商品名・地名などは
すべてここに載せる（品質ルール 2026-11-10。Issue #2）。check_readings.py がビルドの前後にこの台帳と突き合わせる。

    python3 _tools/checks/proper_nouns.py --verify            # 確認ソースを取得し、確認文字列が載っているかを確かめて確認日を書く
    python3 _tools/checks/proper_nouns.py --verify 森岡毅       # 1件だけ
    python3 _tools/checks/proper_nouns.py --list              # 一覧（機械が読めているかの確認）

台帳の決まり：
- 表記：原稿に出る形。複数あるときは「／」で区切る（例：JCペニー／ジェーシーペニー）。
- 読み：カタカナ。長音は「ー」でも母音でもよい（照合のときにそろえる）。
- 種別：人名／企業・団体／商品・サービス／媒体・作品／地名／用語。
- 確認ソース：人名・企業・団体・商品・サービス・媒体・作品は URL が必須（公式サイト・公式プロフィール・出版社の著者紹介など）。
  地名・用語は「—」でよい（読みの照合は同じように行う）。
- 確認文字列：そのページに載っているはずの文字列（例：もりおか つよし）。空白・中黒は無視して照合する。
  漢字の人名は、ふりがなかローマ字（Tsuyoshi Morioka など）を確認文字列にする。表記だけ載っているページは証拠にならない。
- 確認日：--verify が成功した日を書く。手で書かない。空欄の行は「未確認」で、URL 必須の種別ではビルドが止まる。
"""
import datetime
import html
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
LEDGER = os.path.join(ROOT, "docs", "proper-nouns.md")
ALLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reading_allowlist.txt")
NEED_URL = ("人名", "企業", "団体", "商品", "サービス", "媒体", "作品")
COLS = ["表記", "読み", "種別", "確認ソース", "確認文字列", "確認日", "初出"]

_V = {}
for row, v in (("アカサタナハマヤラワガザダバパァャヮ", "ア"), ("イキシチニヒミリギジヂビピィ", "イ"),
               ("ウクスツヌフムユルグズヅブプゥュヴ", "ウ"), ("エケセテネヘメレゲゼデベペェ", "エ"),
               ("オコソトノホモヨロヲゴゾドボポォョ", "オ")):
    for ch in row:
        _V[ch] = v


def norm_kana(s, merge=False):
    """読みの照合用にそろえる：ひらがな→カタカナ、長音「ー」→直前の母音、ヲ→オ、ヂ→ジ、ヅ→ズ。
    merge=True なら、漢語の長音（オ段＋ウ→オオ、エ段＋イ→エエ）もそろえる（VOICEVOX は「コウコク」を「コオコク」と返す）"""
    s = "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)
    s = re.sub(r"[^ァ-ヶー]", "", s).replace("ヲ", "オ").replace("ヂ", "ジ").replace("ヅ", "ズ")
    out = []
    for c in s:
        prev = _V.get(out[-1]) if out else None
        if c == "ー":
            out.append(prev or "")
        elif merge and c == "ウ" and prev == "オ":
            out.append("オ")
        elif merge and c == "イ" and prev == "エ":
            out.append("エ")
        else:
            out.append(c)
    return "".join(out)


def reading_variants(reading):
    """台帳の読み（「／」区切り可）を、音声の読みと照合できる形にする（長音の書き方の違いを両方試す）"""
    out = set()
    for x in reading.split("／"):
        out |= {norm_kana(x), norm_kana(x, merge=True)}
    return {v for v in out if v}


def load():
    """[{表記, forms[], 読み, 種別, 確認ソース, 確認文字列, 確認日, 初出, line}]"""
    rows = []
    if not os.path.exists(LEDGER):
        return rows
    for n, line in enumerate(open(LEDGER, encoding="utf-8")):
        if not line.startswith("|") or re.match(r"\|\s*(表記|-+)\s*\|", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < len(COLS):
            continue
        r = dict(zip(COLS, cells))
        r["forms"] = [f.strip() for f in r["表記"].split("／") if f.strip()]
        r["line"] = n
        rows.append(r)
    return rows


def allowlist():
    if not os.path.exists(ALLOW):
        return set()
    return {w.strip() for w in open(ALLOW, encoding="utf-8") if w.strip() and not w.startswith("#")}


def needs_url(kind):
    return any(k in kind for k in NEED_URL)


def page_text(url):
    url = urllib.parse.quote(url, safe=":/?&=%#+,;@~")      # 日本語を含む URL（事典の項目名など）
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (proper-noun reading check)"})
    raw = urllib.request.urlopen(req, timeout=30).read()
    t = raw.decode("utf-8", "ignore")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", t))


def squash(s):
    return re.sub(r"[\s・･·,，、()（）]", "", s).lower()


def verify(only=None):
    rows = load()
    lines = open(LEDGER, encoding="utf-8").read().split("\n")
    today = datetime.date.today().isoformat()
    ok = True
    for r in rows:
        if only and only not in r["forms"]:
            continue
        url = re.search(r"https?://[^\s)|]+", r["確認ソース"])
        if not url:
            if needs_url(r["種別"]):
                print(f"✗ {r['表記']}（{r['種別']}）: 確認ソースの URL が無い")
                ok = False
            continue
        want = r["確認文字列"]
        if not want or want == "—":
            print(f"✗ {r['表記']}: 確認文字列が無い（ページのどの文字で読みを確かめたかを書く）")
            ok = False
            continue
        try:
            found = squash(want) in squash(page_text(url[0]))
        except Exception as e:
            print(f"✗ {r['表記']}: 取得できない {url[0]}（{str(e)[:60]}）")
            ok = False
            continue
        if not found:
            print(f"✗ {r['表記']}: {url[0]} に「{want}」が見つからない")
            ok = False
            continue
        cells = [c.strip() for c in lines[r["line"]].strip().strip("|").split("|")]
        cells[5] = today
        lines[r["line"]] = "| " + " | ".join(cells) + " |"
        print(f"✓ {r['表記']} ＝ {r['読み']}（{want}）")
    open(LEDGER, "w", encoding="utf-8").write("\n".join(lines))
    print("RESULT: PASS" if ok else "RESULT: FAIL")
    return ok


if __name__ == "__main__":
    if "--verify" in sys.argv:
        rest = [a for a in sys.argv[1:] if not a.startswith("--")]
        sys.exit(0 if verify(rest[0] if rest else None) else 1)
    for r in load():
        print(f"{r['種別']}\t{r['表記']}\t{r['読み']}\t{sorted(reading_variants(r['読み']))}\t{r['確認日'] or '未確認'}")
