#!/usr/bin/env python3
"""Shorts quality gate — analogous to verify_episode.py but for the
vertical 9:16 format.

    python3 _tools/checks/verify_shorts.py <shorts_dir> [--no-browser]

<shorts_dir> must contain shorts.md (script) and stage.html (the vertical
slide.html built from _tools/shorts_template/vertical_template.html).

Checks:
  [1] engine integrity   (heartbeat + rv-* + keyframes not stripped)
  [2] narration match    (shorts.md ⇔ stage.html NARRATIONS, char-for-char)
  [3] duration           (30-45s from SLIDES_META)
  [4] slide count        (5-8)
  [5] hook signal        (S1's first STEP text has a number/claim/question)
  [6] CTA present        (last slide mentions 固定コメント/概要欄 etc.)
  [7] loop echo          (first and last slide share a >=3-char token)
  [8] safe-area render   (Playwright: 0 js errors, no element outside the
                          192/400/48px safe area; skipped with --no-browser)

Spec: .claude/skills/episode-production/shorts-production.md
"""
import math
import os
import re
import sys

FAILS = []
DIR = None


def section(name):
    print(f"\n── {name} " + "─" * max(1, 46 - len(name)))


def fail(msg):
    FAILS.append(msg)
    print(f"  ✗ {msg}")


def ok(msg):
    print(f"  ✓ {msg}")


def load():
    """<shorts_dir> is typically <episode_dir>/shorts_build/shortN/.
    The script lives one level up in shorts.md as a "## Short N" section
    (one file holds all Shorts for the episode), OR a local shorts.md may
    exist directly in <shorts_dir> (standalone use). Try local first."""
    local_md = f"{DIR}/shorts.md"
    if os.path.exists(local_md):
        md = open(local_md, encoding="utf-8").read()
    else:
        m = re.search(r"short(\d+)$", os.path.basename(DIR.rstrip("/")), re.I)
        if not m:
            sys.exit(f"shorts.md が見つからず、ディレクトリ名からShort番号も特定できない: {DIR}")
        n = m.group(1)
        ep_dir = os.path.dirname(os.path.dirname(DIR.rstrip("/")))
        ep_md = open(f"{ep_dir}/shorts.md", encoding="utf-8").read()
        sm = re.search(rf"## Short {n}[：:].*?(?=\n## Short \d|\Z)", ep_md, re.S)
        if not sm:
            sys.exit(f"{ep_dir}/shorts.md 内に「## Short {n}」セクションが見つからない")
        md = sm.group(0)
    html = open(f"{DIR}/stage.html", encoding="utf-8").read()
    return md, html


def check_engine(html):
    section("1) エンジン整合性")
    need = ["__heartbeat", "@keyframes __hb", "rv-fade", "rv-pop",
            ".se { opacity:0; }", "@keyframes fadeIn"]
    missing = [n for n in need if n not in html]
    if missing:
        fail(f"エンジン要素が欠落: {missing}（vertical_template.htmlから丸ごとコピーしたか確認）")
    else:
        ok("heartbeat / rv-* / keyframes 完備")


def _narrations(html):
    m = re.search(r"const NARRATIONS\s*=\s*\[(.*?)\n\];", html, re.S)
    if not m:
        return []
    return [e.replace("\\n", "\n").strip() for e in re.findall(r"`(.*?)`", m.group(1), re.S)]


def check_match(md, html):
    section("2) ナレーション一致（文字単位）")
    md_narr = [m.group(1).strip() for m in re.finditer(
        r"\*\*ナレーション：\*\*\s*\n「(.*?)」", md, re.S)]
    h_narr = _narrations(html)
    if not md_narr:
        fail("shorts.md に「**ナレーション：**」ブロックが見つからない")
        return
    if len(md_narr) != len(h_narr):
        fail(f"件数不一致: shorts.md={len(md_narr)} NARRATIONS={len(h_narr)}")
        return
    bad = [i + 1 for i in range(len(md_narr)) if md_narr[i] != h_narr[i]]
    if bad:
        fail(f"S{bad} が不一致")
    else:
        ok(f"{len(md_narr)}/{len(md_narr)} 完全一致")


def _meta(html):
    return re.findall(r"\{id:'s(\d+)',\s*start:([\d.]+),\s*end:([\d.]+)", html)


