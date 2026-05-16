#!/usr/bin/env python3
"""
slide_record.html を生成する。
  - コントロールパネル (#ctrl) を非表示
  - ナレーションパネル (#narr-panel) を非表示
  - ステージが 1280x720 ちょうどで viewport を埋める
  - Font Awesome はローカル参照のまま引き継ぐ

Usage: python3 make_record_html.py <slide.html> <output.html>
"""
import sys
import re

src = sys.argv[1] if len(sys.argv) > 1 else "../slide.html"
dst = sys.argv[2] if len(sys.argv) > 2 else "../slide_record.html"

INJECT_CSS = """
<style id="record-mode">
/* === 録画モード: コントロール・ナレーション非表示、ステージ全画面 === */
html, body {
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  background: #0b0b1a !important;
  width: 1280px !important;
  height: 720px !important;
}
#stage-wrap {
  max-width: 1280px !important;
  width: 1280px !important;
  margin: 0 !important;
  padding: 0 !important;
}
#stage {
  padding-top: 0 !important;
  height: 720px !important;
  width: 1280px !important;
}
.slide {
  position: absolute !important;
  inset: 0 !important;
  width: 1280px !important;
  height: 720px !important;
}
#ctrl        { display: none !important; }
#narr-panel  { display: none !important; }
#btn-narr    { display: none !important; }
#flash       { display: none !important; }
</style>
"""

with open(src, encoding="utf-8") as f:
    html = f.read()

# </head> の直前に録画モード CSS を挿入
html = html.replace("</head>", INJECT_CSS + "</head>", 1)

with open(dst, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Created: {dst}")
