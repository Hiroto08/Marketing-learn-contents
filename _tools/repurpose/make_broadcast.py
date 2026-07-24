#!/usr/bin/env python3
"""週次ブロードキャストメール草稿を生成（メーリスの定常配信）。

各EPの script.md から「件名・冒頭フック・今週の学び・動画リンク」を抜き、Kitの
Broadcast に貼れる短いメール草稿を作る。収益化戦略 §5-2／`docs/mailing-list-plan.md` §3。
**送信はKit → Broadcasts に貼って手動送信/予約**（本ツールは草稿まで）。

    python3 _tools/repurpose/make_broadcast.py --episode 02_intermediate/ep07_4p-4c-mix
    python3 _tools/repurpose/make_broadcast.py --episode <dir> --note https://note.com/xxx/n/yyy

出力: _deliverables/broadcast/ep<NN>_<slug>.md（件名＋本文）

差し込み（任意）:
  --note <URL>       … 該当回の note記事URL（あれば本文に「文章で読む」導線を足す）
  NOTE_VIDEO_URL 環境変数 or docs/upload-status.md から動画URLを自動解決
"""
import argparse
import glob
import os
import re
import sys

DEFAULT_CHANNEL = "https://www.youtube.com/channel/UCZm9m37ivzDN0ZGvQAhBDpw"
OPT_IN = "https://witty-composer-9473.kit.com/ac0f4ce77b"

HOOK_HEADING = re.compile(r"(コールドオープン|フック)")
_TS = re.compile(r"\s*（[\d:：〜~\.\-\s]+）\s*$")


def strip_quotes(t: str) -> str:
    t = t.strip()
    if t.startswith("「"):
        t = t[1:]
    if t.endswith("」"):
        t = t[:-1]
    return t.strip()


def first_sentences(text: str, n: int) -> str:
    parts = re.split(r"(?<=。)", text)
    return "".join(parts[:n]).strip()


def resolve_video_url(root: str, num: int) -> str | None:
    p = os.path.join(root, "docs", "upload-status.md")
    if not os.path.exists(p):
        return None
    for line in open(p, encoding="utf-8"):
        m = re.match(rf"\|\s*EP0*{num}\s*\|[^|]*\|\s*`([A-Za-z0-9_-]{{6,}})`", line)
        if m:
            return f"https://youtu.be/{m.group(1)}"
    return None


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

    goal_m = re.search(r"学習ゴール\s*\|\s*(.+?)\s*\|", md)
    goal = goal_m.group(1).strip() if goal_m else ""

    # スライドブロックからフック（コールドオープン/フック）のナレーションを取得
    heads = list(re.finditer(
        r"^#{2,3}\s*(?:🎬\s*)?スライド\s*(\d+)\s*[：:]\s*(.+?)\s*$", md, re.M))
    hook = ""
    for i, h in enumerate(heads):
        raw = _TS.sub("", h.group(2))
        if HOOK_HEADING.search(raw):
            span = md[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(md)]
            nm = re.search(r"\*\*ナレーション：\*\*\s*(.+?)(?=\n---|\n\*\*|\Z)", span, re.S)
            if nm:
                hook = strip_quotes(nm.group(1))
                break
    if not hook and len(heads) >= 2:  # フック見出しが無ければスライド2の本文
        h = heads[1]
        span = md[h.end(): heads[2].start() if len(heads) > 2 else len(md)]
        nm = re.search(r"\*\*ナレーション：\*\*\s*(.+?)(?=\n---|\n\*\*|\Z)", span, re.S)
        if nm:
            hook = strip_quotes(nm.group(1))
    if not hook:
        return None
    return {"num": num, "title": title, "goal": goal, "hook": hook,
            "slug": os.path.basename(ep_dir)}


def render(ep: dict, video: str | None, note: str | None) -> str:
    subject = re.sub(r"【[^】]*】", "", ep["title"]).strip()  # 件名は【】を外す
    hook = first_sentences(ep["hook"], 3)

    L = [f"件名: {subject}", "", "---", "", "こんにちは、AI時代のマーケティング・ラボです。", "",
         "今週の動画のさわりを、3分だけ。", "", hook, ""]
    if ep["goal"]:
        L += [f"この続きでは、{ep['goal']}——そんな状態を目指します。", ""]
    L += ["続きは動画でどうぞ（約9分・図解つき）👇", ""]
    L.append(f"🎬 {video or DEFAULT_CHANNEL}")
    if note:
        L += ["", f"📝 文章で読みたい方はこちら → {note}"]
    L += ["", "━━━━━━━━━━",
          "＜まだの方へ＞ 全20話の要点を1枚にまとめた無料チートシート（PDF）を配布中です。",
          f"👉 {OPT_IN}",
          "", "それでは、また来週。", "AI時代のマーケティング・ラボ",
          "", "※配信停止はこのメール下部からいつでも可能です。"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", required=True)
    ap.add_argument("--note", help="該当回の note記事URL（任意）")
    ap.add_argument("--out-dir", default="_deliverables/broadcast")
    ap.add_argument("--root", default=".")
    a = ap.parse_args()

    ep = parse(a.episode.rstrip("/"))
    if not ep:
        sys.exit(f"フック/タイトルを抽出できない（テンプレ回？）: {a.episode}")
    video = os.environ.get("NOTE_VIDEO_URL") or resolve_video_url(a.root, ep["num"])
    out = render(ep, video, a.note)

    os.makedirs(a.out_dir, exist_ok=True)
    slug = ep["slug"].split("_", 1)[-1]
    path = os.path.join(a.out_dir, f"ep{ep['num']:02d}_{slug}.md")
    open(path, "w", encoding="utf-8").write(out)
    print(f"EP{ep['num']:02d} 週次メール草稿 → {path}")
    print(f"  件名: {re.sub(r'【[^】]*】', '', ep['title']).strip()}")
    print(f"  動画: {video or '（未公開＝チャンネルURL）'}")


if __name__ == "__main__":
    main()
