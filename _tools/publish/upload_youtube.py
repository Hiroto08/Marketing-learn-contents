#!/usr/bin/env python3
"""YouTube 非公開アップロード自動化 — 本編/Shorts を「公開ボタンを押すだけ」の
状態まで持っていくパイプライン。

    # 本編（<episode_dir>/video_build/*_final.mp4 を private でアップロード）
    python3 _tools/publish/upload_youtube.py --episode 01_beginner/ep01_what-is-marketing

    # Shorts（shorts_build/short*/short*_final.mp4 を一括アップロード）
    python3 _tools/publish/upload_youtube.py --shorts 01_beginner/ep01_what-is-marketing

    # メタデータの組み立て結果だけ確認（アップロードしない）
    python3 _tools/publish/upload_youtube.py --episode <dir> --dry-run

    # オプション: --privacy unlisted / --publish-at 2026-07-20T21:00:00+09:00
    #           --playlist <playlistId> / --thumbnail <png>

サムネイル（本編）:
  <episode_dir>/thumbnail.png があれば自動で設定される（--thumbnail 指定が優先）。
  生成は `python3 _tools/publish/make_thumbnail.py <episode_dir>`（thumbnail.mdから文言取得）。
  動画がアップロード済みでも、サムネPNGが新規/変更されていれば再実行で後追い設定される
  （publish_manifest.json の thumbSha256 で冪等管理。thumbnails.set=50クォータ単位）。

認証（リポジトリに秘密情報は置かない）:
  環境変数 YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN を使う。
  取得手順は .claude/skills/yt-uploader/SKILL.md を参照
  （claude.ai/code の環境設定 > Secrets に登録すればセッションに自動注入される）。

メタデータの出どころ:
  本編   … <episode_dir>/description.md（メイン説明文/タイムスタンプ/再生リスト/
            関連動画/参考リソース/ハッシュタグ の各セクションを結合）
            タイトルは description.md の見出し（`— ` 以降）
  Shorts … <episode_dir>/shorts.md の「## Short N」ごとの **タイトル案：**。
            説明文は固定ひな形＋#Shorts ハッシュタグ（3〜5個）

冪等性: 各ディレクトリの publish_manifest.json に videoId と mp4 の SHA-256 を記録。
        同一ハッシュのファイルは再アップロードせずスキップする。

APIで自動化できないもの（アップロード後にStudioで手動、checklistに出力）:
  ・Shorts の「関連動画」リンク設定（公式APIなし）
  ・固定コメントのピン留め（APIなし。コメント投稿自体は --pin-comment で投稿だけ実施）
  ・エンドスクリーン/カード

クォータ目安: videos.insert=1600 / thumbnails.set=50 / playlistItems.insert=50 単位。
  既定の1日10,000単位では動画6本/日程度が上限。
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

import requests

API = "https://www.googleapis.com/youtube/v3"
UPLOAD_API = "https://www.googleapis.com/upload/youtube/v3/videos"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CATEGORY_EDUCATION = "27"


# ──────────────────────────────────────────────────────────────────────────
# auth
# ──────────────────────────────────────────────────────────────────────────
def access_token() -> str:
    cid = os.environ.get("YT_CLIENT_ID")
    csec = os.environ.get("YT_CLIENT_SECRET")
    rtok = os.environ.get("YT_REFRESH_TOKEN")
    if not (cid and csec and rtok):
        sys.exit("環境変数 YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN が未設定。\n"
                 "取得手順: .claude/skills/yt-uploader/SKILL.md")
    r = requests.post(TOKEN_URL, data={
        "client_id": cid, "client_secret": csec,
        "refresh_token": rtok, "grant_type": "refresh_token"}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"トークン更新失敗 {r.status_code}: {r.text[:300]}")
    return r.json()["access_token"]


# ──────────────────────────────────────────────────────────────────────────
# metadata assembly
# ──────────────────────────────────────────────────────────────────────────
def _block(md: str, heading: str) -> str:
    """## heading 直下の ```コードブロック``` または素のテキストを取り出す"""
    m = re.search(rf"^## {re.escape(heading)}\s*\n(.*?)(?=\n## |\Z)", md, re.S | re.M)
    if not m:
        return ""
    body = m.group(1)
    code = re.findall(r"```\n?(.*?)```", body, re.S)
    return "\n\n".join(c.strip() for c in code) if code else body.strip()


