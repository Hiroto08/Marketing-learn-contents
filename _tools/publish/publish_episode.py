#!/usr/bin/env python3
"""
publish_episode.py — 既に非公開(private)でアップロード済みのエピソードを
「本編＋その回のShorts」まとめて公開／公開予約する。

設計思想（EP20飛び級公開事故の再発防止 2026-08）:
- 公開は必ずEP番号の昇順。EPn を公開する前に EP1..(n-1) の本編が全て public
  であることを確認し、そうでなければ拒否（--force で上書き可）。
- 本編とその回の Shorts は必ず同時に同じ状態へ（public / 同じ publishAt）。

videoId は各話 publish_manifest.json から取得し、無ければ YouTube のタイトル
（「第NN回」長編＝本編／それ以外の同EP由来＝Shorts）で補完する。

使い方:
  python3 _tools/publish/publish_episode.py --episode 03_practical/ep09_cpa-ltv
  python3 _tools/publish/publish_episode.py --episode <ep_dir> --at 2026-08-15T18:00:00+09:00
  python3 _tools/publish/publish_episode.py --episode <ep_dir> --dry-run
必要スコープ: https://www.googleapis.com/auth/youtube（videos.update）
"""
import os, sys, re, json, glob, argparse, urllib.request, urllib.parse, urllib.error

API = "https://www.googleapis.com/youtube/v3"
KANJI = {1:"一",2:"二",3:"三",4:"四",5:"五",6:"六",7:"七",8:"八",9:"九",10:"十",
         11:"十一",12:"十二",13:"十三",14:"十四",15:"十五",16:"十六",17:"十七",
         18:"十八",19:"十九",20:"二十",21:"二十一",22:"二十二",23:"二十三",24:"二十四"}


