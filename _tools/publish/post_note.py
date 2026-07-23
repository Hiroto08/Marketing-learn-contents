#!/usr/bin/env python3
"""note.com へ「下書き（非公開）」として自動保存する（Playwright／実験的）。

収益化戦略のオフYouTube導線：校了した _deliverables/note/ep*.md を note に**下書き保存**する。
YouTube側の「アップロードは非公開・公開は人間」と同じ原則で、**公開ボタンは押さない**。

    # ブラウザを起動せずパース結果だけ確認（認証不要・CIでも動く）
    python3 _tools/publish/post_note.py --file _deliverables/note/ep01_what-is-marketing.md --dry-run

    # 実際に下書き保存（要 note 認証。初回は --headful --screenshot で挙動確認を強く推奨）
    python3 _tools/publish/post_note.py --file <md> --screenshot /tmp/note.png

認証（どちらか。Secretsに登録。リポジトリ・チャットに置かない）:
  - NOTE_EMAIL / NOTE_PASSWORD … メールログイン（Googleログインのアカウントは不可）
  - NOTE_COOKIE … ログイン済みブラウザの Cookie 文字列（"name=value; name2=value2" 形式）。
                  2要素認証やbot検知を避けやすい。推奨。

⚠️ 重要な前提（正直に明記）:
  - note に公式の投稿APIは無い。本ツールは Web UI をブラウザ操作するため、
    **noteのUI変更でセレクタが変わると壊れる**。初回・UI変更時は下の SELECTORS を調整する。
  - note エディタは WYSIWYG。Markdownはそのまま貼れないため、見出し/区切りは
    noteの入力ルール（"# "→大見出し, "## "→小見出し, "---"→区切り）を type で再現する。
  - 太字・リンク書式は下書きでは簡略化される（本文は入力される）。最終見た目はnote側で微調整。
  - **常に下書き保存**。本ツールは公開操作を一切行わない。
"""
import argparse
import os
import re
import sys
import time

# ── noteのUIセレクタ（UI変更時はここだけ直す） ─────────────────────────────
LOGIN_URL = "https://note.com/login"
NEW_TEXT_URL = "https://note.com/notes/new"
SEL = {
    "login_email": 'input[type="email"], input[name="email"]',
    "login_password": 'input[type="password"], input[name="password"]',
    "login_submit": 'button[type="submit"], button:has-text("ログイン")',
    "editor_title": 'textarea[placeholder*="タイトル"], [placeholder*="記事タイトル"]',
    "editor_body": '[contenteditable="true"]',
    "save_draft": 'button:has-text("下書き保存"), button:has-text("保存")',
    "login_marker": 'text=下書き保存',   # エディタに入れたかの目印
}


# ── Markdown → note入力ブロック（--dry-runで検証可能な純ロジック） ───────────
def parse_article(path: str) -> dict:
    md = open(path, encoding="utf-8").read()
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)          # 制作メモは投稿しない
    lines = md.splitlines()

    title = ""
    blocks = []
    for ln in lines:
        s = ln.rstrip()
        if not title:
            m = re.match(r"#\s+(.+)", s)
            if m:
                title = m.group(1).strip()
                continue
        if not s.strip():
            continue
        if re.match(r"^###\s+", s):
            blocks.append(("h3", re.sub(r"^###\s+", "", s)))
        elif re.match(r"^##\s+", s):
            blocks.append(("h2", re.sub(r"^##\s+", "", s)))
        elif s.strip() == "---":
            blocks.append(("hr", ""))
        else:
            # 箇条書きの記号だけ軽く整える（note側で再整形しやすい素の文へ）
            blocks.append(("p", re.sub(r"^\s*[-*]\s+", "・", s)))
    if not title:
        raise ValueError(f"H1（記事タイトル）が見つからない: {path}")
    return {"title": title, "blocks": blocks}


# ── 認証 ──────────────────────────────────────────────────────────────────
def _cookies_from_env():
    raw = os.environ.get("NOTE_COOKIE", "").strip()
    if not raw:
        return None
    cookies = []
    for part in raw.split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            cookies.append({"name": k, "value": v, "domain": ".note.com", "path": "/"})
    return cookies or None


