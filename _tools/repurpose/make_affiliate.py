#!/usr/bin/env python3
"""アフィリエイト資産生成（L2＝各EPの参考書籍をAmazonアソシエイトのリンクブロックに）。

各EPの script.md『### 主な引用・参考文献』から**書籍**を抽出し、Amazonアソシエイトの
検索リンク付きブロックを生成する。概要欄/note末尾に貼る素材。収益化戦略 §3-L2。

    python3 _tools/repurpose/make_affiliate.py --episode 02_intermediate/ep06_pricing-psychology
    python3 _tools/repurpose/make_affiliate.py --all

出力: _deliverables/affiliate/ep<NN>_<slug>.md（貼り付け用ブロック）

差し込み:
  AMAZON_ASSOC_TAG 環境変数 … あなたのAmazonアソシエイトのトラッキングID（例 yourtag-22）
                              未設定なら "REPLACE-TAG-22" のプレースホルダで出力

方針:
  - **実際に動画で触れた本だけ**（信頼がLTVの源泉。§L2）。参考文献の書籍のみ対象
  - 論文・公式ガイド・レポート等の非書籍は自動除外（Amazon商品でないため）
  - リンクは著者＋タイトルの**Amazon検索リンク**（ASIN不要でも成立。人手でASIN直リンクに差し替えてもよい）
  - **AIツール等のASP案件は自動抽出できない**ため、生成ブロックの下に手動追記する
  - ステマ規制・アソシエイト規約の**表記を必ず入れる**
"""
import argparse
import glob
import os
import re
import sys
import urllib.parse

# 非書籍（媒体・論文・公式サイト）を示す語 → 除外。※URLやWeb等は書籍行にも出るので含めない
NON_BOOK = re.compile(r"(公式サイト|公式ガイド|公式ドキュメント|総研|日経|東洋経済|"
                      r"PR ?Times|プレスリリース|PNAS|Science|Journal|arXiv|NeurIPS|ICML|"
                      r"Report|Index|IR資料|統計データ|調査データ|プロンプトガイド)")
# 記事/サイトのタイトルは「…」を使う（書籍は『…』）。「を含む行は記事citationとして除外
ARTICLE_MARK = re.compile(r"「")
ASIN_RE = re.compile(r"amazon\.co\.jp/(?:dp|gp/product)/([A-Z0-9]{10})")

TAG = os.environ.get("AMAZON_ASSOC_TAG", "REPLACE-TAG-22")


def parse_books(md: str) -> list:
    m = re.search(r"###?\s*(?:主な引用・)?参考文献\s*\n(.*?)(?=\n##|\Z)", md, re.S)
    if not m:
        return []
    books = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        if NON_BOOK.search(line) or ARTICLE_MARK.search(line):
            continue
        tm = re.search(r"『(.+?)』", line)   # 書籍タイトルは『』
        if not tm:
            continue                          # 論文（"..."）等はここで自然に除外
        title = tm.group(1).strip()
        before = line[:line.index("『")].lstrip("-・ 　").strip()
        author = re.sub(r"[（(].*", "", before).strip()
        asin = ASIN_RE.search(line)
        books.append({"title": title, "author": author,
                      "asin": asin.group(1) if asin else None})
    return books


def amazon_link(b: dict) -> str:
    if b.get("asin"):                          # Amazon URLが元々あれば直リンク（高品質）
        return f"https://www.amazon.co.jp/dp/{b['asin']}?tag={TAG}"
    q = urllib.parse.quote_plus(f"{b['author']} {b['title']}".strip())
    return f"https://www.amazon.co.jp/s?k={q}&tag={TAG}"


def render(num: int, title: str, books: list) -> str:
    L = [f"<!-- EP{num:02d} アフィリエイト・ブロック（概要欄/note末尾に貼る） -->",
         "", "――――――――――", "📚 この動画で触れた本（Amazonアソシエイトのリンク）", ""]
    if books:
        for b in books:
            disp = f"『{b['title']}』{('／' + b['author']) if b['author'] else ''}"
            L.append(f"・{disp}")
            L.append(f"　{amazon_link(b)}")
    else:
        L.append("（この回の参考文献に書籍が無い／未執筆。手動で追加してください）")
    L += ["",
          "※上記はAmazonアソシエイトのリンクです。当チャンネルは適格販売により収入を得ています。",
          "",
          "<!-- ▼ここにAIツール/SaaSのASP案件を手動追記（動画で実演したものだけ）",
          "・ツール名 → アフィリエイトURL",
          "-->"]
    return "\n".join(L) + "\n"


def process(ep_dir: str, out_dir: str) -> bool:
    path = os.path.join(ep_dir, "script.md")
    if not os.path.exists(path):
        return False
    md = open(path, encoding="utf-8").read()
    m = re.match(r"#\s*第(\d+)回[：:]\s*(.+)", md.splitlines()[0])
    if not m:
        return False
    num, title = int(m.group(1)), m.group(2).strip()
    books = parse_books(md)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"ep{num:02d}_{os.path.basename(ep_dir).split('_',1)[-1]}.md")
    open(out, "w", encoding="utf-8").write(render(num, title, books))
    print(f"EP{num:02d}: 書籍{len(books)}冊 → {out}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out-dir", default="_deliverables/affiliate")
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    if TAG == "REPLACE-TAG-22":
        print("※ AMAZON_ASSOC_TAG 未設定 → プレースホルダ 'REPLACE-TAG-22' で出力", file=sys.stderr)
    if a.episode:
        dirs = [a.episode.rstrip("/")]
    elif a.all:
        dirs = [os.path.dirname(p) for p in
                sorted(glob.glob(os.path.join(a.root, "0*", "ep*", "script.md")))]
    else:
        ap.error("--episode か --all")
    n = sum(process(d, a.out_dir) for d in dirs)
    if not n:
        sys.exit("生成対象なし。")


if __name__ == "__main__":
    main()
