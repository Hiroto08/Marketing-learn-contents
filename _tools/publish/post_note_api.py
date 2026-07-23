#!/usr/bin/env python3
"""note.com へ「下書き（非公開）」を作成する（非公式API／requests版）。

このコンテナはブラウザ(Playwright)が外部へ出られない一方、requests/HTTPは
プロキシ越しに note へ到達できる。よって**コンテナ内の自動化（Routine）で下書き
保存するにはこのAPI版を使う**（ブラウザ版 post_note.py はローカルPC専用）。

⚠️ note に公式APIは無い。下書き作成の正確なエンドポイント/ペイロードは非公開かつ
   変動する（2026-02にも仕様変更）。**初回は実ブラウザで「下書き保存」した時の
   ネットワークリクエストを1件キャプチャし、下の CONFIG を実測に合わせて確定する**こと。

    # 本文HTML変換だけ確認（認証・ネットワーク不要）
    python3 _tools/publish/post_note_api.py --file _deliverables/note/ep01_*.md --dry-run

    # 実際に下書き作成（要 NOTE_COOKIE。CONFIGが実測で確定してから）
    python3 _tools/publish/post_note_api.py --file _deliverables/note/ep01_*.md

認証: NOTE_COOKIE（"_note_session_v5=...." 形式）を Secrets に。requestsがCookieとして送る。

── 初回キャプチャ手順（1回だけ・あなた側）──────────────────────────────
  1. PCブラウザで note にログイン → 新規テキスト記事を1つ作り、適当に入力して「下書き保存」
  2. F12 → Network タブ → 「下書き保存」を押した瞬間に飛ぶ XHR/fetch を探す
     （Fetch/XHR で絞り込み、Name が text_notes / draft などのPOST/PUT）
  3. その1件の以下を控える（値そのものは伏せてよい・形が分かればよい）：
     - Request URL（例 https://note.com/api/v1/text_notes/... ）
     - Method（POST か PUT か）
     - Request Headers のうち X-Xsrf-Token / X-Requested-With 等の有無
     - Request Payload（JSONのキー名。例 name/title, body, status など）
  → これを共有してもらえれば下の CONFIG を確定して完成できる。
────────────────────────────────────────────────────────────────
"""
import argparse
import os
import re
import sys

import requests

CA = "/root/.ccr/ca-bundle.crt"
BASE = "https://note.com"

# ── CONFIG：初回キャプチャで確定する箇所（現状は既知構造ベースの暫定値） ──────
CONFIG = {
    # 下書き作成/保存のエンドポイントとメソッド（★キャプチャで要確認）
    "create_path": "/api/v1/text_notes",       # 暫定。実測で上書き（NOTE_DRAFT_PATHでも可）
    "create_method": "POST",
    # ペイロードのキー名（★キャプチャで要確認）
    "key_title": "name",
    "key_body": "body",
    "key_status": "status",
    "status_draft_value": "draft",             # 下書き＝非公開を表す値
    "confirmed": False,                          # 実測で確認できたら True（安全ガード）
}


# ── Markdown → note本文HTML ────────────────────────────────────────────────
def md_to_html(path: str):
    md = open(path, encoding="utf-8").read()
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    title, html = "", []
    for ln in md.splitlines():
        s = ln.rstrip()
        if not title:
            m = re.match(r"#\s+(.+)", s)
            if m:
                title = m.group(1).strip()
                continue
        if not s.strip():
            continue
        if re.match(r"^###\s+", s):
            txt = esc(re.sub(r"^###\s+", "", s))
            html.append(f"<h3>{txt}</h3>")
        elif re.match(r"^##\s+", s):
            txt = esc(re.sub(r"^##\s+", "", s))
            html.append(f"<h2>{txt}</h2>")
        elif s.strip() == "---":
            html.append("<hr>")
        else:
            body = esc(re.sub(r"^\s*[-*]\s+", "・", s))
            body = re.sub(r"(https?://[^\s　]+)", r'<a href="\1">\1</a>', body)
            html.append(f"<p>{body}</p>")
    if not title:
        raise ValueError(f"H1が無い: {path}")
    return title, "\n".join(html)


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── 認証つき requests セッション ───────────────────────────────────────────
def session() -> requests.Session:
    raw = os.environ.get("NOTE_COOKIE", "").strip()
    if not raw:
        sys.exit("NOTE_COOKIE が未設定（Secretsに _note_session_v5=... を登録）。")
    s = requests.Session()
    s.verify = CA
    proxy = os.environ.get("HTTPS_PROXY")
    if proxy:
        s.proxies = {"https": proxy, "http": proxy}
    for part in raw.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            s.cookies.set(k, v, domain=".note.com")
    # XSRFトークン取得（note書き込みは X-Xsrf-Token を要求することが多い）
    s.get(f"{BASE}/", timeout=20)
    xsrf = s.cookies.get("XSRF-TOKEN")
    if xsrf:
        s.headers.update({"X-Xsrf-Token": xsrf})
    s.headers.update({"X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/json",
                      "Origin": BASE, "Referer": f"{BASE}/notes/new"})
    return s


def create_draft(title: str, html: str):
    if not CONFIG["confirmed"] and not os.environ.get("NOTE_FORCE"):
        sys.exit("CONFIG が実測で未確認（confirmed=False）。初回キャプチャで "
                 "エンドポイント/ペイロードを確定してから実行するか、検証目的なら "
                 "NOTE_FORCE=1 を付けて試す（失敗しても安全＝下書きAPIのみ）。")
    s = session()
    path = os.environ.get("NOTE_DRAFT_PATH", CONFIG["create_path"])
    payload = {CONFIG["key_title"]: title, CONFIG["key_body"]: html,
               CONFIG["key_status"]: CONFIG["status_draft_value"]}
    r = s.request(CONFIG["create_method"], f"{BASE}{path}", json=payload, timeout=30)
    print(f"POST {path} → {r.status_code}")
    print(r.text[:400])
    if r.status_code in (200, 201):
        print("✓ 下書き作成の可能性（note.comの下書き一覧で要確認・公開はしない）")
    else:
        print("✗ 失敗。キャプチャした実際のURL/メソッド/キー名にCONFIGを合わせる必要あり。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    title, html = md_to_html(a.file)
    if a.dry_run:
        print(f"タイトル: {title}")
        print(f"本文HTML（先頭600字）:\n{html[:600]}")
        print(f"\n生成HTML長: {len(html)}字 / CONFIG.confirmed={CONFIG['confirmed']}")
        print("（dry-run：note未接続。実投稿は初回キャプチャでCONFIG確定後）")
        return
    create_draft(title, html)


if __name__ == "__main__":
    main()
