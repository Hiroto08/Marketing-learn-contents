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
from yt_index import _duration_sec, api, channel_videos, episode_index, privacy, token  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import series as S  # noqa: E402


def main():
    tok = token()
    ch = api(tok, "channels", {"part": "statistics,snippet", "mine": "true"})["items"][0]
    videos = channel_videos(tok)
    idx = episode_index(tok, videos)
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
    # 第2シリーズ（売れる仕組みの裏側）：タグ mlab-uNN / mlab-cNN
    snap["s2"] = {}
    for vid, v in videos.items():
        for t in v["snippet"].get("tags", []):
            m = S.S2_TAG_RE.match(t)
            if m:
                st = v.get("statistics", {})
                snap["s2"][vid] = {"id": f"{m[1]}{m[2]}", "kind": "case" if m[1] == "c" else "short",
                                   "title": v["snippet"]["title"], "privacy": privacy(v),
                                   "publishAt": v["status"].get("publishAt"), "publishedAt": v["snippet"].get("publishedAt"),
                                   "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
                                   "comments": int(st.get("commentCount", 0))}
                break
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
    o += s2_section(snap, prev) + note_section() + kit_section()
    open("docs/weekly-stats.md", "w", encoding="utf-8").write("".join(o))
    print(f"saved docs/stats/{today}.json  subs={c.get('subscriberCount')} views={c.get('viewCount')}"
          f"  prev={prev['date'] if prev else None}")


CA = "/root/.ccr/ca-bundle.crt"


def s2_section(snap, prev):
    """第2シリーズの回ごとの再生。Shorts は公開7日でほぼ出尽くす（v0.2 §3-1）ので「公開からの日数」を添える"""
    rows = sorted(snap.get("s2", {}).items(), key=lambda t: t[1]["id"])
    if not rows:
        return []
    pv = (prev or {}).get("s2", {})
    today = datetime.date.fromisoformat(snap["date"])
    o = [f"\n## {S.S2_NAME}（第2シリーズ）\n\n| 回 | 鮮度 | タイトル | 状態 | 公開から | 再生 | 前回比 | 高評価 |\n|---|---|---|---|---|---|---|---|\n"]
    groups = {}
    for vid, v in rows:
        days, nd = "—", None
        if v["privacy"] == "public":
            pub = (v.get("publishAt") or v.get("publishedAt") or "")[:10]
            if pub:
                nd = (today - datetime.date.fromisoformat(pub)).days
                days = f"{nd}日"
        fr = _freshness(v["id"])
        if v["kind"] == "short" and nd is not None and nd >= 7:   # Shorts は7日でほぼ出尽くす（v0.2 §3-1）
            groups.setdefault(fr.split("（")[0] or "不明", []).append(v["views"])
        d = v["views"] - pv[vid]["views"] if vid in pv else None
        o.append(f"| {v['id']} | {fr or '—'} | [{v['title'][:30]}](https://youtu.be/{vid}) | {v['privacy']} | {days} | {v['views']} | "
                 f"{'—' if d is None else f'{d:+d}'} | {v['likes']} |\n")
    if groups:
        import statistics
        o.append("\n公開7日以上の Shorts の再生（中央値）：" + "／".join(
            f"{k} {statistics.median(vs):.0f}（{len(vs)}本）" for k, vs in sorted(groups.items())) + "（作戦 v0.2 §5.1 の時事と古典の比較）\n")
    return o


def _freshness(item_id):
    """s2_ura/uNN_*/shorts.md の **鮮度：** 時事（YYYY-MM）／古典（YYYY）"""
    import re as _re
    for p in glob.glob(f"{S.S2_DIR}/{item_id}_*/shorts.md"):
        m = _re.search(r"\*\*鮮度：\*\*\s*(\S+)", open(p, encoding="utf-8").read())
        if m:
            return m.group(1)
    return ""


def note_section():
    """note の閲覧数（note のダッシュボードと同じ GET /api/v1/stats/pv・読み取りのみ）。Cookie が無ければ省略"""
    ck = os.environ.get("_note_session_v5")
    if not ck:
        return ["\n## note\n\n（_note_session_v5 が無いため未取得）\n"]
    try:
        import requests
        out = ["\n## note（記事の閲覧数）\n\n| 期間 | 閲覧 | スキ |\n|---|---|---|\n"]
        weekly = []
        for flt, label in [("weekly", "直近7日"), ("all", "全期間")]:
            r = requests.get("https://note.com/api/v1/stats/pv", params={"filter": flt, "page": 1, "sort": "pv"},
                             cookies={"_note_session_v5": ck}, verify=CA, timeout=30,
                             headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"})
            dd = r.json().get("data", {}) if r.status_code == 200 else {}
            if not dd:
                return [f"\n## note\n\n（取得失敗 {r.status_code}。Cookie 期限切れの可能性）\n"]
            out.append(f"| {label} | {dd.get('total_pv', 0)} | {dd.get('total_like', 0)} |\n")
            if flt == "weekly":
                weekly = dd.get("note_stats") or []
        out.append("\n| 直近7日の記事 | 閲覧 | スキ |\n|---|---|---|\n")
        for n in sorted(weekly, key=lambda n: -int(n.get("read_count") or 0))[:10]:
            out.append(f"| {(n.get('name') or '')[:36]} | {n.get('read_count', 0)} | {n.get('like_count', 0)} |\n")
        return out
    except Exception as e:  # noqa: BLE001  統計は非致命
        return [f"\n## note\n\n（取得失敗：{str(e)[:80]}）\n"]


def kit_section():
    """Kit の購読者数と直近の送信済みメールの開封率（v4 API・読み取りのみ）。キーが無ければ省略"""
    key = os.environ.get("KIT_API_KEY")
    if not key:
        return ["\n## メール（Kit）\n\n（KIT_API_KEY が無いため未取得）\n"]
    try:
        import requests
        h = {"X-Kit-Api-Key": key, "Accept": "application/json"}
        r = requests.get("https://api.kit.com/v4/subscribers", params={"per_page": 1, "include_total_count": "true",
                                                                        "status": "active"}, headers=h, verify=CA, timeout=30)
        total = (r.json().get("pagination") or {}).get("total_count") if r.status_code == 200 else None
        out = [f"\n## メール（Kit）\n\n- 購読者（有効）：{total if total is not None else f'取得失敗 {r.status_code}'}\n"]
        r = requests.get("https://api.kit.com/v4/broadcasts", params={"per_page": 100, "slim": "true", "status": "completed"},
                         headers=h, verify=CA, timeout=30)
        sent = sorted((r.json().get("broadcasts") or []) if r.status_code == 200 else [],
                      key=lambda b: b.get("send_at") or "", reverse=True)[:5]
        if sent:
            out.append("\n| 送信日 | 件名 | 受信 | 開封率 | クリック率 |\n|---|---|---|---|---|\n")
        for b in sent:
            s = requests.get(f"https://api.kit.com/v4/broadcasts/{b['id']}/stats", headers=h, verify=CA, timeout=30)
            st = ((s.json().get("broadcast") or {}).get("stats") or {}) if s.status_code == 200 else {}
            out.append(f"| {(b.get('send_at') or '')[:10]} | {(b.get('subject') or '')[:30]} | {st.get('recipients', '—')} | "
                       f"{st.get('open_rate', '—')} | {st.get('click_rate', '—')} |\n")
        return out
    except Exception as e:  # noqa: BLE001
        return [f"\n## メール（Kit）\n\n（取得失敗：{str(e)[:80]}）\n"]


if __name__ == "__main__":
    main()
