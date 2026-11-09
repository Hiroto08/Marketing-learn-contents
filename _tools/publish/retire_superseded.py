#!/usr/bin/env python3
"""
retire_superseded.py — 24話の本編・Shorts を「中身を直して新しくアップ」したあと、旧版を退かせる。

24話の公開ガード（publish_episode.py・gen_upload_status.py）は動画タグ mlab-epNN / mlab-epNN-sM で回を判定する。
旧版にタグと公開予約が残っていると、(1) 旧版も予約どおりに公開される、(2) 同じ回の動画が2本あって新版を見失う。
そこで旧版（manifest の supersededVideoId）について：
  - 公開予約（publishAt）を外して非公開のまま残す（削除はしない。戻せるように）
  - タグ mlab-epNN(-sM) を mlab-old-epNN(-sM) に付け替える
  - タイトルの頭に「[旧版] 」を付ける
公開済みの旧版には触らない。

    python3 _tools/publish/retire_superseded.py 06_case-studies/ep23_failure-cases [--dry-run]
そのあと python3 _tools/publish/publish_episode.py --schedule-all で新版に予約が付く（EP順・Shortsと同時刻）。
"""
import glob
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yt_index import API, api, token  # noqa: E402


def superseded(d):
    out = []
    for p in [f"{d}/publish_manifest.json"] + glob.glob(f"{d}/shorts_build/short*/publish_manifest.json"):
        if os.path.exists(p):
            for v in json.load(open(p, encoding="utf-8")).values():
                if v.get("supersededVideoId"):
                    out.append((v["supersededVideoId"], v["videoId"]))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if not args:
        sys.exit(__doc__)
    tok = token()
    for d in args:
        pairs = superseded(d.rstrip("/"))
        if not pairs:
            print(f"{d}: 旧版なし")
            continue
        vs = {it["id"]: it for it in api(tok, "videos", {"part": "snippet,status", "id": ",".join(o for o, _ in pairs)})["items"]}
        for old, new in pairs:
            v = vs.get(old)
            if not v:
                print(f"  旧版 {old}: 見つからない（削除済み？）")
                continue
            st, sn = v["status"], v["snippet"]
            if st["privacyStatus"] == "public":
                print(f"  旧版 {old}: 公開済みなので触らない（新版 {new}）")
                continue
            tags = [t.replace("mlab-ep", "mlab-old-ep") if t.startswith("mlab-ep") else t for t in sn.get("tags", [])]
            title = sn["title"] if sn["title"].startswith("[旧版]") else ("[旧版] " + sn["title"])[:100]
            body = {"id": old,
                    "snippet": {"title": title, "description": sn.get("description", ""), "tags": tags,
                                "categoryId": sn.get("categoryId", "27"), "defaultLanguage": sn.get("defaultLanguage", "ja")},
                    "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": st.get("selfDeclaredMadeForKids", False),
                               "license": st.get("license", "youtube"), "embeddable": st.get("embeddable", True),
                               "publicStatsViewable": st.get("publicStatsViewable", True)}}
            if dry:
                print(f"  [dry] 旧版 {old}: 予約を外す・タグを mlab-old-… に・タイトルに[旧版]（新版 {new}）")
                continue
            urllib.request.urlopen(urllib.request.Request(f"{API}/videos?part=snippet,status", data=json.dumps(body).encode(), method="PUT",
                                                          headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"}), timeout=30)
            print(f"  旧版 {old}: 予約を外して非公開で残した・タグを mlab-old-… に替えた（新版 {new}）")


if __name__ == "__main__":
    main()
