"""
yt_index.py — チャンネル上の動画を「第何回の本編／何番目のShort」に対応づける共通モジュール。

判定キーは動画タグ（視聴者には見えない）：
  本編  : mlab-epNN        （例 mlab-ep09）
  Short : mlab-epNN-sM     （例 mlab-ep09-s1）
タグが無い古い動画だけ、タイトル先頭の「第N回」とローカルの publish_manifest.json で補完する。
（公開タイトルから「第N回：」を外したため、タイトル照合は主手段にしない）
"""
import glob
import json
import os
import re
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/youtube/v3"
TAG_RE = re.compile(r"^mlab-ep(\d{2})(?:-s(\d+))?$")


def token() -> str:
    cid, csec, rt = (os.environ.get("YT_CLIENT_ID"), os.environ.get("YT_CLIENT_SECRET"),
                     os.environ.get("YT_REFRESH_TOKEN"))
    if not (cid and csec and rt):
        raise SystemExit("環境変数 YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN が未設定")
    data = urllib.parse.urlencode({"client_id": cid, "client_secret": csec,
                                   "refresh_token": rt, "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30))["access_token"]


def api(tok: str, path: str, params: dict) -> dict:
    return json.load(urllib.request.urlopen(urllib.request.Request(
        f"{API}/{path}?" + urllib.parse.urlencode(params),
        headers={"Authorization": "Bearer " + tok}), timeout=30))


def _duration_sec(d: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    return (int(m[1] or 0) * 3600 + int(m[2] or 0) * 60 + int(m[3] or 0)) if m else 0


def _load(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def _manifest_ids() -> dict:
    """ローカル manifest → {videoId: (ep, short_n)}（short_n=0 は本編）"""
    out = {}
    for d in glob.glob("0*/ep*"):
        m = re.search(r"ep(\d+)", os.path.basename(d))
        if not (m and os.path.isdir(d)):
            continue
        ep = int(m[1])
        for v in _load(f"{d}/publish_manifest.json").values():
            if v.get("videoId"):
                out[v["videoId"]] = (ep, 0)
        for sd in glob.glob(f"{d}/shorts_build/short*/publish_manifest.json"):
            n = int(re.search(r"short(\d+)", sd)[1])
            for v in _load(sd).values():
                if v.get("videoId"):
                    out[v["videoId"]] = (ep, n)
    return out


def channel_videos(tok: str) -> dict:
    """{videoId: video resource(snippet,status,contentDetails,statistics)} — チャンネル全動画＋manifest記載分"""
    ch = api(tok, "channels", {"part": "contentDetails", "mine": "true"})["items"][0]
    pl = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page = set(), None
    while True:
        q = {"part": "contentDetails", "playlistId": pl, "maxResults": "50"}
        if page:
            q["pageToken"] = page
        r = api(tok, "playlistItems", q)
        ids |= {it["contentDetails"]["videoId"] for it in r["items"]}
        page = r.get("nextPageToken")
        if not page:
            break
    ids |= set(_manifest_ids())  # uploads プレイリストが取りこぼす動画への保険
    ids, out = list(ids), {}
    for i in range(0, len(ids), 50):
        r = api(tok, "videos", {"part": "snippet,status,contentDetails,statistics", "id": ",".join(ids[i:i + 50])})
        out.update({it["id"]: it for it in r["items"]})
    return out


def episode_index(tok: str, videos: dict | None = None) -> dict:
    """{ep: {"main": videoId|None, "shorts": {n: videoId}, "items": {videoId: video}}}"""
    videos = videos if videos is not None else channel_videos(tok)
    man = _manifest_ids()
    idx = {}

    def slot(ep):
        return idx.setdefault(ep, {"main": None, "shorts": {}, "items": {}})

    for vid, v in videos.items():
        ep = n = None
        for t in v["snippet"].get("tags", []):
            m = TAG_RE.match(t)
            if m:
                ep, n = int(m[1]), int(m[2] or 0)
                break
        if ep is None and vid in man:
            ep, n = man[vid]
        if ep is None:
            m = re.match(r"第\s*(\d+)\s*回", v["snippet"]["title"])
            if m and _duration_sec(v["contentDetails"]["duration"]) > 180:
                ep, n = int(m[1]), 0
        if ep is None:
            continue
        s = slot(ep)
        s["items"][vid] = v
        if n == 0:
            s["main"] = vid
        else:
            s["shorts"][n] = vid
    return idx


def privacy(v: dict) -> str:
    return v["status"]["privacyStatus"]


def public_max_ep(idx: dict) -> int:
    """本編が public の最大EP"""
    pub = [ep for ep, s in idx.items() if s["main"] and privacy(s["items"][s["main"]]) == "public"]
    return max(pub) if pub else 0