def token():
    cid, csec, rt = (os.environ.get("YT_CLIENT_ID"), os.environ.get("YT_CLIENT_SECRET"),
                     os.environ.get("YT_REFRESH_TOKEN"))
    if not (cid and csec and rt):
        sys.exit("環境変数 YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN が未設定")
    data = urllib.parse.urlencode({"client_id": cid, "client_secret": csec,
                                   "refresh_token": rt, "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30))["access_token"]


def api(tok, path, params):
    return json.load(urllib.request.urlopen(urllib.request.Request(
        f"{API}/{path}?" + urllib.parse.urlencode(params),
        headers={"Authorization": "Bearer " + tok}), timeout=30))


def _dur_is_short(d):
    m = re.match(r"PT(?:(\d+)M)?(?:(\d+)S)?", d or "")
    return (int(m.group(1) or 0) * 60 + int(m.group(2) or 0)) <= 60 if m else False


def all_uploads(tok):
    ch = api(tok, "channels", {"part": "contentDetails", "mine": "true"})["items"][0]
    pl = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    out, page = [], None
    while True:
        q = {"part": "snippet", "playlistId": pl, "maxResults": "50"}
        if page: q["pageToken"] = page
        r = api(tok, "playlistItems", q)
        out += [(it["snippet"]["resourceId"]["videoId"], it["snippet"]["title"]) for it in r["items"]]
        page = r.get("nextPageToken")
        if not page: break
    return out


def load(p):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return {}


def resolve(tok, ep_dir):
    """(main_videoId, [short_videoIds]) を manifest 優先・YouTube補完で解決"""
    ep = int(re.search(r"ep(\d+)", ep_dir).group(1))
    mm = load(f"{ep_dir}/publish_manifest.json")
    main = next(iter(mm.values()), {}).get("videoId") if mm else None
    shorts = []
    for sd in sorted(glob.glob(f"{ep_dir}/shorts_build/short*/publish_manifest.json")):
        v = next(iter(load(sd).values()), {}).get("videoId")
        if v: shorts.append(v)
    if main and shorts:
        return ep, main, shorts
    # YouTube 補完
    ups = all_uploads(tok)
    ids = [v for v, _ in ups]
    durs = {}
    for i in range(0, len(ids), 50):
        for it in api(tok, "videos", {"part": "contentDetails", "id": ",".join(ids[i:i+50])})["items"]:
            durs[it["id"]] = it["contentDetails"]["duration"]
    pat = re.compile(rf"第\s*({ep}|{KANJI.get(ep,'')})\s*回")
    if not main:
        for v, t in ups:
            if pat.search(t) and not _dur_is_short(durs.get(v)):
                main = v  # 後勝ち＝最新
    # Shorts 補完は manifest が正（タイトル照合はEP取り違えの恐れがあるため main のみ補完）
    return ep, main, shorts


def public_max_ep(tok):
    """現在 public 済みの本編の最大EP番号"""
    ups = all_uploads(tok)
    ids = [v for v, _ in ups]
    st = {}
    for i in range(0, len(ids), 50):
        for it in api(tok, "videos", {"part": "status,contentDetails", "id": ",".join(ids[i:i+50])})["items"]:
            st[it["id"]] = (it["status"]["privacyStatus"], it["contentDetails"]["duration"])
    mx = 0
    for v, t in ups:
        p, d = st.get(v, ("", ""))
        if p == "public" and not _dur_is_short(d):
            m = None
            for ep in range(1, 25):
                if re.search(rf"第\s*({ep}|{KANJI.get(ep,'')})\s*回", t):
                    m = ep; break
            if m: mx = max(mx, m)
    return mx


def set_privacy(tok, vid, at=None, dry=False):
    it = api(tok, "videos", {"part": "status,snippet", "id": vid})["items"]
    if not it: return f"{vid}: NOT FOUND"
    st = it[0]["status"]; title = it[0]["snippet"]["title"][:34]
    status = {"selfDeclaredMadeForKids": st.get("selfDeclaredMadeForKids", False),
              "license": st.get("license", "youtube"), "embeddable": st.get("embeddable", True),
              "publicStatsViewable": st.get("publicStatsViewable", True)}
    if at:
        status["privacyStatus"] = "private"; status["publishAt"] = at
    else:
        status["privacyStatus"] = "public"
    if dry:
        return f"[dry] {vid} [{title}] -> {'予約 '+at if at else 'public'}"
    body = {"id": vid, "status": status}
    req = urllib.request.Request(f"{API}/videos?part=status", data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"}, method="PUT")
    try:
        r = json.load(urllib.request.urlopen(req, timeout=30))
        s = r["status"]
        return f"{vid} [{title}] -> {s['privacyStatus']}" + (f" @ {s.get('publishAt')}" if s.get("publishAt") else "")
    except urllib.error.HTTPError as e:
        return f"{vid} [{title}]: FAIL {e.code} {e.read().decode()[:150]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", required=True, help="エピソードディレクトリ")
    ap.add_argument("--at", help="RFC3339の公開予約日時（例 2026-08-15T18:00:00+09:00）。省略で即時public")
    ap.add_argument("--force", action="store_true", help="EP順ガードを無視して公開する")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    tok = token()
    ep, mainv, shorts = resolve(tok, a.episode.rstrip("/"))
    if not mainv:
        sys.exit(f"本編 videoId を解決できない（未アップロード？）: {a.episode}")
    # EP順ガード
    mx = public_max_ep(tok)
    if ep > mx + 1 and not a.force:
        sys.exit(f"公開順序ガード: EP{ep:02d} は公開できません。現在 public 済み最大は EP{mx:02d} で、"
                 f"次に公開してよいのは EP{mx+1:02d} のみです（--force で上書き可）。")
    print(f"EP{ep:02d} を{'予約公開('+a.at+')' if a.at else '公開'}（本編＋Shorts{len(shorts)}本 同時）")
    print("  本編 :", set_privacy(tok, mainv, a.at, a.dry_run))
    for v in shorts:
        print("  Short:", set_privacy(tok, v, a.at, a.dry_run))
    if not shorts:
        print("  ! この回の Shorts manifest が見つからない（Short未UP or 別ブランチ）。本編のみ公開した。")


if __name__ == "__main__":
    main()
