#!/usr/bin/env python3
"""_deliverables/affiliate/ep*.md の書籍ブロックを、対応する description.md の
`## アフィリエイト` セクションへ注入する（冪等・HTMLコメント除去）。
実タグ(aicreateslife-22)を持つEPのみ対象。ASP手動枠のコメントは概要欄から除去する。"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TAG = "aicreateslife-22"

def clean_block(md: str) -> str:
    """アフィリエイトmdを概要欄用テキストへ。<!-- --> コメントを全除去。"""
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)   # HTMLコメント枠を除去
    return md.strip()

def upsert_section(desc: str, body: str) -> str:
    section = f"## アフィリエイト\n\n```\n{body}\n```\n"
    # 既存の ## アフィリエイト があれば置換、無ければ末尾に追記（冪等）
    pat = re.compile(r"\n?## アフィリエイト\s*\n.*?(?=\n## |\Z)", re.S)
    if pat.search(desc):
        return pat.sub("\n" + section, desc).rstrip() + "\n"
    sep = "" if desc.endswith("\n") else "\n"
    return desc.rstrip() + "\n\n---\n\n" + section

changed = []
for f in sorted(glob.glob(f"{ROOT}/_deliverables/affiliate/ep*.md")):
    raw = open(f, encoding="utf-8").read()
    if TAG not in raw:
        continue                                     # 書籍0冊/未タグEPはスキップ
    num = os.path.basename(f).split("_")[0]           # ep06
    dirs = glob.glob(f"{ROOT}/*/{num}_*")
    if not dirs:
        print(f"  SKIP {num}: EPディレクトリ無し"); continue
    dpath = os.path.join(dirs[0], "description.md")
    if not os.path.exists(dpath):
        print(f"  SKIP {num}: description.md 無し"); continue
    body = clean_block(raw)
    desc = open(dpath, encoding="utf-8").read()
    new = upsert_section(desc, body)
    if new != desc:
        open(dpath, "w", encoding="utf-8").write(new)
        changed.append(os.path.relpath(dpath, ROOT))
        print(f"  OK   {num}: {os.path.relpath(dpath, ROOT)}")
    else:
        print(f"  --   {num}: 変更なし（既に最新）")

print(f"\n変更 {len(changed)} ファイル")
