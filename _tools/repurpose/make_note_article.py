#!/usr/bin/env python3
"""note記事パイプライン（YouTube以外のマネタイズ自動化）。

各EPの script.md の **ナレーション：** ブロックを抽出して、読み物としての note 記事
Markdown に再構成する。収益化戦略 docs/monetization-strategy.md §5-2「第二の検索戦線
＝各script.mdをnote記事化し、記事末尾で動画とリードマグネットへ誘導」の実装。

    # 1本
    python3 _tools/repurpose/make_note_article.py --episode 04_ai-usage/ep13_ai-market-research
    # 実スクリプトのある全話
    python3 _tools/repurpose/make_note_article.py --all

出力: _deliverables/note/<epNN>_<slug>.md（--out-dir で変更可）

差し込み（環境変数・任意）:
  LEAD_CHANNEL_URL … チャンネルURL   LEAD_NEXT_URL … リードマグネット/特典URL
  NOTE_VIDEO_URL   … その回の動画URL（未設定ならプレースホルダ）

注意:
  - script.md が正となるブランチで実行すること（ブランチにより台本が異なりうる）。
  - 動画URLは docs/upload-status.md の videoId から手で補ってもよい（本ツールは触れない）。
"""
import argparse
import glob
import os
import re
import sys

# 章立てから除外（YouTube固有のイントロ/アウトロ枠。ナレーションごと落とす）
DROP_WHOLE = re.compile(r"^(タイトル|オープニング|次への|次回|エンド|CTA)")
# 見出しは出さず地の文として流す（物語の導入・事例・適用など）
NO_HEADING = re.compile(r"^(約束|フック|コールドオープン|リフック|回収|導入|問題提起|ケース|適用)")

DEFAULT_CHANNEL = "https://www.youtube.com/channel/UCZm9m37ivzDN0ZGvQAhBDpw"

_ENUM = re.compile(r"^(原則|基本|ポイント|ステップ|手順|法則|方法|コツ|要素|続き)"
                   r"[①-⑳0-9]*\s*[：:]?\s*")
_ANNOT = re.compile(r"(＋[^、。（]*(問い|問いかけ)[^、。]*|"
                    r"（[^）]*(図解|固有|問いかけ)[^）]*）|"
                    r"（(NEW|New|新|改|更新)[!！]?）)\s*$")
_TS = re.compile(r"\s*（[\d:：〜~\.\-\s]+）\s*$")


def clean_heading(head: str) -> str:
    head = _TS.sub("", head)
    head = re.sub(r"\s*[—―–]{2,}\s*", "：", head)
    if head.startswith("まとめ"):      # 「まとめ：明日やること1つ」等を統一
        return "まとめ"
    prev = None                        # 「法則②続き」等の二重ラベルを繰り返し除去
    while prev != head:
        prev = head
        head = _ENUM.sub("", head)
    head = _ANNOT.sub("", head)
    return head.strip("：: 　").strip()


def resolve_video_url(root: str, num: int) -> str | None:
    """docs/upload-status.md があれば本編videoIdからURLを組む（無ければNone）。"""
    path = os.path.join(root, "docs", "upload-status.md")
    if not os.path.exists(path):
        return None
    for line in open(path, encoding="utf-8"):
        m = re.match(rf"\|\s*EP0*{num}\s*\|[^|]*\|\s*`([A-Za-z0-9_-]{{6,}})`", line)
        if m:
            return f"https://youtu.be/{m.group(1)}"
    return None


def strip_quotes(text: str) -> str:
    text = text.strip()
    if text.startswith("「"):
        text = text[1:]
    if text.endswith("」"):
        text = text[:-1]
    return text.strip()


