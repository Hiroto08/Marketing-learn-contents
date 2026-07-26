#!/usr/bin/env python3
"""note記事の見出し画像（アイキャッチ）PNGを自動生成して貯める。

    # 1本だけ生成
    python3 _tools/publish/make_note_thumbnail.py --file _deliverables/note/ep02_3c-stp-analysis.md

    # _deliverables/note/ の「見出し画像案」メモを持つ全記事を一括生成（貯める）
    python3 _tools/publish/make_note_thumbnail.py --all

テキストの出どころ：各note記事末尾の
    <!-- 見出し画像案: メイン「…」／サブ「…」／数字 …／背景 シリーズ共通色 #0B1220 -->
から メイン→main、サブ→sub を取り出す（--main / --sub で上書き可）。

デザインはYouTubeサムネ（make_thumbnail.py）とシリーズ共通：背景#0B1220・第N回バッジ・
Noto Sans JP Black・数字強調。アクセント色は対応エピソードの slide.html の
:root { --accent:… } から自動取得する（noteファイル名の epNN から該当ディレクトリを解決）。
サイズは note 推奨の見出し画像 1280x670。

出力先は既定で _deliverables/note/thumbnails/epNN.png（コミット対象。コンテナ再作成後も残る）。
noteへの画像添付は非公式APIの本ツール範囲外——生成したPNGを note 編集画面で人が設定する。
"""
import argparse
import glob
import os
import re
import sys

# YouTubeサムネと描画ヘルパー（数字強調・2行分割）を共有する
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_thumbnail import _hi, _split_two_lines  # noqa: E402

W, H = 1280, 670          # note推奨の見出し画像サイズ
USABLE = 1150             # 左右パディングを除いた実効幅
DEFAULT_ACCENT = "#FFD54F"
OUT_DIR = "_deliverables/note/thumbnails"


def _episode_no(note_path: str) -> str:
    m = re.search(r"ep(\d+)", os.path.basename(note_path))
    return str(int(m.group(1))) if m else "?"


def _accent_for(note_path: str) -> str:
    """note epNN に対応する本編 slide.html の --accent を取得（無ければ既定色）"""
    m = re.search(r"(ep\d+)", os.path.basename(note_path))
    if not m:
        return DEFAULT_ACCENT
    hits = glob.glob(f"*/{m.group(1)}_*/slide.html") + glob.glob(f"{m.group(1)}_*/slide.html")
    if not hits:
        return DEFAULT_ACCENT
    html = open(hits[0], encoding="utf-8").read()
    cols = re.findall(r":root\s*\{\s*--accent:\s*(#[0-9A-Fa-f]{6})", html)
    return cols[-1] if cols else DEFAULT_ACCENT


def texts_from_note(note_path: str):
    """記事末尾の『見出し画像案』メモから (main, sub) を取り出す"""
    md = open(note_path, encoding="utf-8").read()
    m = re.search(r"見出し画像案[:：](.+?)-->", md, re.S)
    if not m:
        return None, None
    body = m.group(1)
    main = re.search(r"メイン[「『](.+?)[」』]", body)
    sub = re.search(r"サブ[「『](.+?)[」』]", body)
    return (main.group(1).strip() if main else None,
            sub.group(1).strip() if sub else None)


def render_html(no: str, accent: str, main: str, sub: str | None) -> str:
    main_len = len(re.sub(r"\s", "", main))
    lines = [main] if main_len <= 9 else _split_two_lines(main)
    longest = max(len(re.sub(r"\s", "", l)) for l in lines)
    size = min(180, int(USABLE / max(longest, 1)))
    main_html = "<br>".join(_hi(l) for l in lines)
    sub_html = f'<div class="sub">{_hi(sub)}</div>' if sub else ""
    return f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Noto Sans JP','Noto Sans CJK JP',sans-serif;color:#EEEEF8}}
#t{{position:relative;width:{W}px;height:{H}px;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:30px;padding:0 60px;
  background:radial-gradient(ellipse at 78% 20%, {accent}2E 0%, transparent 52%),
             linear-gradient(135deg,#0B1220 0%,#101830 62%,#0B1220 100%)}}
.badge{{position:absolute;top:34px;left:44px;font-weight:900;font-size:38px;
  color:{accent};border:4px solid {accent};border-radius:999px;padding:.18em .8em}}
.series{{position:absolute;top:46px;right:48px;font-weight:500;font-size:28px;color:#B8BEDD}}
.main{{font-weight:900;font-size:{size}px;line-height:1.14;text-align:center;
  white-space:nowrap;text-shadow:0 6px 30px rgba(0,0,0,.6)}}
.main .acc{{color:{accent};text-shadow:0 0 44px {accent}59}}
.sub{{font-weight:900;font-size:50px;line-height:1.3;text-align:center;color:#D9DCEF;
  border-top:3px solid {accent}66;padding-top:24px}}
.sub .acc{{color:{accent}}}
.bar{{position:absolute;left:0;bottom:0;width:100%;height:14px;
  background:linear-gradient(90deg,{accent},{accent}00 82%)}}
</style></head><body><div id="t">
  <div class="badge">第{no}回</div>
  <div class="series">AI時代のマーケティング・ラボ</div>
  <div class="main">{main_html}</div>
  {sub_html}
  <div class="bar"></div>
</div></body></html>"""


def render_png(page, note_path: str, main: str, sub: str | None, out: str):
    html = render_html(_episode_no(note_path), _accent_for(note_path), main, sub)
    tmp = f"{out}.src.html"
    open(tmp, "w", encoding="utf-8").write(html)
    page.set_viewport_size({"width": W, "height": H})
    page.goto(f"file://{os.path.abspath(tmp)}")
    page.wait_for_timeout(300)
    page.screenshot(path=out)
    os.remove(tmp)
    print(f"note-thumbnail: {out}  main=「{main}」 sub=「{sub or '(なし)'}」")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="note記事md（1本だけ生成）")
    ap.add_argument("--all", action="store_true", help="_deliverables/note/ の全記事を一括生成")
    ap.add_argument("--main")
    ap.add_argument("--sub")
    ap.add_argument("--out")
    a = ap.parse_args()

    if a.all:
        files = sorted(f for f in glob.glob("_deliverables/note/ep*.md"))
    elif a.file:
        files = [a.file]
    else:
        sys.exit("--file <md> か --all のどちらかを指定")

    os.makedirs(OUT_DIR, exist_ok=True)
    jobs = []
    for f in files:
        main_t = a.main or texts_from_note(f)[0]
        sub_t = a.sub if a.sub is not None else texts_from_note(f)[1]
        if not main_t:
            print(f"skip（見出し画像案メモなし）: {f}")
            continue
        no = _episode_no(f)
        out = a.out or os.path.join(OUT_DIR, f"ep{int(no):02d}.png")
        jobs.append((f, main_t, sub_t, out))

    if not jobs:
        sys.exit("生成対象なし（見出し画像案メモを持つ記事が見つからない）")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": W, "height": H})
        for f, main_t, sub_t, out in jobs:
            render_png(page, f, main_t, sub_t, out)
        b.close()
    print(f"完了：{len(jobs)}枚を {OUT_DIR}/ に生成")


if __name__ == "__main__":
    main()
