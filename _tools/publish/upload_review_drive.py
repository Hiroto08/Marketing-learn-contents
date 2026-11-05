#!/usr/bin/env python3
"""
upload_review_drive.py — 完成 mp4 を Google Drive の共有フォルダ「マーケラボ レビュー便」へ上げる（Issue #2）。

社長が公開前の非公開動画を通勤中に確認するためのフロー。YouTube へ非公開アップしたタイミングで同じ mp4 を上げる
（upload_youtube.py が第2シリーズの回をアップした直後に自動で呼ぶ。手動でも実行できる）。

  python3 _tools/publish/upload_review_drive.py s2_ura/u01_jcpenney-sale [s2_ura/c01_... ...]
  python3 _tools/publish/upload_review_drive.py --check        # 認証とフォルダへの書き込み権限だけ確かめる

- フォルダ ID は series.json の review.drive_folder_id。
- ファイル名は「u01_<タイトル>.mp4」（回の番号とタイトルが分かる形）。
- 冪等：publish_manifest.json の同じ mp4 の項目に driveFileId と送付時の videoId を記録し、同じ動画（videoId が同じ）なら上げ直さない。
  中身が変わった（差し替え）場合は「…_r2.mp4」のように別名で上げる（古い方は統合運営側が整理する）。
- 認証：DRIVE_REFRESH_TOKEN（フォルダを共有された Google アカウントで get_refresh_token.py --drive を実行して取得）。
  無ければ YT_REFRESH_TOKEN を試す（そのトークンに Drive の権限が含まれていれば使える）。
  クライアントは YT_CLIENT_ID / YT_CLIENT_SECRET（同じ Google Cloud プロジェクトで「Google Drive API」を有効化しておく）。
"""
import glob
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import series as S  # noqa: E402

FOLDER = (S.CFG.get("review") or {}).get("drive_folder_id")


def access_token():
    cid, csec = os.environ.get("YT_CLIENT_ID"), os.environ.get("YT_CLIENT_SECRET")
    for name in ("DRIVE_REFRESH_TOKEN", "YT_REFRESH_TOKEN"):
        rt = os.environ.get(name)
        if not (cid and csec and rt):
            continue
        data = urllib.parse.urlencode({"client_id": cid, "client_secret": csec, "refresh_token": rt,
                                       "grant_type": "refresh_token"}).encode()
        tok = json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=30))
        scopes = tok.get("scope", "")
        if "auth/drive" in scopes:
            return tok["access_token"]
    raise SystemExit("Drive の権限があるトークンが無い：DRIVE_REFRESH_TOKEN を設定する（get_refresh_token.py --drive。Issue #2 参照）")


def item_files(d):
    """回のディレクトリ → [(mp4, manifestのパス, タイトル)]"""
    d = d.rstrip("/")
    base = os.path.basename(d)
    out = []
    if base.startswith("u") or os.path.exists(f"{d}/shorts.md") and not os.path.exists(f"{d}/script.md"):
        md = open(f"{d}/shorts.md", encoding="utf-8").read() if os.path.exists(f"{d}/shorts.md") else ""
        for sd in sorted(glob.glob(f"{d}/shorts_build/short*")):
            n = re.search(r"short(\d+)", sd)[1]
            m = re.search(rf"## Short {n}[：:].*?\*\*タイトル案：\*\* (.*?)\n", md, re.S)
            for f in glob.glob(f"{sd}/*_final.mp4"):
                out.append((f, f"{sd}/publish_manifest.json", m[1].strip() if m else base))
    else:
        head = open(f"{d}/description.md", encoding="utf-8").readline() if os.path.exists(f"{d}/description.md") else ""
        m = re.search(r"— (.+)$", head)
        for f in glob.glob(f"{d}/video_build/*_final.mp4"):
            out.append((f, f"{d}/publish_manifest.json", m[1].strip() if m else base))
    return out


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def safe(s):
    return re.sub(r'[\\/:*?"<>|]', "＿", s)[:80]


def upload(tok, path, name):
    meta = json.dumps({"name": name, "parents": [FOLDER], "mimeType": "video/mp4"}).encode()
    req = urllib.request.Request("https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true",
                                 data=meta, method="POST",
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json; charset=UTF-8",
                                          "X-Upload-Content-Type": "video/mp4",
                                          "X-Upload-Content-Length": str(os.path.getsize(path))})
    loc = urllib.request.urlopen(req, timeout=60).headers["Location"]
    with open(path, "rb") as f:
        body = f.read()
    r = urllib.request.urlopen(urllib.request.Request(loc, data=body, method="PUT",
                                                      headers={"Content-Type": "video/mp4"}), timeout=600)
    return json.load(r)["id"]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not FOLDER:
        sys.exit("series.json に review.drive_folder_id が無い")
    tok = access_token()
    if "--check" in sys.argv:
        q = urllib.parse.urlencode({"fields": "id,name,capabilities/canAddChildren", "supportsAllDrives": "true"})
        r = json.load(urllib.request.urlopen(urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files/{FOLDER}?{q}", headers={"Authorization": "Bearer " + tok}), timeout=30))
        print(f"OK フォルダ「{r['name']}」 書き込み可={r.get('capabilities', {}).get('canAddChildren')}")
        return
    if not args:
        sys.exit(__doc__)
    for d in args:
        for mp4, manp, title in item_files(d):
            man = json.load(open(manp, encoding="utf-8")) if os.path.exists(manp) else {}
            key = os.path.basename(mp4)
            ent = man.get(key, {})
            digest = sha256(mp4)
            # 送付済みかは「YouTube の videoId」で判定する（同じ動画を別の環境で作り直すと mp4 のバイトは変わるため）。
            # 中身を差し替えて新しい videoId になったときだけ、もう一度（_r2 などの名前で）送る
            if ent.get("driveFileId") and (ent.get("driveForVideoId") == ent.get("videoId") or ent.get("driveSha256") == digest):
                print(f"skip（この動画はレビュー便に送付済み {ent['driveFileId']}）: {mp4}")
                continue
            rev = ent.get("driveRev", 0) + 1
            iid = os.path.basename(d.rstrip("/")).split("_")[0]
            name = f"{iid}_{safe(title)}{'' if rev == 1 else f'_r{rev}'}.mp4"
            try:
                fid = upload(tok, mp4, name)
            except urllib.error.HTTPError as e:
                print(f"FAIL {e.code} {e.read().decode()[:200]}: {mp4}")
                continue
            ent.update({"driveFileId": fid, "driveSha256": digest, "driveRev": rev, "driveName": name,
                        "driveForVideoId": ent.get("videoId")})
            man[key] = ent
            json.dump(man, open(manp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"レビュー便へ送付: {name} → https://drive.google.com/file/d/{fid}/view")


if __name__ == "__main__":
    main()
