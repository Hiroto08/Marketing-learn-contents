#!/usr/bin/env python3
"""
publish_episode.py — 既に非公開(private)でアップロード済みのエピソードを
「本編＋その回のShorts」まとめて公開／公開予約する。

設計思想（EP20飛び級公開事故の再発防止 2026-08）:
- 公開は必ずEP番号の昇順。EPn を公開する前に EP1..(n-1) の本編が全て public
  であることを確認し、そうでなければ拒否（--force で上書き可）。
- 本編とその回の Shorts は必ず同時に同じ状態へ（public / 同じ publishAt）。

回の判定は動画タグ mlab-epNN / mlab-epNN-sM（yt_index.py。公開タイトルに「第N回」は入れない）。

使い方:
  python3 _tools/publish/publish_episode.py --episode 03_practical/ep10_copywriting-5laws
  python3 _tools/publish/publish_episode.py --episode <ep_dir> --at 2026-10-24T18:00:00+09:00
  python3 _tools/publish/publish_episode.py --episode <ep_dir> --dry-run
必要スコープ: https://www.googleapis.com/auth/youtube（videos.update）
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yt_index import API, episode_index, public_max_ep, token  # noqa: E402


def set_privacy(tok, v, at=None, dry=False):
    vid, st, title = v["id"], v["status"], v["snippet"]["title"][:34]
    status = {"selfDeclaredMadeForKids": st.get("selfDeclaredMadeForKids", False),
              "license": st.get("license", "youtube"), "embeddable": st.get("embeddable", True),
              "publicStatsViewable": st.get("publicStatsViewable", True)}
    if at:
        status["privacyStatus"] = "private"
        status["publishAt"] = at
    else:
        status["privacyStatus"] = "public"
    if dry:
        return f"[dry] {vid} [{title}] -> {'予約 ' + at if at else 'public'}"
    req = urllib.request.Request(f"{API}/videos?part=status", data=json.dumps({"id": vid, "status": status}).encode(),
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"},
                                 method="PUT")
    try:
        s = json.load(urllib.request.urlopen(req, timeout=30))["status"]
        return f"{vid} [{title}] -> {s['privacyStatus']}" + (f" @ {s.get('publishAt')}" if s.get("publishAt") else "")
    except urllib.error.HTTPError as e:
        return f"{vid} [{title}]: FAIL {e.code} {e.read().decode()[:150]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", required=True, help="エピソードディレクトリ")
    ap.add_argument("--at", help="RFC3339の公開予約日時（例 2026-10-24T18:00:00+09:00）。省略で即時public")
    ap.add_argument("--force", action="store_true", help="EP順ガードを無視して公開する")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ep = int(re.search(r"ep(\d+)", os.path.basename(a.episode.rstrip("/"))).group(1))
    tok = token()
    idx = episode_index(tok)
    s = idx.get(ep)
    if not s or not s["main"]:
        sys.exit(f"EP{ep:02d} の本編がYouTube上に見つからない（未アップロード？）: {a.episode}")
    mx = public_max_ep(idx)
    if ep > mx + 1 and not a.force:
        sys.exit(f"公開順序ガード: EP{ep:02d} は公開できません。現在 public 済み最大は EP{mx:02d} で、"
                 f"次に公開してよいのは EP{mx + 1:02d} のみです（--force で上書き可）。")
    shorts = [s["shorts"][n] for n in sorted(s["shorts"])]
    print(f"EP{ep:02d} を{'予約公開(' + a.at + ')' if a.at else '公開'}（本編＋Shorts{len(shorts)}本 同時）")
    print("  本編 :", set_privacy(tok, s["items"][s["main"]], a.at, a.dry_run))
    for vid in shorts:
        print("  Short:", set_privacy(tok, s["items"][vid], a.at, a.dry_run))
    if not shorts:
        print("  ! この回の Shorts が見つからない（未UP）。本編のみ処理した。")


if __name__ == "__main__":
    main()
