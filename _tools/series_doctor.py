#!/usr/bin/env python3
"""series_doctor.py — 新しいテーマ（チャンネル）を立ち上げるときの設定チェック。

  python3 _tools/series_doctor.py           # 設定ファイルと環境変数の有無だけ（ネットワーク不要）
  python3 _tools/series_doctor.py --online  # YouTube／note／Kit に読み取りだけで接続して確認

何も書き込まない。秘密の値は表示しない（有無と文字数だけ）。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import series as S  # noqa: E402

CA = "/root/.ccr/ca-bundle.crt"
OK, NG, WARN = "OK  ", "NG  ", "注意"
problems = []


def line(mark, msg):
    print(f"[{mark}] {msg}")
    if mark == NG:
        problems.append(msg)


def check_config():
    print("── series.json")
    c = S.CFG
    for key, val in [("series_name", c["series_name"]), ("tag_prefix", c["tag_prefix"]),
                     ("youtube.channel_id", S.CHANNEL_ID), ("note.urlname", S.NOTE_USER),
                     ("kit.optin_url", S.OPTIN_URL)]:
        bad = not val or "<" in str(val) or "TODO" in str(val)
        line(NG if bad else OK, f"{key} = {val if not bad else '未設定'}")
    line(OK if S.CHANNEL_ID.startswith("UC") else NG, "channel_id は UC で始まる")
    line(OK if S.PUBLISH_DAYS else NG, f"公開曜日 {S.DAYS_JA} {S.YT_HOUR}:00 JST ／ note {S.NOTE_HOUR}:00 JST")
    line(OK if S.YT.get("master_playlist_id") else WARN,
         "master_playlist_id（全話の再生リスト）" + ("" if S.YT.get("master_playlist_id") else "：未設定。sync_playlists.py を流した後にIDを入れる"))
    pls = S.YT.get("playlists") or []
    line(OK if pls else WARN, f"再生リスト定義 {len(pls)} 本")
    for p in pls:
        a, b = p["episodes"]
        if not (1 <= a <= b <= S.TOTAL):
            line(NG, f"再生リスト「{p['title'][:20]}」の episodes {a}-{b} が total_episodes={S.TOTAL} の範囲外")
    line(OK if len(S.YT.get("channel_description", "")) <= 1000 else NG, "channel_description は1000字以内")
    line(OK if len(S.YT.get("channel_keywords", "")) <= 500 else NG, "channel_keywords は500字以内")


def check_env():
    print("── 環境変数（claude.ai/code の環境設定 → Environment variables）")
    for name, why in [("YT_CLIENT_ID", "YouTube"), ("YT_CLIENT_SECRET", "YouTube"), ("YT_REFRESH_TOKEN", "YouTube"),
                      ("_note_session_v5", "note の下書き保存・公開"), ("KIT_API_KEY", "Kit のメール予約")]:
        v = os.environ.get(name)
        line(OK if v else NG, f"{name}（{why}）" + (f"：{len(v)}文字" if v else "：未設定"))


def check_online():
    import requests
    print("── 接続（読み取りのみ）")
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "publish"))
        from yt_index import api, token
        tok = token()
        scopes = requests.get("https://oauth2.googleapis.com/tokeninfo", params={"access_token": tok},
                              verify=CA, timeout=30).json().get("scope", "")
        for sc, why in [("youtube.upload", "アップロード"), ("auth/youtube ", "公開・再生リスト"),
                        ("youtube.force-ssl", "字幕"), ("yt-analytics.readonly", "アナリティクス")]:
            line(OK if sc.strip() in scopes + " " else NG, f"YouTube 権限 {sc.strip()}（{why}）")
        ch = api(tok, "channels", {"part": "snippet", "mine": "true"})["items"][0]
        line(OK if ch["id"] == S.CHANNEL_ID else NG, f"認可したチャンネル {ch['snippet']['title']}（{ch['id']}）が series.json と一致")
    except Exception as e:  # noqa: BLE001
        line(NG, f"YouTube に接続できない：{str(e)[:120]}")
    ck = os.environ.get("_note_session_v5")
    if ck:
        r = requests.get("https://note.com/api/v2/note_list/contents", params={"limit": 1, "page": 1},
                         cookies={"_note_session_v5": ck}, verify=CA, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"})
        line(OK if r.status_code == 200 else NG, f"note ログイン（記事一覧の取得）：{r.status_code}")
    key = os.environ.get("KIT_API_KEY")
    if key:
        r = requests.get("https://api.kit.com/v4/account", headers={"X-Kit-Api-Key": key}, verify=CA, timeout=30)
        line(OK if r.status_code == 200 else NG, f"Kit API：{r.status_code}"
             + ("（401=キー誤り／403=プランか権限）" if r.status_code in (401, 403) else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--online", action="store_true")
    a = ap.parse_args()
    check_config()
    check_env()
    if a.online:
        check_online()
    print("\n結果：" + ("問題なし" if not problems else f"{len(problems)}件の NG を直してください"))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
