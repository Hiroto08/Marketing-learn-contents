#!/usr/bin/env python3
"""
ura_schedule.py — 第2シリーズ「売れる仕組みの裏側」の公開予約と状態表。

24話側（publish_episode.py）とは別の公開ルール（docs/post-series-strategy.md v0.2 §8、2026-11-04 承認）:
- Shorts（s2_ura/uNN_*）は毎日1本、本編ケースファイル（s2_ura/cNN_*）は週1本。本編と Shorts の同時公開は求めない。
- 飛び級は禁止：同じ種類（u／c）の中で、番号の小さい回より先に大きい回を公開・予約しない。
  予定日（s2_ura/schedule.json）は番号順に昇順（同じ日は可）でなければ全体を拒否する。
- 公開済み（public）の動画には触らない。非公開アップ済みの動画に publishAt を付けるだけ（予定時刻に YouTube が公開）。

  python3 _tools/publish/ura_schedule.py              # 状態表 s2_ura/STATUS.md を更新（読み取りのみ）
  python3 _tools/publish/ura_schedule.py --apply      # schedule.json の予定どおりに公開予約（冪等）
  python3 _tools/publish/ura_schedule.py --apply --dry-run
  python3 _tools/publish/ura_schedule.py --playlist   # シリーズの再生リストを作成し、予定順に追加（冪等）

schedule.json の形式: {"playlist_id": null, "items": [{"id": "u01", "date": "2026-11-15"}, ...]}
  時刻は series.json の series2.youtube_hour_jst（既定18時）。
動画の判定は publish_manifest.json の videoId（uNN は shorts_build/short1/ 内、cNN は直下）。
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yt_index import API, api, token  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import series as S  # noqa: E402

JST = dt.timezone(dt.timedelta(hours=9))
ROOT = S.S2_DIR
SCHED = f"{ROOT}/schedule.json"


def item_dir(iid):
    ds = [d for d in glob.glob(f"{ROOT}/{iid}_*") if os.path.isdir(d)]
    return ds[0] if ds else None


def video_id(d):
    if not d:
        return None
    kind = os.path.basename(d)[0]
    p = f"{d}/shorts_build/short1/publish_manifest.json" if kind == "u" else f"{d}/publish_manifest.json"
    if not os.path.exists(p):
        return None
    for k, v in json.load(open(p, encoding="utf-8")).items():
        if k.endswith("_final.mp4") and v.get("videoId"):
            return v["videoId"]
    return None


def slot(date):
    return dt.datetime.fromisoformat(date).replace(hour=S.S2_HOUR, tzinfo=JST)


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load():
    sc = json.load(open(SCHED, encoding="utf-8"))
    rows = []
    for it in sc["items"]:
        d = item_dir(it["id"])
        rows.append({"id": it["id"], "kind": it["id"][0], "no": int(it["id"][1:]), "date": it["date"],
                     "at": slot(it["date"]), "dir": d, "vid": video_id(d)})
    return sc, rows


def check_order(rows):
    errs = []
    for kind in "uc":
        ks = sorted([r for r in rows if r["kind"] == kind], key=lambda r: r["no"])
        for a, b in zip(ks, ks[1:]):
            if a["at"] > b["at"]:   # 同じ日にまとめて出すのは可（§4.6 の2週目）。番号が後の回を先にしない
                errs.append(f"{a['id']}（{a['date']}）→ {b['id']}（{b['date']}）が番号順に昇順でない")
    return errs


def fetch(tok, vids):
    out = {}
    vids = [v for v in vids if v]
    for i in range(0, len(vids), 50):
        for v in api(tok, "videos", {"part": "status,snippet,statistics", "id": ",".join(vids[i:i + 50])}).get("items", []):
            out[v["id"]] = v
    return out


def set_at(tok, v, at, dry):
    st = v["status"]
    status = {"privacyStatus": "private", "publishAt": at,
              "selfDeclaredMadeForKids": st.get("selfDeclaredMadeForKids", False),
              "license": st.get("license", "youtube"), "embeddable": st.get("embeddable", True),
              "publicStatsViewable": st.get("publicStatsViewable", True)}
    if dry:
        return "[dry] 予約 " + at
    req = urllib.request.Request(f"{API}/videos?part=status", data=json.dumps({"id": v["id"], "status": status}).encode(),
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"}, method="PUT")
    try:
        s = json.load(urllib.request.urlopen(req, timeout=30))["status"]
        return f"{s['privacyStatus']} @ {s.get('publishAt')}"
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        if e.code == 403 and "quota" in body.lower():
            raise SystemExit("quotaExceeded: 翌日16:00 JST以降に同じコマンドで再開")
        return f"FAIL {e.code} {body}"


def state(v):
    if not v:
        return "未アップ"
    p = v["status"]["privacyStatus"]
    if p == "private" and v["status"].get("publishAt"):
        return "予約済み"
    return {"public": "公開済み", "private": "非公開", "unlisted": "限定公開"}.get(p, p)


def superseded_ids():
    """差し替えで旧版になった videoId（manifest の supersededVideoId）。Issue #2：旧動画は削除せず非公開のまま残す"""
    out = set()
    for p in glob.glob(f"{ROOT}/*/publish_manifest.json") + glob.glob(f"{ROOT}/*/shorts_build/short*/publish_manifest.json"):
        for v in json.load(open(p, encoding="utf-8")).values():
            if isinstance(v, dict) and v.get("supersededVideoId"):
                out.add(v["supersededVideoId"])
    return out