def login(page, context):
    cookies = _cookies_from_env()
    if cookies:
        context.add_cookies(cookies)
        page.goto("https://note.com/", wait_until="domcontentloaded")
        return
    email = os.environ.get("NOTE_EMAIL")
    pw = os.environ.get("NOTE_PASSWORD")
    if not (email and pw):
        sys.exit("認証情報が無い。NOTE_COOKIE か NOTE_EMAIL/NOTE_PASSWORD を Secrets に設定。")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.fill(SEL["login_email"], email)
    page.fill(SEL["login_password"], pw)
    page.click(SEL["login_submit"])
    page.wait_for_load_state("networkidle")


# ── 本文投入（WYSIWYGへ入力ルールで打ち込む） ──────────────────────────────
def type_body(page, blocks):
    body = page.query_selector(SEL["editor_body"])
    if not body:
        raise RuntimeError("本文エディタが見つからない（SEL['editor_body']を確認）")
    body.click()
    for kind, text in blocks:
        if kind == "h2":
            page.keyboard.type("# ")          # note: 大見出し
            page.keyboard.type(text)
        elif kind == "h3":
            page.keyboard.type("## ")         # note: 小見出し
            page.keyboard.type(text)
        elif kind == "hr":
            page.keyboard.type("---")         # note: 区切り線
        else:
            page.keyboard.type(text)
        page.keyboard.press("Enter")
        time.sleep(0.03)


def post_draft(article: dict, headful: bool, screenshot: str | None):
    from playwright.sync_api import sync_playwright
    # ブラウザは PLAYWRIGHT_BROWSERS_PATH の既定検出に任せる（環境で設定済み）
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headful)
        context = browser.new_context()
        page = context.new_page()
        try:
            login(page, context)
            page.goto(NEW_TEXT_URL, wait_until="domcontentloaded")
            page.wait_for_selector(SEL["editor_title"], timeout=20000)
            page.fill(SEL["editor_title"], article["title"])
            type_body(page, article["blocks"])
            # 下書き保存（noteは自動保存もあるが明示的に押す）
            btn = page.query_selector(SEL["save_draft"])
            if btn:
                btn.click()
                page.wait_for_timeout(2000)
            if screenshot:
                page.screenshot(path=screenshot, full_page=True)
            print(f"✓ 下書き保存を実行（公開はしていない）: 「{article['title']}」")
            print("  → note.com の「下書き一覧」で確認し、見た目を整えてから人手で公開")
        finally:
            browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="投稿する note記事 Markdown")
    ap.add_argument("--episode", help="ep_dir（_deliverables/note/ から自動解決）")
    ap.add_argument("--dry-run", action="store_true", help="ブラウザを起動せずパース結果のみ表示")
    ap.add_argument("--headful", action="store_true", help="ブラウザを表示（初回デバッグ用）")
    ap.add_argument("--screenshot", help="保存後のスクショ出力先")
    a = ap.parse_args()

    path = a.file
    if not path and a.episode:
        import glob
        cands = glob.glob(f"_deliverables/note/{os.path.basename(a.episode.rstrip('/'))}*.md") \
            or glob.glob(f"_deliverables/note/*{os.path.basename(a.episode.rstrip('/'))}*.md")
        path = cands[0] if cands else None
    if not path or not os.path.exists(path):
        ap.error("--file か --episode で有効なMarkdownを指定")

    article = parse_article(path)
    if a.dry_run:
        print(f"タイトル: {article['title']}")
        print(f"ブロック数: {len(article['blocks'])}")
        for kind, text in article["blocks"][:12]:
            print(f"  [{kind}] {text[:50]}")
        print("  …" if len(article["blocks"]) > 12 else "")
        print("\n（dry-run：ブラウザ未起動・note未接続）")
        return
    post_draft(article, a.headful, a.screenshot)


if __name__ == "__main__":
    main()
