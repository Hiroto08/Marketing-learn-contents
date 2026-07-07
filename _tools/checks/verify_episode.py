#!/usr/bin/env python3
"""Unified episode verification — the ONE command every workflow runs.

    python3 _tools/checks/verify_episode.py <episode_dir> [--no-browser]

Runs all mechanical quality gates and prints a sectioned PASS/FAIL report:
  [1] file presence & counts (18 slides everywhere)
  [2] narration match  (script.md ↔ slide.html NARRATIONS, char-for-char)
  [3] narration quality (banned openings / connectives / questions / S18 loop)
  [4] STEPS density    (>= narration_secs/7 per slide, no >15s static gap)
  [5] accent uniqueness (no --accent collision across episodes)
  [6] typography       (line length, explicit <br> breaks, kinsoku, spacing)
  [7] browser render   (Playwright: 0 js errors, ids exist; skipped with --no-browser)

Exit code 0 = all PASS. Any FAIL prints an actionable reason.
Spec sources: .claude/skills/episode-production/{retention-packaging,design-system}.md
"""
import math
import os
import re
import sys
from collections import defaultdict

EP = None
FAILS = []
WARNS = []


def section(name):
    print(f"\n── {name} " + "─" * max(1, 46 - len(name)))


def fail(msg):
    FAILS.append(msg)
    print(f"  ✗ {msg}")


def ok(msg):
    print(f"  ✓ {msg}")


def warn(msg):
    WARNS.append(msg)
    print(f"  ! {msg}")


def load():
    md = open(f"{EP}/script.md", encoding="utf-8").read()
    html = open(f"{EP}/slide.html", encoding="utf-8").read()
    md_narr = [m.group(1).strip() for m in re.finditer(
        r'\*\*ナレーション：\*\*\s*\n「(.*?)」\s*\n\s*---', md, re.S)]
    arr = re.search(r"const NARRATIONS\s*=\s*\[(.*?)\n\];", html, re.S)
    h_narr = [e.replace("\\n", "\n").strip()
              for e in re.findall(r"`(.*?)`", arr.group(1), re.S)] if arr else []
    return md, html, md_narr, h_narr


def check_counts(md, html, md_narr, h_narr):
    section("1) ファイル・枚数")
    for f in ("script.md", "description.md", "slide.html", "thumbnail.md"):
        if not os.path.exists(f"{EP}/{f}"):
            fail(f"{f} が無い")
    n_sec = len(re.findall(r'<section class="slide[^"]*" id="s\d+"', html))
    metas = len(re.findall(r"\{id:'s\d+',\s*start:", html))
    if not (len(md_narr) == len(h_narr) == n_sec == metas == 18):
        fail(f"枚数不一致: script={len(md_narr)} NARRATIONS={len(h_narr)} section={n_sec} META={metas}（全て18のこと）")
    else:
        ok("script/NARRATIONS/section/SLIDES_META = 18 で一致")


def check_match(md_narr, h_narr):
    section("2) ナレーション一致（文字単位）")
    bad = [i + 1 for i in range(min(len(md_narr), len(h_narr))) if md_narr[i] != h_narr[i]]
    if bad:
        fail(f"S{bad} が script.md と slide.html で不一致")
    else:
        ok("18/18 完全一致")


def check_quality(md_narr):
    section("3) ナレーション品質（維持率ライティング）")
    all_text = "\n".join(md_narr)
    head = "。".join(md_narr[0].split("。")[:2]) if md_narr else ""
    for ban in ("のテーマは", "さっそく始めましょう", "始めていきましょう"):
        if ban in head:
            fail(f"S1冒頭2文に禁止句「{ban}」")
    n_s = len(re.findall(r"そして", all_text)) + len(re.findall(r"また、", all_text))
    if n_s > 2:
        fail(f"「そして/また、」{n_s}回（上限2）→ しかし/実は/だから 等へ")
    n_q = len(re.findall(r"(と思いますか|でしょうか|考えてみてください|ませんか)", all_text))
    if n_q < 3:
        fail(f"問いかけ{n_q}回（最低3）")
    n_b = len(re.findall(r"(しかし|ところが|実は|だから|つまり|それなのに)", all_text))
    if n_b < 6:
        fail(f"逆接・因果接続詞{n_b}回（最低6）")
    if md_narr and not re.search(r"(でしょうか|と思いますか|？)", md_narr[-1]):
        fail("S18に未解決の問い（開ループ）が無い")
    if not FAILS:
        ok(f"問いかけ{n_q} / 逆接因果{n_b} / そして系{n_s}")