def check_duration(html):
    section("3) 尺（30〜45秒）")
    meta = _meta(html)
    if not meta:
        fail("SLIDES_META が見つからない")
        return
    total = max(float(e) for _, _, e in meta)
    if not (30 <= total <= 45):
        fail(f"尺 {total:.1f}秒（30〜45秒の範囲外）")
    else:
        ok(f"尺 {total:.1f}秒")


def check_slide_count(html):
    section("4) スライド枚数（5〜8）")
    n = len(_meta(html))
    if not (5 <= n <= 8):
        fail(f"{n}枚（5〜8枚の範囲外）")
    else:
        ok(f"{n}枚")


HOOK_PAT = re.compile(r"[0-9０-９]|倍|割|円|万|億|人|なぜ|ですか|でしょうか|ませんか|しない|ではない|知らない")


def check_hook(html):
    section("5) 冒頭フック信号")
    narr = _narrations(html)
    if not narr:
        fail("ナレーションが空")
        return
    first = narr[0]
    if HOOK_PAT.search(first):
        ok(f"S1に数字/断言/否定形/問いかけの信号あり: 「{first[:30]}…」")
    else:
        fail(f"S1に数字/断言/否定形/問いかけの信号が見当たらない: 「{first[:30]}…」")


CTA_PAT = re.compile(r"固定コメント|概要欄|続きは|長編で|チャンネル登録")


def check_cta(html):
    section("6) 送客CTA")
    narr = _narrations(html)
    if not narr:
        fail("ナレーションが空")
        return
    last = narr[-1]
    if CTA_PAT.search(last):
        ok("末尾に送客文言あり")
    else:
        fail(f"末尾に送客文言（固定コメント/概要欄等）が無い: 「{last[-40:]}」")


def check_loop(html):
    section("7) ループ（冒頭⇔末尾の共通語）")
    narr = _narrations(html)
    if len(narr) < 2:
        fail("スライドが2枚未満でループ判定不可")
        return
    first, last = narr[0], narr[-1]
    toks_first = set(re.findall(r"[一-龥]{2,}|[ァ-ヶー]{2,}|[0-9]+", first))
    toks_last = set(re.findall(r"[一-龥]{2,}|[ァ-ヶー]{2,}|[0-9]+", last))
    common = {t for t in toks_first & toks_last if len(t) >= 2}
    if common:
        ok(f"共通語あり: {common}")
    else:
        fail("冒頭と末尾に共通語が無い（ナラティブループになっていない可能性）")


def check_browser(html_path):
    section("8) セーフエリア描画（Playwright）")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  ! playwright未導入のためスキップ")
        return
    errs = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--no-sandbox", "--disable-gpu"])
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"file://{os.path.abspath(html_path)}")
        pg.wait_for_load_state("networkidle")
        r = pg.evaluate("""()=>{
          const SAFE={top:192,bottom:1920-400,left:48,right:1080-48};
          const over=[];
          document.querySelectorAll('section.slide').forEach(sec=>{
            sec.style.display='flex';
            sec.querySelectorAll('*').forEach(e=>{e.style.opacity='1';e.style.transform='none';});
            sec.querySelectorAll('.k-num,.k-line,.k-sub,.k-tag,.caption').forEach(e=>{
              const r=e.getBoundingClientRect();
              if(r.width && (r.top<SAFE.top-2||r.bottom>SAFE.bottom+2||r.left<SAFE.left-2||r.right>SAFE.right+2))
                over.push(sec.id+':'+(e.className||e.id));
            });
            sec.style.display='';
          });
          return {over:over.slice(0,10), n:document.querySelectorAll('section.slide').length};
        }""")
        b.close()
    if errs:
        fail(f"JSエラー: {errs[:3]}")
    if r["over"]:
        fail(f"セーフエリア外にはみ出し: {r['over']}")
    if not errs and not r["over"]:
        ok(f"JSエラー0・{r['n']}枚・セーフエリア内")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    DIR = sys.argv[1].rstrip("/")
    no_browser = "--no-browser" in sys.argv
    md, html = load()
    check_engine(html)
    check_match(md, html)
    check_duration(html)
    check_slide_count(html)
    check_hook(html)
    check_cta(html)
    check_loop(html)
    if not no_browser:
        check_browser(f"{DIR}/stage.html")
    print("\n" + "=" * 50)
    if FAILS:
        print(f"RESULT: FAIL ({len(FAILS)}件) — 上記を修正して再実行")
        sys.exit(1)
    print("RESULT: PASS")