def parse(ep_dir: str) -> dict | None:
    path = os.path.join(ep_dir, "script.md")
    if not os.path.exists(path):
        return None
    md = open(path, encoding="utf-8").read()
    lines = md.splitlines()
    m = re.match(r"#\s*第(\d+)回[：:]\s*(.+)", lines[0]) if lines else None
    if not m:
        return None
    num, title = int(m.group(1)), m.group(2).strip()

    # スライド見出しの位置を取得し、各ブロックからナレーションを抜く
    heads = list(re.finditer(
        r"^#{2,3}\s*(?:🎬\s*)?スライド\s*(\d+)\s*[：:]\s*(.+?)\s*$", md, re.M))
    if not heads:
        return None

    sections = []
    for i, h in enumerate(heads):
        raw = _TS.sub("", h.group(2).strip())
        span = md[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(md)]
        nm = re.search(r"\*\*ナレーション：\*\*\s*(.+?)(?=\n---|\n\*\*|\Z)", span, re.S)
        if not nm:
            continue
        narration = strip_quotes(nm.group(1))
        if not narration:
            continue
        if DROP_WHOLE.match(raw):
            continue
        show_head = None if NO_HEADING.match(raw) else clean_heading(raw)
        sections.append((show_head, narration))

    if not sections:
        return None
    return {"num": num, "title": title, "slug": os.path.basename(ep_dir), "sections": sections}


def render(ep: dict) -> str:
    ch = os.environ.get("LEAD_CHANNEL_URL", DEFAULT_CHANNEL)
    nxt = os.environ.get("LEAD_NEXT_URL")  # 未ホストなら None
    vid = os.environ.get("NOTE_VIDEO_URL") or ep.get("video_url")

    L = [f"# {ep['title']}", ""]
    for head, narration in ep["sections"]:
        if head:
            L += [f"## {head}", ""]
        # ナレーションの段落（空行区切り）を保ったまま出す
        for para in re.split(r"\n\s*\n", narration):
            para = para.strip()
            if para:
                L += [para, ""]

    L += ["---", "",
          "## この記事は動画でも見られます",
          "",
          f"この記事は「AI時代のマーケティング・ラボ 第{ep['num']}回」の内容を、"
          "読み物として再構成したものです。図解つきの動画版もあります👇", ""]
    if vid:
        L.append(f"🎬 動画で見る：{vid}")
    L.append(f"📺 チャンネル（全話）：{ch}")
    if nxt:
        L.append(f"✉️ 全話の要点をまとめた無料チートシート：{nxt}")
    else:
        L.append("✉️ 全話の要点をまとめた無料チートシートも配布中（プロフィールのリンクから）")
    L += ["",
          "役に立ったら、スキとフォローで応援してもらえると励みになります。",
          "",
          "#マーケティング #マーケティング入門 #ビジネス #マーケティング初心者"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", help="単一エピソードのディレクトリ")
    ap.add_argument("--all", action="store_true", help="実スクリプトのある全話")
    ap.add_argument("--out-dir", default="_deliverables/note")
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    if not (a.episode or a.all):
        ap.error("--episode か --all を指定")

    if a.episode:
        dirs = [a.episode.rstrip("/")]
    else:
        dirs = [os.path.dirname(p) for p in
                sorted(glob.glob(os.path.join(a.root, "0*", "ep*", "script.md")))]

    os.makedirs(a.out_dir, exist_ok=True)
    made = 0
    for d in dirs:
        ep = parse(d)
        if not ep:
            print(f"skip（ナレーション抽出不可/テンプレ）: {d}")
            continue
        ep["video_url"] = resolve_video_url(a.root, ep["num"])
        out = os.path.join(a.out_dir, f"ep{ep['num']:02d}_{ep['slug'].split('_', 1)[-1]}.md")
        with open(out, "w", encoding="utf-8") as f:
            f.write(render(ep))
        chars = sum(len(n) for _, n in ep["sections"])
        print(f"EP{ep['num']:02d} → {out}（本文 約{chars}字・{len(ep['sections'])}節）")
        made += 1
    if not made:
        sys.exit("生成対象なし。")


if __name__ == "__main__":
    main()