def check_steps(html):
    section("4) STEPS密度（5〜7秒毎の視覚変化）")
    meta = re.findall(r"\{id:'s(\d+)',\s*start:([\d.]+),\s*end:([\d.]+)", html)
    steps = re.findall(r"\{si:(\d+),\s*t:([\d.]+)", html)
    per = defaultdict(list)
    for si, t in steps:
        per[int(si)].append(float(t))
    n0 = len(FAILS)
    for sid, start, end in meta:
        i, dur = int(sid) - 1, float(end) - float(start)
        need = math.ceil(dur / 7)
        ts = sorted(per.get(i, []))
        if len(ts) < need:
            fail(f"S{sid}: STEP {len(ts)}個 < 必要{need}個（{dur:.0f}秒）")
        seq = [float(start)] + ts + [float(end)]
        for a, b in zip(seq, seq[1:]):
            if b - a > 15:
                fail(f"S{sid}: {b - a:.0f}秒の無変化区間")
    if len(FAILS) == n0:
        ok(f"全18枚OK（総STEP {len(steps)}個）")


def check_accent(html):
    section("5) アクセントカラー衝突")
    # エピソード固有色はベースCSSの後の :root 上書きにあるため「最後の」--accent を採用
    mm = re.findall(r"--accent:\s*(#[0-9A-Fa-f]{6})", html)
    if not mm:
        fail("--accent が見つからない")
        return
    mine = mm[-1].upper()
    dup = []
    for root, _, files in os.walk("."):
        if "slide.html" in files and not root.startswith("./.claude"):
            p = os.path.join(root, "slide.html")
            if os.path.abspath(p) == os.path.abspath(f"{EP}/slide.html"):
                continue
            try:
                body = open(p, encoding="utf-8").read()
            except OSError:
                continue
            m2 = re.findall(r"--accent:\s*(#[0-9A-Fa-f]{6})", body)
            if m2 and m2[-1].upper() == mine:
                dup.append(p)
    if dup:
        fail(f"accent {mine} が重複: {dup}")
    else:
        ok(f"accent {mine} は一意")


KINSOKU_HEAD = "。、！？」』）・ぁぃぅぇぉっゃゅょーんゎ"


def _stage(html):
    """slide sections only (skip CSS/base64/JS)."""
    m = re.search(r'(<section class="slide.*?)</div><!-- /stage -->', html, re.S)
    return m.group(1) if m else ""


