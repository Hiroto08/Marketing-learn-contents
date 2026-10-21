#!/usr/bin/env python3
"""
weekly_stats.py — YouTube Data API の公開統計（再生・高評価・コメント・登録者）を週次で記録し、
前回スナップショットとの差分レポートを docs/weekly-stats.md に書く。

Analytics API（yt-analytics.readonly）が使えない間の代替。CTR・維持率は取れないが、
「どの動画が伸びたか／登録者が増えたか」の週次推移は追える。クォータ数単位。

  python3 _tools/publish/weekly_stats.py
出力: docs/stats/YYYY-MM-DD.json（スナップショット・コミットする）／docs/weekly-stats.md（最新レポート）
"""
import datetime
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yt_index import _duration_sec, api, episode_index, privacy, token  # noqa: E402


def main():
    tok = token()
    ch = api(tok, "channels", {"part": "statistics,snippet", "mine": "true"})["items"][0]
    idx = episode_index(tok)
    today = datetime.date.today().isoformat()
    snap = {"date": today, "channel": {k: int(v) for k, v in ch["statistics"].items() if isinstance(v, str) and v.isdigit()}, "videos": {}}
    for ep, s in idx.items():
        for vid, v in s["items"].items():
            st = v.get("statistics", {})
            snap["videos"][vid] = {
                "ep": ep, "kind": "main" if vid == s["main"] else "short", "title": v["snippet"]["title"],
                "privacy": privacy(v), "sec": _duration_sec(v["contentDetails"]["duration"]),
                "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0))}
    os.makedirs("docs/stats", exist_ok=True)
    prevs = sorted(p for p in glob.glob("docs/stats/*.json") if not p.endswith(f"{today}.json"))
    prev = json.load(open(prevs[-1], encoding="utf-8")) if prevs else None
    json.dump(snap, open(f"docs/stats/{today}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    def d(vid, k):
        if not prev or vid not in prev["videos"]:
            return None
        return snap["videos"][vid][k] - prev["videos"][vid][k]

    c, pc = snap["channel"], (prev or {}).get("channel", {})
    o = [f"# 週次統計（{ch['snippet']['title']}）\n\n",
         f"> 自動生成 {today}／比較対象 {prev['date'] if prev else 'なし（初回）'}／ソース：YouTube Data API 公開統計"
         "（CTR・維持率は Analytics API の再認可後に fetch_analytics.py で取得）\n\n",
         "## チャンネル\n\n| 指標 | 現在 | 前回比 |\n|---|---|---|\n"]
    for k, name in [("subscriberCount", "登録者"), ("viewCount", "総再生"), ("videoCount", "動画数")]:
        delta = (f"{c.get(k, 0) - pc[k]:+d}" if k in pc else "—")
        o.append(f"| {name} | {c.get(k, 0)} | {delta} |\n")
    for kind, label in [("main", "本編"), ("short", "Shorts")]:
        rows = [(vid, v) for vid, v in snap["videos"].items() if v["kind"] == kind and v["privacy"] == "public"]
        rows.sort(key=lambda t: (-(d(t[0], "views") or 0), -t[1]["views"]))
        tot = sum(v["views"] for _, v in rows)
        wk = sum(d(vid, "views") or 0 for vid, _ in rows)
        o.append(f"\n## {label}（公開 {len(rows)}本・累計 {tot}再生・前回比 {wk:+d}）\n\n"
                 "| EP | タイトル | 再生 | 前回比 | 高評価 | コメント |\n|---|---|---|---|---|---|\n")
        for vid, v in rows[:15]:
            dv = d(vid, "views")
            o.append(f"| EP{v['ep']:02d} | [{v['title'][:30]}](https://youtu.be/{vid}) | {v['views']} | "
                     f"{'—' if dv is None else f'{dv:+d}'} | {v['likes']} | {v['comments']} |\n")
    open("docs/weekly-stats.md", "w", encoding="utf-8").write("".join(o))
    print(f"saved docs/stats/{today}.json  subs={c.get('subscriberCount')} views={c.get('viewCount')}"
          f"  prev={prev['date'] if prev else None}")


if __name__ == "__main__":
    main()
