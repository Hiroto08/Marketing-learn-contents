#!/usr/bin/env python3
"""Markdown配布物 → PDF（ローカルChromiumで印刷・ネット不要）。

pandoc等が無い環境向け。Noto Sans CJK JP で日本語を綺麗に出す。リードマグネット
（チートシート）の配布用PDF生成に使う。

    python3 _tools/repurpose/md_to_pdf.py \
      _deliverables/lead-magnet/marketing-lab-cheatsheet.md \
      _deliverables/lead-magnet/marketing-lab-cheatsheet.pdf
"""
import html as _html
import re
import sys


def md_to_html(md: str) -> str:
    out, i, lines = [], 0, md.splitlines()
    list_open = False

    def close_list():
        nonlocal list_open
        if list_open:
            out.append("</ul>")
            list_open = False

    for ln in lines:
        s = ln.rstrip()
        if not s.strip():
            close_list()
            continue
        # 見出し
        m = re.match(r"^(#{1,4})\s+(.+)", s)
        if m:
            close_list()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            continue
        if s.strip() == "---":
            close_list()
            out.append("<hr>")
            continue
        if s.strip().startswith(">"):
            close_list()
            out.append(f"<blockquote>{inline(s.strip()[1:].strip())}</blockquote>")
            continue
        # 箇条書き（インデントでネスト）
        mb = re.match(r"^(\s*)[-*]\s+(.+)", s)
        if mb:
            if not list_open:
                out.append("<ul>")
                list_open = True
            indent = len(mb.group(1))
            cls = ' class="sub"' if indent >= 2 else ""
            out.append(f"<li{cls}>{inline(mb.group(2))}</li>")
            continue
        close_list()
        out.append(f"<p>{inline(s)}</p>")
    close_list()
    return "\n".join(out)


def inline(t: str) -> str:
    t = _html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    t = re.sub(r"(https?://[^\s　]+)", r'<a href="\1">\1</a>', t)
    return t


CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body { font-family: "Noto Sans CJK JP","Noto Sans JP",sans-serif; color:#1a2230;
  line-height:1.75; font-size:10.5pt; }
h1 { font-size:20pt; color:#0B1220; border-bottom:3px solid #0B1220;
  padding-bottom:6px; margin:0 0 14px; }
h2 { font-size:14pt; color:#0B1220; margin:22px 0 8px;
  border-left:6px solid #f5c518; padding-left:10px; }
h3 { font-size:11.5pt; color:#12305a; margin:14px 0 4px; }
p { margin:6px 0; }
ul { margin:4px 0 10px; padding-left:20px; }
li { margin:2px 0; }
li.sub { list-style:circle; margin-left:16px; color:#33405a; font-size:10pt; }
strong { color:#0B1220; }
blockquote { border-left:4px solid #cbd5e1; margin:12px 0; padding:6px 12px;
  color:#475569; background:#f8fafc; font-size:9.5pt; }
hr { border:0; border-top:1px solid #e2e8f0; margin:16px 0; }
a { color:#12305a; text-decoration:none; word-break:break-all; }
code { background:#f1f5f9; padding:1px 5px; border-radius:4px; font-size:9.5pt; }
"""


def build(md_path: str, pdf_path: str):
    md = open(md_path, encoding="utf-8").read()
    doc = (f"<!doctype html><html lang='ja'><head><meta charset='utf-8'>"
           f"<style>{CSS}</style></head><body>{md_to_html(md)}</body></html>")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        pg.set_content(doc, wait_until="load")
        pg.emulate_media(media="print")
        pg.pdf(path=pdf_path, format="A4", print_background=True)
        b.close()
    print(f"✓ PDF生成: {pdf_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: md_to_pdf.py <in.md> <out.pdf>")
    build(sys.argv[1], sys.argv[2])
