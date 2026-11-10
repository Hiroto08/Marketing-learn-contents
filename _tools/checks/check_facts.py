#!/usr/bin/env python3
"""
check_facts.py — ナレーションに出る数字が、2つ以上の情報源で確かめてあるかを機械で判定する（quality-gates.md F1〜F3）。

    python3 _tools/checks/check_facts.py <回のフォルダ | shorts_build/shortN>
    python3 _tools/checks/check_facts.py <dir> --json
    python3 _tools/checks/check_facts.py <dir> --strict     # 旧基準の回も判定する

台本（本編・ケースファイルは script.md、Shorts は shorts.md）に、次の表を書く。見出しは「## 数字の確認」。

    ## 数字の確認
    | 数字 | 何の数字か | ソース1 | ソース2 |
    |---|---|---|---|
    | 25% | JCペニーの2012年度の売上の減少率 | https://… | https://… |
    | 18時 | 対象外：このチャンネルの公開時刻 | — | — |

  F1 網羅    ナレーションの「数字＋単位」（%・倍・円・ドル・人・件・回・時間…。西暦は F3）が、すべて表の「数字」欄にある
  F2 2ソース  各行に URL が2つ以上あり、ドメインが2つ以上に分かれている（同じサイトの2ページは1つと数える）。
              事例の数字でないもの（公開時刻・手順の数など）は「何の数字か」を「対象外：理由」で始める
  F3 西暦    ナレーションの西暦（19xx年・20xx年）も表にある（出来事の年は事実なので、同じく2ソース）

旧基準の回（_tools/checks/style_legacy.txt）は参考表示にとどめる。
"""
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_style as CS  # noqa: E402

YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})年")


def table(d):
    d = d.rstrip("/")
    item = re.sub(r"/shorts_build/short\d+$", "", d)
    md = f"{item}/shorts.md" if d != item or not os.path.exists(f"{item}/script.md") else f"{item}/script.md"
    if not os.path.exists(md):
        return md, None
    t = open(md, encoding="utf-8").read()
    m = re.search(r"^## 数字の確認\s*\n(.*?)(?=^## |\Z)", t, re.S | re.M)
    if not m:
        return md, None
    rows = []
    for line in m[1].split("\n"):
        if not line.startswith("|") or re.match(r"\|\s*(数字|-+)\s*\|", line):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) >= 2:
            rows.append({"num": c[0], "what": c[1], "urls": re.findall(r"https?://[^\s)|\]]+", " ".join(c[2:]))})
    return md, rows


def check(d):
    path = CS.source_of(d)
    if not path:
        sys.exit(f"{d}: slide.html / stage.html が無い")
    whole = "".join(CS.sents_of(path))
    nums = CS.numbers(whole)
    years = sorted({m[1] for m in YEAR_RE.finditer(whole)})
    md, rows = table(d)
    F = {"F1": [], "F2": [], "F3": []}
    leg = CS.legacy(d) and "--strict" not in sys.argv
    if rows is None:
        F["F1"].append(f"{os.path.relpath(md)} に「## 数字の確認」の表が無い（数字 {len(nums)}個・西暦 {len(years)}個）")
    else:
        have, have_y = {}, set()
        for r in rows:
            for k in CS.numbers(r["num"]):
                have[k] = r
            for m in YEAR_RE.finditer(r["num"]):
                have_y.add(m[1])
        for k, raw in sorted(nums.items(), key=lambda x: x[1]):
            if k not in have:
                F["F1"].append(f"「{raw}」が表に無い")
        for y in years:
            if y not in have_y:
                F["F3"].append(f"西暦「{y}年」が表に無い")
        for r in rows:
            if r["what"].startswith("対象外"):
                continue
            doms = {urllib.parse.urlparse(u).netloc.replace("www.", "") for u in r["urls"]}
            if len(doms) < 2:
                F["F2"].append(f"「{r['num']}」（{r['what'][:20]}）の情報源が {len(doms)} つ（2つ以上の別のサイトで確かめる）")
    return {"dir": d.rstrip("/"), "legacy": leg, "numbers": len(nums), "years": len(years), "rows": len(rows or []),
            "fails": F, "pass": leg or not any(F.values())}


NAMES = {"F1": "数字の網羅", "F2": "2ソース", "F3": "西暦"}


def report(res):
    print(f"── 数字の確認：{res['dir']}  数字 {res['numbers']}個・西暦 {res['years']}個・表 {res['rows']}行" + ("  ※旧基準の回（参考表示）" if res["legacy"] else "") + " ──")
    for k, v in res["fails"].items():
        if v:
            for x in v[:8]:
                print(f"  {'!' if res['legacy'] else '✗'} {k} {NAMES[k]}：{x}")
            if len(v) > 8:
                print(f"    …ほか{len(v) - 8}件")
        else:
            print(f"  ✓ {k} {NAMES[k]}")
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