def episode_metadata(ep_dir: str) -> dict:
    md = open(f"{ep_dir}/description.md", encoding="utf-8").read()
    head = md.splitlines()[0]
    m = re.search(r"— (.+)$", head)
    title = m.group(1).strip() if m else os.path.basename(ep_dir)

    parts = []
    for sec in ["メイン説明文", "タイムスタンプ", "シリーズ再生リスト", "関連動画", "参考・補足リソース"]:
        b = _block(md, sec)
        if b:
            # 制作用の未確定マーカーを公開文面から除去
            b = b.replace("：（公開後追記）", "").replace("（公開後追記）", "")
            b = "\n".join(l for l in b.splitlines()
                          if "この欄にURLを追記" not in l and "実測値へ更新" not in l)
            parts.append(b.strip())
    tags_block = _block(md, "ハッシュタグ")
    hashtags = re.findall(r"#[^\s#]+", tags_block)
    if hashtags:
        parts.append(" ".join(hashtags[:15]))
    description = "\n\n".join(parts)
    # YouTube制限: description<=5000文字・タグ合計<=500文字
    tags = [h.lstrip("#") for h in hashtags][:20]
    return {"title": title[:100], "description": description[:4990], "tags": tags}


def shorts_metadata(ep_dir: str) -> list:
    md = open(f"{ep_dir}/shorts.md", encoding="utf-8").read()
    ep_title_m = re.search(r"— (.+)$", md.splitlines()[0])
    ep_title = ep_title_m.group(1).strip() if ep_title_m else ""
    out = []
    for m in re.finditer(r"## Short (\d+)[：:].*?\*\*タイトル案：\*\* (.*?)\n", md, re.S):
        n, title = int(m.group(1)), m.group(2).strip()
        desc = (f"{title}\n\n"
                f"本編「{ep_title}」の要点を1論点だけ切り出したShortsです。\n"
                f"続きは、この画面のリンク（関連動画）から本編へ。\n\n"
                f"※ナレーションはAI音声合成（VOICEVOX:玄野武宏）を使用しています。\n\n"
                f"#Shorts #マーケティング #ビジネス")
        out.append({"n": n, "title": title[:100], "description": desc,
                    "tags": ["Shorts", "マーケティング", "ビジネス"]})
    return out


