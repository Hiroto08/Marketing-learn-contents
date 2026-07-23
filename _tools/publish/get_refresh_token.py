#!/usr/bin/env python3
"""YT_REFRESH_TOKEN 取得用の一回きりヘルパ（ブラウザが必要なので**手元のPCで**実行する）。

前提（Google Cloud Console で5分）:
  1. プロジェクト作成 → 「YouTube Data API v3」を有効化
  2. OAuth同意画面: 外部・テストユーザーに自分のGoogleアカウントを追加
  3. 認証情報 → OAuthクライアントID作成 → 種類「デスクトップアプリ」
     → クライアントID / クライアントシークレットを控える

実行:
  python3 get_refresh_token.py <CLIENT_ID> <CLIENT_SECRET>

ブラウザが開くので、チャンネルを管理するGoogleアカウントで許可すると
リフレッシュトークンが表示される。以下3つを claude.ai/code の
環境設定 > Secrets（環境変数）に登録する:
  YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN

トークンはリポジトリ・チャットに貼らないこと。
"""
import http.server
import secrets
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser

SCOPE = ("https://www.googleapis.com/auth/youtube.upload "
         "https://www.googleapis.com/auth/youtube "
         # 公開後のCTR・維持率・流入元を取得して改善ループを閉じるため
         "https://www.googleapis.com/auth/yt-analytics.readonly")
PORT = 8765


class _ReusableServer(http.server.HTTPServer):
    # 前回の実行が異常終了してもポートを再利用できるように
    allow_reuse_address = True


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    cid, csec = sys.argv[1], sys.argv[2]
    state = secrets.token_urlsafe(16)
    redirect = f"http://localhost:{PORT}"
    auth_url = ("https://accounts.google.com/o/oauth2/v2/auth?" +
                urllib.parse.urlencode({
                    "client_id": cid, "redirect_uri": redirect,
                    "response_type": "code", "scope": SCOPE,
                    "access_type": "offline", "prompt": "consent",
                    "state": state}))
    code_holder = {}
    got = threading.Event()

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state and "code" in q:
                code_holder["code"] = q["code"][0]
                body = "認可完了。ターミナルに戻ってください。".encode()
                got.set()
            elif "error" in q:
                body = f"認可エラー: {q['error'][0]}（ターミナルを確認）".encode()
                code_holder["error"] = q["error"][0]
                got.set()
            else:
                body = "パラメータ不正".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = _ReusableServer(("localhost", PORT), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("ブラウザで認可してください…（10分でタイムアウト。中断は Ctrl+C）")
    webbrowser.open(auth_url) or print(f"開かない場合はこのURLへ:\n{auth_url}")
    try:
        if not got.wait(timeout=600):
            sys.exit("タイムアウト。もう一度実行してください。")
    except KeyboardInterrupt:
        sys.exit("\n中断しました。")
    finally:
        srv.shutdown()
    if "error" in code_holder:
        sys.exit(f"認可エラー: {code_holder['error']}\n"
                 "access_denied の場合は OAuth同意画面の「テストユーザー」に"
                 "ログインするアカウントを追加してから再実行。")

    data = urllib.parse.urlencode({
        "client_id": cid, "client_secret": csec,
        "code": code_holder["code"], "redirect_uri": redirect,
        "grant_type": "authorization_code"}).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data) as r:
        import json
        tok = json.load(r)
    rt = tok.get("refresh_token")
    if not rt:
        sys.exit("refresh_tokenが返らなかった（既存の許可を myaccount.google.com/permissions で"
                 "取り消してから prompt=consent で再実行）")
    print("\n=== 環境Secretsに登録する3つ ===")
    print(f"YT_CLIENT_ID={cid}")
    print(f"YT_CLIENT_SECRET={csec}")
    print(f"YT_REFRESH_TOKEN={rt}")


if __name__ == "__main__":
    main()