def check_typography(html):
    section("6) タイポグラフィ（改行・空白・文字数）")
    stage = _stage(html)
    if not stage:
        fail("ステージ領域を抽出できない")
        return
    n0 = len(FAILS)
    LIMITS = {"t-xl": 14, "t-lg": 20, "t-md": 26, "hl-banner": 26}

    import unicodedata

    def dw(s):  # 表示幅: 全角=1, 半角=0.5
        return sum(1.0 if unicodedata.east_asian_width(c) in "WFA" else 0.5 for c in s)
    # 表示テキスト要素の行長・改行位置・ぶら下がりを検査
    for m in re.finditer(
            r'<div[^>]*class="[^"]*\b(t-xl|t-lg|t-md|hl-banner)\b[^"]*"[^>]*>(.*?)</div>',
            stage, re.S):
        cls, inner = m.group(1), m.group(2)
        # コンテナ（子ブロック要素あり）は静的判定の対象外 — 実寸は 7) のPlaywright検査が担保
        if re.search(r"<(div|svg|table|ul|ol)\b", inner):
            continue
        # チップ列（achip/tag/aarrow）はflexで折り返す設計なので行長判定の対象外
        if re.search(r'class="(achip|tag|aarrow)', inner):
            continue
        # 行長・禁則: <br> と <small>（CSSでblock表示）の両方を行区切りとして評価
        text_lines = re.split(r"<br\s*/?>|<small[^>]*>|</small>", inner)
        plain_lines = [re.sub(r"<[^>]+>", "", x).strip() for x in text_lines]
        plain_lines = [x for x in plain_lines if x]
        joined = "".join(plain_lines)
        ctx = (joined[:14] + "…") if len(joined) > 14 else joined
        limit = LIMITS[cls]
        for ln in plain_lines:
            if dw(ln) > limit:
                fail(f"{cls}「{ctx}」: 1行 幅{dw(ln):.1f} > {limit}（全角換算）→ 自動折返しで端数行が出る。"
                     f"読点・助詞の後に<br>を入れて行を割る")
        if cls == "t-xl" and len(plain_lines) > 2:
            fail(f"t-xl「{ctx}」: {len(plain_lines)}行（最大2行）")
        for ln in plain_lines[1:]:
            if ln and ln[0] in KINSOKU_HEAD:
                fail(f"{cls}「{ctx}」: 行頭が禁則文字「{ln[0]}」")
        # ぶら下がり禁止：<br>で作った行に幅3以下の行を残さない
        # （<small>サブラベルはデザイン上の別行なので対象外＝除去して評価）
        no_small = re.sub(r"<small[^>]*>.*?</small>", "", inner, flags=re.S)
        br_lines = [re.sub(r"<[^>]+>", "", x).strip()
                    for x in re.split(r"<br\s*/?>", no_small)]
        br_lines = [x for x in br_lines if x]
        if len(br_lines) >= 2:
            for ln in br_lines:
                if dw(ln) <= 3:
                    fail(f"{cls}「{ctx}」: 幅{dw(ln):.1f}の行「{ln}」（ぶら下がり）→ 各行を全角4字以上に")
    # 全角スペースでの位置調整禁止（2連続以上）
    for m in re.finditer(r"　{2,}", re.sub(r"<[^>]+>", "", stage)):
        fail("全角スペース連続による位置調整がある（flex/gap/marginで組む）")
        break
    # margin-top は許可段階のみ（.15/.2/.3/.4/.5/.6/.8em, 数cqw）
    for m in re.finditer(r"margin-top:\s*([\d.]+)em", stage):
        v = float(m.group(1))
        if v > 1.2:
            fail(f"margin-top:{v}em が大きすぎる（最大1.2em。レイアウトはコンテナ側で）")
    if len(FAILS) == n0:
        ok("行長・改行位置・禁則・空白OK")


def check_browser(html_path):
    section("7) ブラウザ描画（Playwright）")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        warn("playwright未導入のためスキップ（--no-browser相当）")
        return
    errs = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--no-sandbox", "--disable-gpu"])
        pg = b.new_page(viewport={"width": 1280, "height": 720})
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"file://{os.path.abspath(html_path)}")
        pg.wait_for_load_state("networkidle")
        r = pg.evaluate("""()=>{
          const missing=[]; SLIDES_META.forEach(s=>{if(!document.getElementById(s.id))missing.push(s.id)});
          const over=[];
          document.querySelectorAll('section.slide').forEach(sec=>{
            sec.style.display='flex';
            sec.querySelectorAll('*').forEach(e=>{e.style.opacity='1';e.style.transform='none';});
            const sr=sec.getBoundingClientRect();
            sec.querySelectorAll('.se,.sh').forEach(e=>{
              const r=e.getBoundingClientRect();
              if(r.width && (r.right>sr.right+4||r.left<sr.left-4||r.bottom>sr.bottom+4))
                over.push(sec.id+':'+(e.id||e.className));
              if(e.scrollWidth>e.clientWidth+4) over.push(sec.id+':overflow:'+(e.id||e.className));
            });
            sec.style.display='';
          });
          return {missing, over:over.slice(0,8), n:document.querySelectorAll('section.slide').length};
        }""")
        b.close()
    if errs:
        fail(f"JSエラー: {errs[:3]}")
    if r["missing"]:
        fail(f"DOM欠落id: {r['missing']}")
    if r["over"]:
        fail(f"はみ出し/オーバーフロー: {r['over']}")
    if not errs and not r["missing"] and not r["over"]:
        ok(f"JSエラー0・{r['n']}枚・要素はみ出しなし")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    EP = sys.argv[1].rstrip("/")
    no_browser = "--no-browser" in sys.argv
    md, html, md_narr, h_narr = load()
    check_counts(md, html, md_narr, h_narr)
    check_match(md_narr, h_narr)
    check_quality(md_narr)
    check_steps(html)
    check_accent(html)
    check_typography(html)
    if not no_browser:
        check_browser(f"{EP}/slide.html")
    print("\n" + "=" * 50)
    if FAILS:
        print(f"RESULT: FAIL ({len(FAILS)}件) — 上記を修正して再実行")
        sys.exit(1)
    print(f"RESULT: PASS{'（警告 ' + str(len(WARNS)) + '件）' if WARNS else ''}")