# ──────────────────────────────────────────────────────────────────────────
# upload
# ──────────────────────────────────────────────────────────────────────────
def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(d: str) -> dict:
    p = f"{d}/publish_manifest.json"
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def save_manifest(d: str, man: dict):
    with open(f"{d}/publish_manifest.json", "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)


def upload_video(tok: str, path: str, meta: dict, privacy: str,
                 publish_at: str | None) -> str:
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    body = {"snippet": {"title": meta["title"], "description": meta["description"],
                        "tags": meta["tags"], "categoryId": CATEGORY_EDUCATION,
                        "defaultLanguage": "ja", "defaultAudioLanguage": "ja"},
            "status": status}
    size = os.path.getsize(path)
    r = requests.post(
        f"{UPLOAD_API}?uploadType=resumable&part=snippet,status",
        headers={"Authorization": f"Bearer {tok}",
                 "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Length": str(size),
                 "X-Upload-Content-Type": "video/mp4"},
        data=json.dumps(body), timeout=60)
    if r.status_code != 200:
        sys.exit(f"アップロード開始失敗 {r.status_code}: {r.text[:300]}")
    session_url = r.headers["Location"]

    # 単発PUT（1080p数十MBまでなら十分。失敗時は8MBチャンクで再開）
    with open(path, "rb") as f:
        r = requests.put(session_url,
                         headers={"Authorization": f"Bearer {tok}",
                                  "Content-Type": "video/mp4"},
                         data=f, timeout=1800)
    if r.status_code in (200, 201):
        return r.json()["id"]
    # resume with ranged chunks
    CHUNK = 8 << 20
    sent = 0
    for attempt in range(20):
        q = requests.put(session_url, headers={
            "Authorization": f"Bearer {tok}",
            "Content-Range": f"bytes */{size}"}, timeout=60)
        if q.status_code in (200, 201):
            return q.json()["id"]
        if q.status_code != 308:
            sys.exit(f"アップロード失敗 {q.status_code}: {q.text[:300]}")
        rng = q.headers.get("Range", "")
        sent = int(rng.split("-")[1]) + 1 if "-" in rng else 0
        with open(path, "rb") as f:
            f.seek(sent)
            chunk = f.read(CHUNK)
            end = sent + len(chunk) - 1
            r = requests.put(session_url, headers={
                "Authorization": f"Bearer {tok}",
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes {sent}-{end}/{size}"},
                data=chunk, timeout=600)
        if r.status_code in (200, 201):
            return r.json()["id"]
        time.sleep(2 ** min(attempt, 5))
    sys.exit("アップロードが20回のリトライ後も完了しない")


def set_thumbnail(tok: str, video_id: str, png: str) -> bool:
    with open(png, "rb") as f:
        r = requests.post(
            f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set?videoId={video_id}",
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "image/png"},
            data=f, timeout=120)
    print(f"  thumbnail: {'OK' if r.status_code == 200 else f'FAIL {r.status_code} {r.text[:120]}'}")
    return r.status_code == 200


def episode_thumbnail(ep_dir: str, cli_thumb: str | None) -> str | None:
    """本編サムネの解決: --thumbnail 指定 > <ep>/thumbnail.png（make_thumbnail.py の出力）"""
    if cli_thumb:
        return cli_thumb
    auto = f"{ep_dir}/thumbnail.png"
    return auto if os.path.exists(auto) else None


def add_to_playlist(tok: str, video_id: str, playlist_id: str):
    r = requests.post(f"{API}/playlistItems?part=snippet",
                      headers={"Authorization": f"Bearer {tok}",
                               "Content-Type": "application/json"},
                      json={"snippet": {"playlistId": playlist_id,
                            "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
                      timeout=30)
    print(f"  playlist: {'OK' if r.status_code == 200 else f'FAIL {r.status_code} {r.text[:120]}'}")


def post_comment(tok: str, video_id: str, text: str):
    r = requests.post(f"{API}/commentThreads?part=snippet",
                      headers={"Authorization": f"Bearer {tok}",
                               "Content-Type": "application/json"},
                      json={"snippet": {"videoId": video_id, "topLevelComment":
                            {"snippet": {"textOriginal": text}}}}, timeout=30)
    print(f"  comment: {'投稿OK（ピン留めはStudioで手動）' if r.status_code == 200 else f'FAIL {r.status_code} {r.text[:120]}'}")


# ──────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", help="本編のエピソードディレクトリ")
    ap.add_argument("--shorts", help="Shortsを一括処理するエピソードディレクトリ")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted"])
    ap.add_argument("--publish-at", dest="publish_at",
                    help="公開予約 ISO8601（指定時は private+publishAt）")
    ap.add_argument("--playlist", help="追加先プレイリストID")
    ap.add_argument("--thumbnail", help="サムネイルPNG（本編のみ）")
    ap.add_argument("--pin-comment", dest="pin_comment",
                    help="投稿する固定コメント文（ピン留め自体は手動）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not (a.episode or a.shorts):
        ap.error("--episode か --shorts を指定")

    jobs = []  # (dir_key, mp4, meta)
    if a.episode:
        d = a.episode.rstrip("/")
        mp4s = [f"{d}/video_build/{f}" for f in
                sorted(os.listdir(f"{d}/video_build"))
                if f.endswith("_final.mp4")] if os.path.isdir(f"{d}/video_build") else []
        meta = episode_metadata(d)
        if not mp4s:
            print(f"! {d}/video_build に *_final.mp4 が無い（ビルド前？）")
            if a.dry_run:
                jobs.append((d, f"{d}/video_build/(未ビルド)", meta))
        jobs += [(d, m, meta) for m in mp4s[:1]]
    if a.shorts:
        d = a.shorts.rstrip("/")
        for sm in shorts_metadata(d):
            p = f"{d}/shorts_build/short{sm['n']}/short{sm['n']}_final.mp4"
            if os.path.exists(p):
                jobs.append((f"{d}/shorts_build/short{sm['n']}", p, sm))
            elif a.dry_run:
                jobs.append((f"{d}/shorts_build/short{sm['n']}", p + "(未ビルド)", sm))
            else:
                print(f"! 見つからない: {p}")

    if a.dry_run:
        for _, p, m in jobs:
            print(f"═══ {p}")
            print(f"  title: {m['title']}")
            print(f"  tags : {m['tags']}")
            print(f"  desc : {m['description'][:200]}…({len(m['description'])}字)")
        print(f"\n{len(jobs)}本（dry-run・アップロードなし）")
        return

    tok = access_token()
    checklist = []
    ep_thumb = episode_thumbnail(a.episode.rstrip("/"), a.thumbnail) if a.episode else None
    for dkey, path, meta in jobs:
        man = load_manifest(dkey)
        digest = sha256(path)
        prev = man.get(os.path.basename(path))
        is_episode = dkey == (a.episode or "").rstrip("/")
        if prev and prev.get("sha256") == digest:
            print(f"skip（同一ハッシュ済み videoId={prev['videoId']}）: {path}")
            # 動画は既アップでもサムネが新規/更新なら後追いで設定する（thumbnails.set=50単位）
            if is_episode and ep_thumb:
                tdigest = sha256(ep_thumb)
                if prev.get("thumbSha256") != tdigest:
                    print(f"  サムネ更新: {ep_thumb} → videoId={prev['videoId']}")
                    if set_thumbnail(tok, prev["videoId"], ep_thumb):
                        prev["thumbSha256"] = tdigest
                        man[os.path.basename(path)] = prev
                        save_manifest(dkey, man)
            continue
        print(f"uploading: {path}  ({os.path.getsize(path)//1024//1024}MB)")
        vid = upload_video(tok, path, meta, a.privacy, a.publish_at)
        print(f"  → https://studio.youtube.com/video/{vid}/edit  (privacy={a.privacy}{' publishAt=' + a.publish_at if a.publish_at else ''})")
        thumb_sha = None
        if is_episode and ep_thumb:
            if set_thumbnail(tok, vid, ep_thumb):
                thumb_sha = sha256(ep_thumb)
        if a.playlist:
            add_to_playlist(tok, vid, a.playlist)
        if a.pin_comment:
            post_comment(tok, vid, a.pin_comment)
        man[os.path.basename(path)] = {"videoId": vid, "sha256": digest,
                                       "privacy": a.privacy,
                                       "publishAt": a.publish_at,
                                       "thumbSha256": thumb_sha,
                                       "uploadedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        save_manifest(dkey, man)
        if "short" in dkey:
            checklist.append(f"[ ] Studio: short{dkey[-1]} (video {vid}) に「関連動画」→本編を設定")
        else:
            checklist.append(f"[ ] Studio: 本編 {vid} のエンドスクリーン/カード確認")

    if checklist:
        print("\n── 残る手動作業（APIで自動化不可）──")
        print("\n".join(checklist))
        print("（固定コメントのピン留め・Shortsの関連動画リンクはStudioのみ）")


if __name__ == "__main__":
    main()
