#!/usr/bin/env python3
"""remove_newsletter_cta.py — 動画の概要欄・再生リストの説明から、メルマガ登録の導線を外す（社長決裁 2026-11-18・Issue #2）。

外すもの（現行の導線・表記だけ。メルマガの仕組み自体は残す）：
  - 「▼【無料】マーケの型 全20話まとめ＆実践チートシート（PDF）を配布中」などの、チートシート・無料特典の見出し行
  - その直後の Kit の登録ページの URL の行（👉 https://…kit.com/…）
  - 行の中に Kit の登録ページの URL だけが残っているもの

  python3 _tools/publish/remove_newsletter_cta.py --dry-run     # 対象と件数だけを表示（読み取りのみ）
  python3 _tools/publish/remove_newsletter_cta.py               # YouTube 上の概要欄・再生リストの説明を更新
  python3 _tools/publish/remove_newsletter_cta.py --local       # リポジトリの description.md も同じ規則で直す

videos.update は1本 50 単位（1日 10,000 単位）。タイトル・タグ・カテゴリ・言語はそのまま送り返す。
"""
import argparse
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt_index as Y  # noqa: E402

HEAD = re.compile(r"^.*(チートシート|無料特典|全20話まとめ|全20回まとめ).*$")
URL = re.compile(r"https?://[\w.-]*kit\.com/\S*")


def strip_cta(text: str) -> str:
    lines = text.split("\n")
    out, skip_url = [], False
    for ln in lines:
        if HEAD.match(ln):
            skip_url = True
            continue
        if URL.search(ln) and (skip_url or re.fullmatch(r"\s*(👉\s*)?" + URL.pattern + r"\s*", ln)):
            skip_url = False
            continue
        skip_url = False
        out.append(ln)
    s = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", s).strip("\n") + ("\n" if text.endswith("\n") else "")


def put(tok, path, body):
    req = urllib.request.Request(f"{Y.API}/{path}", data=json.dumps(body).encode(), method="PUT",
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json; charset=UTF-8"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def videos(tok):
    ch = Y.api(tok, "channels", {"part": "contentDetails", "mine": "true"})["items"][0]
    pl = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page = [], None
    while True:
        q = {"part": "contentDetails", "playlistId": pl, "maxResults": "50"}
        if page:
            q["pageToken"] = page
        r = Y.api(tok, "playlistItems", q)
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        page = r.get("nextPageToken")
        if not page:
            break
    out = []
    for i in range(0, len(ids), 50):
        out += Y.api(tok, "videos", {"part": "snippet,status", "id": ",".join(ids[i:i + 50])})["items"]
    return out


def playlists(tok):
    out, page = [], None
    while True:
        q = {"part": "snippet", "mine": "true", "maxResults": "50"}
        if page:
            q["pageToken"] = page
        r = Y.api(tok, "playlists", q)
        out += r["items"]
        page = r.get("nextPageToken")
        if not page:
            break
    return out


def local_fix(dry):
    n = 0
    for p in sorted(glob.glob("0*/ep*/description.md") + glob.glob("s2_ura/*/description.md")):
        s = open(p, encoding="utf-8").read()
        t = strip_cta(s)
        if t != s:
            n += 1
            print(f"  local {'（dry）' if dry else ''}{p}")
            if not dry:
                open(p, "w", encoding="utf-8").write(t)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--local", action="store_true")
    a = ap.parse_args()
    if a.local:
        print(f"description.md：{local_fix(a.dry_run)} 件")
        return
    tok = Y.token()
    vs = videos(tok)
    hit = [v for v in vs if strip_cta(v["snippet"].get("description", "")) != v["snippet"].get("description", "")]
    print(f"動画 {len(vs)} 本のうち、導線が入っているもの {len(hit)} 本")
    done, failed = [], []
    for v in hit:
        sn = v["snippet"]
        new = strip_cta(sn["description"])
        print(f"  {v['id']} [{v['status']['privacyStatus']}] {sn['title'][:40]}  {len(sn['description'])}→{len(new)}字")
        if a.dry_run:
            continue
        body = {"id": v["id"], "snippet": {"title": sn["title"], "description": new, "categoryId": sn["categoryId"]}}
        for k in ("tags", "defaultLanguage", "defaultAudioLanguage"):
            if sn.get(k):
                body["snippet"][k] = sn[k]
        try:
            put(tok, "videos?part=snippet", body)
            done.append(v["id"])
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:200]
            failed.append((v["id"], e.code, msg))
            print(f"    ✗ {e.code} {msg}")
            if "quotaExceeded" in msg:
                print("  クォータ超過：日本時間17時（冬）以降に同じコマンドでもう一度。直したものは自動で飛ばす")
                break
    pls = playlists(tok)
    phit = [p for p in pls if strip_cta(p["snippet"].get("description", "")) != p["snippet"].get("description", "")]
    print(f"再生リスト {len(pls)} 個のうち、導線が入っているもの {len(phit)} 個")
    for p in phit:
        sn = p["snippet"]
        print(f"  {p['id']} {sn['title'][:40]}")
        if a.dry_run:
            continue
        try:
            put(tok, "playlists?part=snippet", {"id": p["id"], "snippet": {"title": sn["title"], "description": strip_cta(sn["description"]),
                                                                          **({"defaultLanguage": sn["defaultLanguage"]} if sn.get("defaultLanguage") else {})}})
            done.append(p["id"])
        except urllib.error.HTTPError as e:
            failed.append((p["id"], e.code, e.read().decode()[:200]))
    if not a.dry_run:
        print(f"更新 {len(done)} 件／失敗 {len(failed)} 件")
        json.dump({"updated": done, "failed": failed}, open("docs/newsletter-cta-removal.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
