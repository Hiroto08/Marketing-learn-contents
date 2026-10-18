#!/usr/bin/env python3
"""
sync_playlists.py — シリーズ再生リスト（全話・章別・Shorts）を YouTube 実体と同期する。

- 再生リストはタイトルで照合し、無ければ作成（public）。
- 回の判定は yt_index（タグ mlab-epNN / mlab-epNN-sM）。
- 既に入っている動画は飛ばし、足りない動画だけを EP順の正しい位置（snippet.position）へ挿入。
  → 何度実行しても安全（冪等）。新しい回をアップした後に1回流せば再生リストに並ぶ。
- 非公開動画も追加される（視聴者には公開された時点から表示される）。

クォータ: 一覧 1単位/ページ、作成・挿入 50単位/件。

使い方:
  python3 _tools/publish/sync_playlists.py            # 同期
  python3 _tools/publish/sync_playlists.py --dry-run  # 追加予定だけ表示
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yt_index import API, api, episode_index, token  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import series as S  # noqa: E402  シリーズ固有の値（series.json）

SUFFIX = f"\n\n▼無料特典：{S.LEAD_MAGNET}\n{S.OPTIN_URL}\n\n{S.VOICE_CREDIT}"

# 再生リスト（タイトル・説明・対象EP範囲・本編/Shorts）は series.json の youtube.playlists
PLAYLISTS = [(p["title"], p["description"], range(p["episodes"][0], p["episodes"][1] + 1), p["kind"])
             for p in S.YT["playlists"]]


def post(tok, path, body):
    req = urllib.request.Request(f"{API}/{path}", data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def items(tok, pid):
    out, page = [], None
    while True:
        q = {"part": "contentDetails", "playlistId": pid, "maxResults": "50"}
        if page:
            q["pageToken"] = page
        try:
            r = api(tok, "playlistItems", q)
        except urllib.error.HTTPError:   # 作成直後は404になることがある
            return out
        out += [i["contentDetails"]["videoId"] for i in r["items"]]
        page = r.get("nextPageToken")
        if not page:
            return list(dict.fromkeys(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    tok = token()
    idx = episode_index(tok)
    existing = {p["snippet"]["title"]: p["id"]
                for p in api(tok, "playlists", {"part": "snippet", "mine": "true", "maxResults": "50"})["items"]}
    for title, desc, eps, kind in PLAYLISTS:
        want = []
        for ep in eps:
            s = idx.get(ep)
            if not s:
                continue
            if kind == "main" and s["main"]:
                want.append(s["main"])
            if kind == "shorts":
                want += [s["shorts"][n] for n in sorted(s["shorts"])]
        pid = existing.get(title)
        if not pid:
            if a.dry_run:
                print(f"[dry] 作成予定 {title[:40]}（{len(want)}本）")
                continue
            pid = post(tok, "playlists?part=snippet,status",
                       {"snippet": {"title": title, "description": desc + SUFFIX, "defaultLanguage": "ja"},
                        "status": {"privacyStatus": "public"}})["id"]
        have = items(tok, pid)
        added = 0
        for v in want:
            if v in have:
                continue
            # EP順で直前にあるべき動画の、現在の並びの直後に挿入
            prev = [w for w in want[:want.index(v)] if w in have]
            pos = have.index(prev[-1]) + 1 if prev else 0
            if a.dry_run:
                print(f"[dry] {title[:24]}… に {v} を位置{pos}へ")
                have.insert(pos, v)
                continue
            for attempt in range(3):
                try:
                    post(tok, "playlistItems?part=snippet",
                         {"snippet": {"playlistId": pid, "position": pos,
                                      "resourceId": {"kind": "youtube#video", "videoId": v}}})
                    have.insert(pos, v)
                    added += 1
                    break
                except urllib.error.HTTPError as e:
                    msg = e.read().decode()[:160]
                    if e.code == 403:
                        sys.exit(f"403で停止（quota/権限）: {msg}\n翌日16:00 JST以降に再実行すれば続きから同期する")
                    if e.code == 409 and attempt < 2:   # 一時的な "operation aborted"
                        time.sleep(3)
                        continue
                    print(f"  FAIL {v} {e.code} {msg}")
                    break
        print(f"{pid} +{added}（{len([w for w in want if w in have])}/{len(want)}） {title[:40]}")


if __name__ == "__main__":
    main()
