#!/usr/bin/env python3
"""公開後のYouTube実測を取得して yt-analyst の改善ループを閉じるスクリプト。

これまで「数値はユーザーが手で貼る」前提だった yt-analyst の入力を自動化する。
YouTube Analytics API から CTR・平均維持率・30秒残存・維持率カーブ（急落地点）・
流入元を取り、改革計画 §1 のKPIと突き合わせた Markdown レポートを出力する。

    # 1話ぶん（publish_manifest.json の本編videoIdを自動検出）
    python3 _tools/publish/fetch_analytics.py --episode 01_beginner/ep01_what-is-marketing

    # videoId 直接指定 / 期間指定（既定は直近28日）
    python3 _tools/publish/fetch_analytics.py --video VIDEOID --days 7

    # チャンネル全体のサマリ（YPP進捗確認用：総再生時間・登録者増）
    python3 _tools/publish/fetch_analytics.py --channel --days 28

認証: upload_youtube.py と同じ YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN。
      ただし Analytics 取得には yt-analytics.readonly スコープが要るため、
      get_refresh_token.py を **一度だけ再実行**してトークンを取り直すこと
      （アップロード用の既存トークンのままだと 403 になる）。

出力: 標準出力に Markdown。--out <path> でファイル保存も可。
      yt-analyst はこの結果を retention-packaging.md §7 に日付つきで書き戻す。
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

import requests

# access_token は upload_youtube.py と共通（同一ディレクトリなので import 可能）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upload_youtube import access_token  # noqa: E402

DATA_API = "https://www.googleapis.com/youtube/v3"
ANALYTICS_API = "https://youtubeanalytics.googleapis.com/v2/reports"

# 改革計画 §1 のKPIライン（判定に使う）
KPI = {
    "ctr_floor": 2.0, "ctr_pass": 4.0, "ctr_good": 7.0,      # %（サムネCTR）
    "ret30_min": 60.0, "ret30_target": 70.0,                 # %（30秒残存）
    "avgret_min": 35.0, "avgret_target": 45.0,               # %（平均視聴維持率）
}


def _query(tok: str, params: dict) -> dict:
    r = requests.get(ANALYTICS_API, params=params,
                     headers={"Authorization": f"Bearer {tok}"}, timeout=60)
    if r.status_code == 403:
        sys.exit("403: yt-analytics.readonly スコープが無いトークン。\n"
                 "get_refresh_token.py を再実行して YT_REFRESH_TOKEN を取り直す。")
    if r.status_code != 200:
        sys.exit(f"Analytics API {r.status_code}: {r.text[:400]}")
    return r.json()


def _rows(resp: dict) -> list:
    return resp.get("rows", []) or []


def video_duration_seconds(tok: str, video_id: str) -> int | None:
    r = requests.get(f"{DATA_API}/videos", params={
        "part": "contentDetails", "id": video_id},
        headers={"Authorization": f"Bearer {tok}"}, timeout=30)
    if r.status_code != 200 or not r.json().get("items"):
        return None
    iso = r.json()["items"][0]["contentDetails"]["duration"]  # PT8M42S
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def _mmss(sec: float) -> str:
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def core_metrics(tok: str, video_id: str, start: str, end: str) -> dict:
    resp = _query(tok, {
        "ids": "channel==MINE", "startDate": start, "endDate": end,
        "metrics": ("views,estimatedMinutesWatched,averageViewDuration,"
                    "averageViewPercentage,subscribersGained,subscribersLost"),
        "filters": f"video=={video_id}"})
    cols = [h["name"] for h in resp.get("columnHeaders", [])]
    rows = _rows(resp)
    return dict(zip(cols, rows[0])) if rows else {}


def ctr_metrics(tok: str, video_id: str, start: str, end: str) -> dict:
    # 2026-01 追加メトリクス。古い環境では未提供のことがあるので失敗は握りつぶす
    try:
        resp = _query(tok, {
            "ids": "channel==MINE", "startDate": start, "endDate": end,
            "metrics": "videoThumbnailImpressions,videoThumbnailImpressionsClickRate",
            "filters": f"video=={video_id}"})
    except SystemExit:
        return {}
    cols = [h["name"] for h in resp.get("columnHeaders", [])]
    rows = _rows(resp)
    return dict(zip(cols, rows[0])) if rows else {}


def retention_curve(tok: str, video_id: str, start: str, end: str) -> list:
    resp = _query(tok, {
        "ids": "channel==MINE", "startDate": start, "endDate": end,
        "dimensions": "elapsedVideoTimeRatio",
        "metrics": "audienceWatchRatio,relativeRetentionPerformance",
        "filters": f"video=={video_id}", "sort": "elapsedVideoTimeRatio"})
    return _rows(resp)  # [[ratio, audienceWatchRatio, relRetPerf], ...] 100点


def traffic_sources(tok: str, video_id: str, start: str, end: str) -> list:
    resp = _query(tok, {
        "ids": "channel==MINE", "startDate": start, "endDate": end,
        "dimensions": "insightTrafficSourceType",
        "metrics": "views,estimatedMinutesWatched",
        "filters": f"video=={video_id}", "sort": "-views"})
    return _rows(resp)


def channel_summary(tok: str, start: str, end: str) -> dict:
    resp = _query(tok, {
        "ids": "channel==MINE", "startDate": start, "endDate": end,
        "metrics": ("views,estimatedMinutesWatched,averageViewPercentage,"
                    "subscribersGained,subscribersLost")})
    cols = [h["name"] for h in resp.get("columnHeaders", [])]
    rows = _rows(resp)
    return dict(zip(cols, rows[0])) if rows else {}


def episode_video_id(ep_dir: str) -> str | None:
    """publish_manifest.json から本編（Shortsでない *_final.mp4）の videoId を拾う"""
    p = f"{ep_dir.rstrip('/')}/publish_manifest.json"
    if not os.path.exists(p):
        return None
    man = json.load(open(p, encoding="utf-8"))
    for fname, rec in man.items():
        if "short" not in fname.lower():
            return rec.get("videoId")
    return next(iter(man.values()), {}).get("videoId")


def _flag(val: float | None, floor: float, target: float) -> str:
    if val is None:
        return "—"
    if val >= target:
        return "✅ 目標達成"
    if val >= floor:
        return "△ 最低ライン超"
    return "🔴 未達"


def build_report(tok: str, video_id: str, start: str, end: str) -> str:
    dur = video_duration_seconds(tok, video_id)
    core = core_metrics(tok, video_id, start, end)
    ctr = ctr_metrics(tok, video_id, start, end)
    curve = retention_curve(tok, video_id, start, end)
    traffic = traffic_sources(tok, video_id, start, end)

    avg_ret = core.get("averageViewPercentage")
    ctr_rate = ctr.get("videoThumbnailImpressionsClickRate")  # 0-100? APIは%表記
    # 30秒残存：カーブから elapsed=30/dur に最も近い点の audienceWatchRatio
    ret30 = None
    if curve and dur:
        target_ratio = 30.0 / dur
        near = min(curve, key=lambda row: abs(row[0] - target_ratio))
        ret30 = near[1] * 100.0

    L = [f"# 実測レポート — video {video_id}",
         f"期間: {start} 〜 {end}／尺: {_mmss(dur) if dur else '不明'}",
         "",
         "## KPI比較（改革計画 §1）",
         "| 指標 | 実測 | 最低 | 目標 | 判定 |",
         "|------|------|------|------|------|"]
    L.append(f"| サムネCTR | {f'{ctr_rate:.1f}%' if ctr_rate is not None else '—'} | "
             f"{KPI['ctr_floor']}% | {KPI['ctr_pass']}% | "
             f"{_flag(ctr_rate, KPI['ctr_floor'], KPI['ctr_pass'])} |")
    L.append(f"| 30秒残存 | {f'{ret30:.0f}%' if ret30 is not None else '—'} | "
             f"{KPI['ret30_min']:.0f}% | {KPI['ret30_target']:.0f}% | "
             f"{_flag(ret30, KPI['ret30_min'], KPI['ret30_target'])} |")
    L.append(f"| 平均視聴維持率 | {f'{avg_ret:.0f}%' if avg_ret is not None else '—'} | "
             f"{KPI['avgret_min']:.0f}% | {KPI['avgret_target']:.0f}% | "
             f"{_flag(avg_ret, KPI['avgret_min'], KPI['avgret_target'])} |")
    L.append("")
    L.append(f"- 再生数: {core.get('views', '—')}／"
             f"総再生分: {core.get('estimatedMinutesWatched', '—')}／"
             f"平均視聴: {_mmss(core.get('averageViewDuration', 0)) if core.get('averageViewDuration') else '—'}／"
             f"登録: +{core.get('subscribersGained', 0)} / -{core.get('subscribersLost', 0)}")

    # 急落地点（隣接点の audienceWatchRatio 低下が大きい順に上位3つ）
    L += ["", "## 維持率の急落地点（構成の敗因逆引き用）"]
    if curve and dur:
        drops = []
        for i in range(1, len(curve)):
            prev, cur = curve[i - 1], curve[i]
            delta = (prev[1] - cur[1]) * 100.0  # %ポイント低下
            t = cur[0] * dur
            drops.append((delta, _mmss(t), cur[0]))
        drops.sort(reverse=True)
        L.append("| 順位 | 時点 | 低下幅(pt) | 該当スライド逆引きの目安 |")
        L.append("|------|------|-----------|--------------------------|")
        for rank, (delta, t, ratio) in enumerate(drops[:3], 1):
            slide = min(18, max(1, round(ratio * 18)))
            L.append(f"| {rank} | {t} | {delta:.1f} | S{slide}前後（script.mdを確認）|")
        L.append("\n> script.md の該当タイムスタンプ・スライドを開き、"
                 "長い前置き／図なし説明／静止区間のどれかを特定 → §7へ書き戻す。")
    else:
        L.append("（維持率カーブ未取得：視聴数が閾値未満か、公開直後）")

    L += ["", "## 流入元"]
    if traffic:
        L.append("| ソース | 再生数 | 総再生分 |")
        L.append("|--------|--------|----------|")
        label = {"YT_SEARCH": "検索", "SHORTS": "Shortsフィード",
                 "SUGGESTED_VIDEO": "関連動画", "BROWSE": "ブラウジング",
                 "EXT_URL": "外部URL", "NO_LINK_OTHER": "直接/その他",
                 "PLAYLIST": "再生リスト", "SUBSCRIBER": "登録フィード"}
        for src, views, mins in traffic:
            L.append(f"| {label.get(src, src)} | {views} | {mins} |")
    else:
        L.append("（流入データなし）")

    L += ["", "---", "_yt-analyst へ_: この結果を "
          "`.claude/skills/episode-production/retention-packaging.md` §7 に "
          "`- YYYY-MM-DD EP◯◯: 事象 → ルール変更` の形式で追記すること。"]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", help="publish_manifest.json から本編videoIdを自動検出")
    ap.add_argument("--video", help="videoId 直接指定")
    ap.add_argument("--channel", action="store_true", help="チャンネル全体サマリ")
    ap.add_argument("--days", type=int, default=28, help="遡る日数（既定28）")
    ap.add_argument("--out", help="Markdownを保存するパス")
    a = ap.parse_args()

    end = dt.date.today()
    start = end - dt.timedelta(days=a.days)
    s, e = start.isoformat(), end.isoformat()
    tok = access_token()

    if a.channel:
        c = channel_summary(tok, s, e)
        out = (f"# チャンネルサマリ {s}〜{e}\n"
               f"- 再生数: {c.get('views', '—')}\n"
               f"- 総再生時間: {c.get('estimatedMinutesWatched', 0)}分 "
               f"（≒{c.get('estimatedMinutesWatched', 0)/60:.0f}時間 / YPP Tier2は4,000時間）\n"
               f"- 平均維持率: {c.get('averageViewPercentage', '—')}%\n"
               f"- 登録: +{c.get('subscribersGained', 0)} / -{c.get('subscribersLost', 0)}")
    else:
        vid = a.video or (episode_video_id(a.episode) if a.episode else None)
        if not vid:
            ap.error("--video / --episode（manifestにvideoId有り）/ --channel のいずれかが必要")
        out = build_report(tok, vid, s, e)

    print(out)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print(f"\n（保存: {a.out}）", file=sys.stderr)


if __name__ == "__main__":
    main()