def unschedule_superseded(tok, dry):
    """旧版に公開予約（publishAt）が残っていると、差し替えたのに旧版も公開されてしまう → 予約だけ外して非公開のまま残す"""
    old = superseded_ids()
    if not old:
        return
    for vid, v in fetch(tok, list(old)).items():
        st = v["status"]
        if st["privacyStatus"] == "private" and st.get("publishAt"):
            body = {"id": vid, "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": st.get("selfDeclaredMadeForKids", False),
                                          "license": st.get("license", "youtube"), "embeddable": st.get("embeddable", True),
                                          "publicStatsViewable": st.get("publicStatsViewable", True)}}
            if dry:
                print(f"  [dry] 旧版 {vid} の公開予約を外す（非公開のまま残す）")
                continue
            urllib.request.urlopen(urllib.request.Request(f"{API}/videos?part=status", data=json.dumps(body).encode(), method="PUT",
                                                          headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"}), timeout=30)
            print(f"  旧版 {vid} の公開予約を外した（非公開のまま残す。Issue #2 でチャツネへ新旧の videoId を報告する）")


def apply(tok, rows, vs, dry):
    unschedule_superseded(tok, dry)
    blocked = {"u": False, "c": False}
    for r in sorted(rows, key=lambda r: (r["kind"], r["no"])):
        v = vs.get(r["vid"])
        want = iso(r["at"])
        tag = f"{r['id']} {r['date']}"
        if blocked[r["kind"]]:
            print(f"  {tag}: 保留（前の回が未アップ／未予約のため飛び級しない）")
            continue
        if not v:
            print(f"  {tag}: 未アップ → 以降の同種の回は保留")
            blocked[r["kind"]] = True
            continue
        if v["status"]["privacyStatus"] == "public":
            print(f"  {tag}: 公開済み（触らない）")
            continue
        cur = v["status"].get("publishAt")
        if cur and cur.replace(".000", "") == want:
            print(f"  {tag}: 予約済み（変更なし）")
            continue
        if r["at"] <= dt.datetime.now(JST) + dt.timedelta(minutes=20):
            print(f"  {tag}: 予定時刻が過ぎている/近すぎる → 予約しない（schedule.json を直す）")
            blocked[r["kind"]] = True
            continue
        print(f"  {tag}: {r['vid']} → {set_at(tok, v, want, dry)}")


def playlist(tok, sc, rows, dry):
    pid = sc.get("playlist_id")
    hdr = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}
    if not pid:
        body = {"snippet": {"title": S.S2.get("playlist_title", S.S2_NAME), "description": S.S2.get("playlist_description", ""),
                            "defaultLanguage": "ja"}, "status": {"privacyStatus": "public"}}
        if dry:
            print("[dry] 再生リスト作成:", body["snippet"]["title"])
            return
        pid = json.load(urllib.request.urlopen(urllib.request.Request(
            f"{API}/playlists?part=snippet,status", data=json.dumps(body).encode(), headers=hdr, method="POST"), timeout=30))["id"]
        sc["playlist_id"] = pid
        json.dump(sc, open(SCHED, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("再生リスト作成:", pid)
    have, tokp = set(), None
    while True:
        q = {"part": "contentDetails", "playlistId": pid, "maxResults": 50}
        if tokp:
            q["pageToken"] = tokp
        for attempt in range(6):  # 作成直後の再生リストは数十秒 404 を返すことがある
            try:
                res = api(tok, "playlistItems", q)
                break
            except urllib.error.HTTPError as e:
                if e.code != 404 or attempt == 5:
                    raise
                import time
                time.sleep(10)
        have |= {i["contentDetails"]["videoId"] for i in res.get("items", [])}
        tokp = res.get("nextPageToken")
        if not tokp:
            break
    # 差し替えで旧版になった動画は再生リストから外す（動画そのものは非公開のまま残す）
    old = superseded_ids()
    if old & have:
        tokp = None
        while True:
            q = {"part": "id,contentDetails", "playlistId": pid, "maxResults": 50}
            if tokp:
                q["pageToken"] = tokp
            res = api(tok, "playlistItems", q)
            for it in res.get("items", []):
                if it["contentDetails"]["videoId"] in old and not dry:
                    urllib.request.urlopen(urllib.request.Request(f"{API}/playlistItems?id={it['id']}", method="DELETE",
                                                                  headers=hdr), timeout=30)
                    print(f"  再生リストから外した（旧版）{it['contentDetails']['videoId']}")
            tokp = res.get("nextPageToken")
            if not tokp:
                break
    for r in sorted(rows, key=lambda r: (r["at"], r["kind"] == "c")):
        if r["vid"] and r["vid"] not in have:
            if dry:
                print(f"[dry] 追加 {r['id']} {r['vid']}")
                continue
            urllib.request.urlopen(urllib.request.Request(
                f"{API}/playlistItems?part=snippet", headers=hdr, method="POST",
                data=json.dumps({"snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": r["vid"]}}}).encode()),
                timeout=30)
            print(f"  追加 {r['id']} {r['vid']}")


def write_status(rows, vs, sc):
    now = dt.datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    o = [f"# {S.S2_NAME}｜公開状態（自動生成）\n\n",
         f"> 生成 {now} JST・`python3 _tools/publish/ura_schedule.py`。予定は `{SCHED}`、公開予約は `--apply`。"
         "Shorts＝毎日、ケースファイル（本編）＝週1。同じ種類の中で飛び級しない。\n\n",
         f"- 再生リスト：{'https://www.youtube.com/playlist?list=' + sc['playlist_id'] if sc.get('playlist_id') else '未作成（--playlist）'}\n\n",
         "| 予定日 | 回 | ディレクトリ | videoId | 状態 | 再生 |\n|---|---|---|---|---|---|\n"]
    wd = "月火水木金土日"
    for r in sorted(rows, key=lambda r: (r["at"], r["kind"] == "c")):
        v = vs.get(r["vid"])
        views = v.get("statistics", {}).get("viewCount", "—") if v else "—"
        o.append(f"| {r['at']:%m/%d}({wd[r['at'].weekday()]}) | {'Short' if r['kind'] == 'u' else '本編'} {r['id']} | "
                 f"`{os.path.basename(r['dir']) if r['dir'] else '（未作成）'}` | {'`' + r['vid'] + '`' if r['vid'] else '—'} | "
                 f"{state(v)} | {views} |\n")
    o.append("\n関連動画（各 Short → 同じ話のケースファイル）は、本編の公開後に統合運営側（チャツネ）がブラウザで代行する（Issue #1。ここでの手動設定は不要）。"
             "動画を差し替えたときは Issue #2 で新旧の videoId を報告する。\n")
    open(f"{ROOT}/STATUS.md", "w", encoding="utf-8").write("".join(o))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--playlist", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sc, rows = load()
    errs = check_order(rows)
    if errs:
        sys.exit("拒否（schedule.json）：\n  " + "\n  ".join(errs))
    tok = token()
    vs = fetch(tok, [r["vid"] for r in rows])
    if a.apply:
        apply(tok, rows, vs, a.dry_run)
        vs = fetch(tok, [r["vid"] for r in rows])
    if a.playlist:
        playlist(tok, sc, rows, a.dry_run)
    write_status(rows, vs, sc)
    n = {s: sum(1 for r in rows if state(vs.get(r["vid"])) == s) for s in ("未アップ", "非公開", "予約済み", "公開済み")}
    print(f"{ROOT}/STATUS.md 更新  " + "  ".join(f"{k}{v}" for k, v in n.items()))


if __name__ == "__main__":
    main()
