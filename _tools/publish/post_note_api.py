#!/usr/bin/env python3
"""note.com へ「下書き（非公開）」を作成する／下書きを公開する（非公式API／requests版）。

このコンテナはブラウザ(Playwright)が外部へ出られない一方、requests/HTTPは
プロキシ越しに note へ到達できる。よって**コンテナ内の自動化（Routine）ではこのAPI版を使う**
（ブラウザ版 post_note.py はローカルPC専用）。

⚠️ note に公式APIは無い。本ツールは実測キャプチャに基づく非公式API利用で、note側の仕様変更で壊れうる。
   - 下書き作成（--file）：2026-07 キャプチャ。draft_save は実測確定、create のみ推定。
   - 公開（--publish-ep）：2026-10-17 キャプチャ（HAR）＋ editor.note.com の公開画面コードで確定。
       GET  /api/v3/notes/<id>?draft=true           … 下書き本文・key・見出し画像の有無を取得
       POST /api/v1/image_upload/note_eyecatch      … 見出し画像（multipart: note_id, file, width=1920, height=1005）
       PUT  /api/v1/text_notes/<id>  status=published … 公開（本文はサーバ上の最新下書きをそのまま送る＝手直しを保持）
     **公開は --publish-ep だけ**。note-draft-status.md が「下書き保存済み」かつ docs/upload-status.md で
     同じEPの YouTube 本編が public の回しか公開しない（--force で動画チェックのみ省略可）。成功したら
     note-draft-status.md の status を「公開済み YYYY-MM-DD」に書き換える。
   失敗（4xx・仕様変化）時は推測で直さず停止。その1リクエストだけ再キャプチャして直す。

    # 本文HTML変換だけ確認（認証・ネットワーク不要）
    python3 _tools/publish/post_note_api.py --file _deliverables/note/ep01_*.md --dry-run

    # 実際に下書き作成（要 NOTE_COOKIE。新セッションでSecret注入後に実行）
    python3 _tools/publish/post_note_api.py --file _deliverables/note/ep01_*.md

    # 公開（--dry-run は読み取りGETのみで送信内容を表示）
    python3 _tools/publish/post_note_api.py --publish-ep 1 --dry-run
    python3 _tools/publish/post_note_api.py --publish-ep 1

認証: NOTE_COOKIE（"_note_session_v5=...." 形式）を Secrets に。requestsがCookieとして送る。
"""
import argparse
import datetime as dt
import html as htmlmod
import os
import re
import sys
import time
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
    # note側WAF(CloudFront)がUA無しのPOSTを403で弾くため、ブラウザ相当のUAを必ず送る
    s.headers.update({"X-Requested-With": "XMLHttpRequest",
                      "Content-Type": "application/json",
                      "Accept": "application/json",
                      "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                                     "Chrome/126.0.0.0 Safari/537.36"),
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


# ── 公開（2026-10-17 HAR＋editor公開画面コードで確定） ───────────────────────
STATUS = "_deliverables/note/note-draft-status.md"
ROW = re.compile(r"^\| EP(\d+) \| ([^|]*?) \| ([^|]*?) \| ([^|]*?) \| ([^|]*?) \| ([^|]*?) \|$", re.M)


def status_rows() -> dict:
    t = open(STATUS, encoding="utf-8").read()
    return {int(m[1]): {"file": m[2].strip(), "status": m[3].strip(), "note_id": m[4].strip(),
                        "edit_url": m[5].strip(), "saved_at": m[6].strip()} for m in ROW.finditer(t)}


def set_status(ep: int, status: str):
    t = open(STATUS, encoding="utf-8").read()

    def rep(m):
        if int(m[1]) != ep:
            return m[0]
        return f"| EP{m[1]} | {m[2]} | {status} | {m[4]} | {m[5]} | {m[6]} |"
    open(STATUS, "w", encoding="utf-8").write(ROW.sub(rep, t))


def video_is_public(ep: int) -> bool:
    t = open("docs/upload-status.md", encoding="utf-8").read()
    m = re.search(rf"^\| EP{ep:02d} \| [^|]*\| [^|]*\| ([^|]+)\|", t, re.M)
    return bool(m) and m[1].strip() == "public"


def hashtags_from(md_path: str) -> list:
    for ln in reversed(open(md_path, encoding="utf-8").read().splitlines()):
        s = ln.strip()
        if re.fullmatch(r"#[^\s#]+(?:\s+#[^\s#]+)*", s):
            return s.split()
    return []


def text_len(body_html: str) -> int:
    t = re.sub(r"<[^>]+>", "", body_html)
    return len(htmlmod.unescape(t))


def my_notes(s) -> dict:
    """{id: {key, status, publishAt, name}} — 自分の全記事（下書き＋公開）。/v2/note_list/contents（読み取り）"""
    out, page = {}, 1
    while True:
        r = s.get(f"{BASE}/api/v2/note_list/contents",
                  params={"limit": 50, "page": page, "without_magazines": "true"}, timeout=30)
        if r.status_code in (401, 403):
            sys.exit(f"一覧取得 {r.status_code}：_note_session_v5 Cookie の期限切れの可能性（Secretを更新）")
        if r.status_code != 200:
            sys.exit(f"記事一覧の取得失敗 {r.status_code}: {r.text[:200]}")
        notes = (r.json().get("data") or {}).get("notes") or []
        for n in notes:
            out[int(n["id"])] = {"key": n.get("key"), "status": n.get("status"),
                                 "publishAt": n.get("publishAt") or n.get("publish_at"), "name": n.get("name")}
        if len(notes) < 50 or page >= 20:
            return out
        page += 1


def fetch_note(s, key, nid, draft=True) -> dict:
    r = s.get(f"{BASE}/api/v3/notes/{key}", params={"draft": "true" if draft else "false", "draft_reedit": "false",
                                                     "ts": int(time.time() * 1000)}, timeout=30)
    if r.status_code in (401, 403):
        sys.exit(f"取得 {r.status_code}：_note_session_v5 Cookie の期限切れの可能性（Secretを更新）")
    if r.status_code != 200:
        sys.exit(f"note取得失敗 {r.status_code}: {r.text[:200]}")
    d = r.json().get("data") or {}
    if str(d.get("id")) != str(nid):
        sys.exit(f"取得したnoteのidが一致しない（{d.get('id')} != {nid}）→ 停止")
    return d


def sync_status(s=None, quiet=False) -> dict:
    """note 上で公開済みなのに状態表が未反映の回を「公開済み YYYY-MM-DD」に直す（手動公開の取り込み）"""
    s = s or session()
    notes = my_notes(s)
    for ep, row in sorted(status_rows().items()):
        n = notes.get(int(row["note_id"])) if row["note_id"].isdigit() else None
        if n and n["status"] == "published" and not row["status"].startswith("公開済み"):
            day = (n["publishAt"] or "")[:10] or f"{dt.date.today():%Y-%m-%d}"
            set_status(ep, f"公開済み {day}")
            if not quiet:
                print(f"EP{ep:02d}: note上で公開済み（{day}）→ 状態表を更新")
    return notes


def upload_eyecatch(s, nid, png: str) -> str:
    with open(png, "rb") as f:
        r = s.post(f"{BASE}/api/v1/image_upload/note_eyecatch",
                   files={"file": (os.path.basename(png), f, "image/png")},
                   data={"note_id": str(nid), "width": "1920", "height": "1005"},
                   headers={"Content-Type": None}, timeout=60)
    j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code not in (200, 201) or j.get("error") or not (j.get("data") or {}).get("url"):
        sys.exit(f"見出し画像アップロード失敗 {r.status_code}: {r.text[:200]}")
    return j["data"]["url"]


def note_payload(d, body, name, tags, notify):
    """PUT /api/v1/text_notes/<id> の本文（2026-10-17 HAR の公開リクエストと同形）"""
    return {"author_ids": [], "body_length": text_len(body), "disable_comment": bool(d.get("disable_comment")),
            "exclude_from_creator_top": bool(d.get("exclude_from_creator_top")),
            "exclude_ai_learning_reward": bool(d.get("exclude_ai_learning_reward")),
            "free_body": body, "hashtags": tags, "image_keys": [], "index": False, "is_refund": False,
            "limited": False, "magazine_ids": [], "magazine_keys": list(d.get("belonging_magazine_keys") or []),
            "name": name, "pay_body": "", "price": 0, "send_notifications_flag": notify, "separator": None,
            "slug": d.get("slug") or f"slug-{d['key']}", "status": "published", "circle_permissions": [],
            "discount_campaigns": [], "lead_form": {"is_active": False, "consent_url": ""},
            "line_add_friend": {"is_active": False, "keyword": "", "add_friend_url": ""},
            "line_add_friend_access_token": uuid.uuid4().hex, "pro_coupon_keys": []}


def put_note(s, nid, payload):
    r = s.put(f"{BASE}/api/v1/text_notes/{nid}", json=payload, timeout=60)
    j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    data = j.get("data") or {}
    if r.status_code != 200 or data.get("status") != "published":
        sys.exit(f"公開/更新失敗 {r.status_code}: {r.text[:300]}")
    return data


def with_cta(s, d, ep, body, notes):
    """本文に YouTube 導線（冒頭の動画埋め込み・章の時刻リンク・末尾の回遊リンク）を差し込む（note_cta.py）"""
    import note_cta
    vid, st = note_cta.video_row(ep)
    if not vid or st != "public":
        print(f"  （EP{ep:02d} の動画が public でないため導線の差し込みは省略）")
        return body
    r = s.get(f"{BASE}/api/v2/embed_by_external_api", params={"url": f"https://youtu.be/{vid}", "service": "youtube",
                                                              "embeddable_key": d["key"], "embeddable_type": "Note"}, timeout=30)
    e = (r.json().get("data") or {}) if r.status_code == 200 else {}
    if not e.get("html_for_embed") or not e.get("key"):
        print(f"  （動画埋め込みの取得に失敗 {r.status_code}：導線の差し込みは省略）")
        return body
    return note_cta.enhance(body, ep, e["html_for_embed"], e["key"], note_cta.next_info(ep, notes, status_rows()))


def outline(body):
    import note_cta
    out = []
    for b in note_cta.split_blocks(body):
        t = note_cta._text(b).strip()
        if b.startswith("<figure"):
            out.append("  [動画埋め込み]")
        elif t.startswith(note_cta.MARKS) or t.startswith("🎬"):
            out.append("  " + t[:70])
    return "\n".join(out)


def update_cta(ep: int, dry: bool, s=None, notes=None):
    """公開済みの記事の導線を最新化（冒頭埋め込み・章リンク・次の回など）。本文の他の部分は変えない"""
    row = status_rows().get(ep)
    if not row or not row["note_id"].isdigit():
        print(f"EP{ep:02d}: 状態表に note_id が無い → スキップ")
        return
    s = s or session()
    notes = notes if notes is not None else my_notes(s)
    nid = int(row["note_id"])
    n = notes.get(nid)
    if not n or n["status"] != "published":
        print(f"EP{ep:02d}: note 上で未公開 → スキップ（公開時に --publish-ep が差し込む）")
        return
    d = fetch_note(s, n["key"], nid, draft=False)
    body, name = d.get("body"), d.get("name")
    if not body or not name:
        sys.exit(f"EP{ep:02d}: 公開本文が取得できない → 停止")
    new = with_cta(s, d, ep, body, notes)

    def norm(h):  # id・埋め込みキー・埋め込み中身の違いは「変更」とみなさない
        h = re.sub(r'\s(?:name|id|embedded-content-key)="[^"]*"', "", h)
        return re.sub(r"(<figure[^>]*>).*?</figure>", r"\1</figure>", h, flags=re.S)
    if norm(new) == norm(body):
        print(f"EP{ep:02d}: 変更なし")
        return
    tags = [h["hashtag"]["name"] for h in d.get("hashtag_notes") or [] if h.get("hashtag", {}).get("name")]
    print(f"EP{ep:02d}「{name}」 導線を更新:\n{outline(new)}")
    if dry:
        print("  [dry] 送信していない")
        return
    data = put_note(s, nid, note_payload(d, new, name, tags, notify=False))
    print(f"  ✓ 更新: {data.get('note_url')}")


def publish_ep(ep: int, dry: bool, force: bool):
    row = status_rows().get(ep)
    if not row:
        sys.exit(f"EP{ep:02d} が {STATUS} に無い")
    if row["status"].startswith("公開済み"):
        print(f"EP{ep:02d} は既に公開済み（{row['status']}）→ 何もしない")
        return
    if row["status"] != "下書き保存済み" or not row["note_id"].isdigit():
        sys.exit(f"EP{ep:02d} は公開できる状態でない（status={row['status']} note_id={row['note_id']}）")
    if not video_is_public(ep) and not force:
        sys.exit(f"EP{ep:02d} の YouTube 本編がまだ public でない（docs/upload-status.md）→ 記事の動画リンクが切れるので公開しない")
    md = f"_deliverables/note/{row['file']}"
    png = f"_deliverables/note/thumbnails/ep{ep:02d}.png"
    nid = int(row["note_id"])
    s = session()
    notes = my_notes(s)
    n = notes.get(nid)
    if not n or not n.get("key"):
        sys.exit(f"note_id {nid} が自分の記事一覧に無い（削除済み？）→ 停止")
    if n["status"] == "published":
        print(f"EP{ep:02d} は note 上で既に公開済み（{n['publishAt']}）→ 状態表だけ更新")
        if not dry:
            set_status(ep, f"公開済み {(n['publishAt'] or '')[:10]}")
        return
    d = fetch_note(s, n["key"], nid)
    if d.get("status") != "draft":
        sys.exit(f"想定外の status={d.get('status')} → 停止")
    draft = d.get("note_draft") or {}
    body, name = draft.get("body") or d.get("body"), draft.get("name") or d.get("name")
    if not body or not name:
        sys.exit("下書き本文/タイトルが取得できない → 停止")
    body = with_cta(s, d, ep, body, notes)
    tags = hashtags_from(md)
    payload = note_payload(d, body, name, tags, notify=True)
    eyecatch = d.get("eyecatch")
    print(f"EP{ep:02d} id={nid} key={d.get('key')}「{name}」 本文{payload['body_length']}字 タグ{len(tags)}個 "
          f"見出し画像={'設定済み' if eyecatch else ('アップロード予定 ' + png if os.path.exists(png) else 'なし')}")
    print(outline(body))
    if dry:
        print("[dry] 読み取りのみ。アップロード・公開はしていない")
        return
    if not eyecatch:
        if not os.path.exists(png):
            sys.exit(f"見出し画像 {png} が無い → make_note_thumbnail.py で生成してから再実行")
        print("  見出し画像:", upload_eyecatch(s, nid, png))
    data = put_note(s, nid, payload)
    set_status(ep, f"公開済み {dt.datetime.now(dt.timezone(dt.timedelta(hours=9))):%Y-%m-%d}")
    print(f"✓ 公開: {data.get('note_url')}  （{STATUS} を更新）")
    # 前の回の「次の回」リンクをこの回の記事URLへ更新（非致命）
    if ep > 1:
        try:
            update_cta(ep - 1, False, s, my_notes(s))
        except SystemExit as e:
            print(f"  （EP{ep - 1:02d} の導線更新に失敗：{e}）")


def ep_list(spec: str):
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="下書き作成するMarkdown")
    g.add_argument("--publish-ep", type=int, help="この回の下書きを公開（見出し画像も設定）")
    g.add_argument("--sync-status", action="store_true", help="note上の公開状態を状態表に取り込む（読み取りのみ）")
    g.add_argument("--update-cta", help="公開済み記事のYouTube導線を最新化（例 12 / 1-12 / 3,5）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="--publish-ep で YouTube 公開チェックを省略")
    a = ap.parse_args()
    if a.sync_status:
        sync_status()
        return
    if a.update_cta:
        s = session()
        notes = my_notes(s)
        for ep in ep_list(a.update_cta):
            update_cta(ep, a.dry_run, s, notes)
        return
    if a.publish_ep:
        publish_ep(a.publish_ep, a.dry_run, a.force)
        return
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
