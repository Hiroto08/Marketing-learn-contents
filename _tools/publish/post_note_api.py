#!/usr/bin/env python3
"""note.com へ「下書き（非公開）」を作成する（非公式API／requests版）。

このコンテナはブラウザ(Playwright)が外部へ出られない一方、requests/HTTPは
プロキシ越しに note へ到達できる。よって**コンテナ内の自動化（Routine）で下書き
保存するにはこのAPI版を使う**（ブラウザ版 post_note.py はローカルPC専用）。

⚠️ note に公式APIは無い。本ツールは 2026-07 の実測キャプチャに基づく非公式API利用で、
   note側の仕様変更で壊れうる。**常に下書き（非公開）まで。公開操作は一切しない。**
   draft_save の仕様は実測確定。create（空draft作成でidを得る）のみ推定なので、
   もし create で失敗したら、その1リクエストだけ再キャプチャして CONFIG['create_path'] を直す。

    # 本文HTML変換だけ確認（認証・ネットワーク不要）
    python3 _tools/publish/post_note_api.py --file _deliverables/note/ep01_*.md --dry-run

    # 実際に下書き作成（要 NOTE_COOKIE。新セッションでSecret注入後に実行）
    python3 _tools/publish/post_note_api.py --file _deliverables/note/ep01_*.md

認証: NOTE_COOKIE（"_note_session_v5=...." 形式）を Secrets に。requestsがCookieとして送る。
"""
import argparse
import os
import re
import sys
import uuid

import requests

CA = "/root/.ccr/ca-bundle.crt"
BASE = "https://note.com"
EDITOR = "https://editor.note.com"

# ── 実測キャプチャ（2026-07）で確定した仕様 ────────────────────────────────
#   新規テキストdraft作成: POST /api/v1/text_notes  → data.id を得る
#   本文保存(下書き)     : POST /api/v1/text_notes/draft_save?id=<id>&is_temp_saved=true
#   payload: {name(title), body(HTML), body_length(int), index:false, is_lead_form:false}
#   認証: _note_session_v5 クッキー ＋ X-Requested-With ＋ Origin/Referer=editor.note.com
CONFIG = {
    "create_path": "/api/v1/text_notes",       # 空draft作成（idの発行元。※createのみ推定）
    "save_path": "/api/v1/text_notes/draft_save",
}


# ── Markdown → note本文HTML（ブロックに name=uuid を付与） ──────────────────
def md_to_html(path: str):
    md = open(path, encoding="utf-8").read()
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    title, html, text_len = "", [], 0

    def blk(tag, inner, plain):
        nonlocal text_len
        text_len += len(plain)
        html.append(f'<{tag} name="{uuid.uuid4().hex[:12]}">{inner}</{tag}>')

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
            t = re.sub(r"^###\s+", "", s)
            blk("h3", esc(t), t)
        elif re.match(r"^##\s+", s):
            t = re.sub(r"^##\s+", "", s)
            blk("h2", esc(t), t)
        elif s.strip() == "---":
            html.append(f'<hr name="{uuid.uuid4().hex[:12]}">')
        else:
            t = re.sub(r"^\s*[-*]\s+", "・", s)
            inner = re.sub(r"(https?://[^\s　]+)", r'<a href="\1">\1</a>', esc(t))
            blk("p", inner, t)
    if not title:
        raise ValueError(f"H1が無い: {path}")
    return title, "\n".join(html), text_len


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
    s.headers.update({"X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/json",
                      "Accept": "application/json",
                      "Origin": EDITOR, "Referer": f"{EDITOR}/"})
    return s


def _find_id(obj):
    """レスポンスJSONから draft の id を再帰的に拾う"""
    if isinstance(obj, dict):
        for k in ("id", "key", "note_id"):
            if k in obj and isinstance(obj[k], (int, str)):
                return obj[k]
        for v in obj.values():
            r = _find_id(v)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_id(v)
            if r is not None:
                return r
    return None


def create_draft(title: str, html: str, body_len: int):
    s = session()
    # 1) 空のtext_noteを作成して id を得る
    c = s.post(f"{BASE}{CONFIG['create_path']}", json={}, timeout=30)
    if c.status_code not in (200, 201):
        sys.exit(f"draft作成失敗 {c.status_code}: {c.text[:300]}\n"
                 "→ createエンドポイントが変わっている可能性（この1件だけ再キャプチャを）。")
    did = _find_id(c.json())
    if did is None:
        sys.exit(f"作成レスポンスから id を取得できず: {c.text[:300]}")
    # 2) 本文を下書き保存
    url = f"{BASE}{CONFIG['save_path']}?id={did}&is_temp_saved=true"
    payload = {"name": title, "body": html, "body_length": body_len,
               "index": False, "is_lead_form": False}
    r = s.post(url, json=payload, timeout=30)
    print(f"draft_save id={did} → {r.status_code}")
    if r.status_code in (200, 201):
        print(f"✓ 下書き（非公開）を保存しました。編集URL: {EDITOR}/notes/{did}/edit")
        print("  note.comの「下書き」一覧で見た目を整え、公開は人間が行う。")
    else:
        print(f"✗ 保存失敗: {r.text[:300]}")
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    title, html, body_len = md_to_html(a.file)
    if a.dry_run:
        print(f"タイトル: {title}")
        print(f"本文HTML（先頭500字）:\n{html[:500]}")
        print(f"\nHTML長: {len(html)} / body_length(本文字数): {body_len}")
        print(f"送信payload形: {{name, body, body_length:{body_len}, index:false, is_lead_form:false}}")
        print("（dry-run：note未接続）")
        return
    create_draft(title, html, body_len)


if __name__ == "__main__":
    main()
