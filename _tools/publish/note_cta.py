#!/usr/bin/env python3
"""note_cta.py — note 記事本文（HTML）に YouTube への導線を差し込む（post_note_api.py から使う）。

差し込む導線（冪等：再実行すると前回分を消して最新の内容で入れ直す）
  1. 冒頭（リード直後）：「図解つきの動画版」の一言＋動画プレーヤー埋め込み（note の YouTube 埋め込み）
  2. 中盤（真ん中の見出しの直前）：その章を動画の該当時刻から見られるリンク（youtu.be/ID?t=秒）
  3. 末尾（🎬動画リンクの直後）：全24話の再生リスト／チャンネル登録（sub_confirmation）／次の回（動画・記事）
埋め込みHTMLは note の GET /api/v2/embed_by_external_api が返すもの（editor と同じ）を
<figure embedded-service="youtube" ...> で包む（editor の embed ノード toDOM と同じ属性）。
"""
import datetime as dt
import glob
import os
import re
import uuid

CHANNEL = "https://www.youtube.com/channel/UCZm9m37ivzDN0ZGvQAhBDpw"
PLAYLIST = "https://www.youtube.com/playlist?list=PLazN5XmDSQHo"   # 全24話（第1回から順に）
NOTE_USER = "marketing_lab_jp"
JST = dt.timezone(dt.timedelta(hours=9))

# 前回差し込んだ段落の目印（本文の先頭文字列）。ここに無い段落は触らない
MARKS = ("📺 図解つきの動画版", "▶ この章は動画", "📚 第1回から順に", "🔔 チャンネル登録", "▶ 次の回", "▶ 次回",
         "📺 チャンネル（全話）")


def _id():
    return str(uuid.uuid4())


def _p(inner):
    i = _id()
    return f'<p name="{i}" id="{i}">{inner}</p>'


def _a(url, text=None):
    return f'<a href="{url}" rel="nofollow noopener">{text or url}</a>'


def _text(html_s):
    return re.sub(r"<[^>]+>", "", html_s)


# ── データ（ローカルの状態表から） ─────────────────────────────────────────
def video_row(ep):
    """(videoId, 状態) — docs/upload-status.md"""
    t = open("docs/upload-status.md", encoding="utf-8").read()
    m = re.search(rf"^\| EP{ep:02d} \| [^|]*\| `?([\w-]+)?`? \| ([^|]+)\|", t, re.M)
    return (m[1], m[2].strip()) if m else (None, None)


def ep_dir(ep):
    return next((d for d in glob.glob(f"0*/ep{ep:02d}_*") if os.path.isdir(d)), None)


def slides(ep):
    """[(秒, スライド見出し)] — script.md の「### スライド N：見出し（M:SS〜M:SS）」"""
    d = ep_dir(ep)
    if not d or not os.path.exists(f"{d}/script.md"):
        return []
    out = []
    for m in re.finditer(r"^###[^\n]*スライド\s*\d+\s*[：:]\s*([^（\n]+)（(\d+):(\d+)", open(f"{d}/script.md", encoding="utf-8").read(), re.M):
        out.append((int(m[2]) * 60 + int(m[3]), m[1].strip()))
    return out


def minutes(ep):
    d = ep_dir(ep)
    if not d or not os.path.exists(f"{d}/script.md"):
        return 9
    ends = [int(a) * 60 + int(b) for a, b in re.findall(r"〜(\d+):(\d+)）", open(f"{d}/script.md", encoding="utf-8").read())]
    return max(1, round(max(ends) / 60)) if ends else 9


def note_title(ep):
    p = sorted(glob.glob(f"_deliverables/note/ep{ep:02d}_*.md"))
    if not p:
        return None
    m = re.search(r"^#\s+(.+)$", open(p[0], encoding="utf-8").read(), re.M)
    return m[1].strip() if m else None


def _common(a, b):
    best = 0
    for i in range(len(a)):
        for j in range(i + best + 1, len(a) + 1):
            if a[i:j] in b:
                best = j - i
            else:
                break
    return best


def chapter_time(ep, heading):
    """見出しに最も似たスライドの開始秒（共通部分4文字以上）"""
    best = (0, None)
    for sec, title in slides(ep):
        c = _common(heading, title)
        if c > best[0]:
            best = (c, sec)
    return best[1] if best[0] >= 4 else None


# ── 本文の変換 ──────────────────────────────────────────────────────────────
BLOCK = re.compile(r"<(p|h2|h3|figure|ul|ol|pre|blockquote)\b[^>]*>.*?</\1>|<hr\b[^>]*>", re.S)


def split_blocks(body):
    return [m.group(0) for m in BLOCK.finditer(body)]


def strip_ours(blocks, vid):
    out = []
    for b in blocks:
        if b.startswith("<p") and _text(b).strip().startswith(MARKS):
            continue
        if b.startswith("<figure") and 'embedded-service="youtube"' in b and vid and vid in b:
            continue
        out.append(b)
    return out


def enhance(body, ep, embed_html, embed_key, next_info):
    """本文HTMLに導線を差し込んだ新しい本文を返す。next_info = 末尾「次の回」の段落の中身（HTML）か None"""
    vid, _ = video_row(ep)
    if not vid:
        return body
    url = f"https://youtu.be/{vid}"
    raw = split_blocks(body)
    squash = lambda h: re.sub(r">\s+<", "><", h.strip())  # noqa: E731
    if not raw or squash("".join(raw)) != squash(body):
        print(f"  （EP{ep:02d}: 本文をブロックに完全分解できない構造 → 内容を失わないよう導線の差し込みは省略）")
        return body
    blocks = strip_ours(raw, vid)
    heads = [i for i, b in enumerate(blocks) if b.startswith("<h2")]
    # 2. 中盤：真ん中の見出しの直前に、その章の時刻つきリンク（前に入れると添字がずれるので先に）
    if len(heads) >= 3:
        hi = heads[(len(heads) - 1) // 2] if len(heads) > 4 else heads[1]
        h = _text(blocks[hi])
        sec = chapter_time(ep, h)
        if sec:
            link = _a(f"{url}?t={sec}", f"{url}?t={sec}")
            blocks.insert(hi, _p(f"▶ この章は動画の {sec // 60}:{sec % 60:02d} から図解つきで見られます → {link}"))
    # 1. 冒頭：リード（「読み終える頃には」の段落、無ければ最初の見出しの前）の直後に埋め込み
    lead = next((i for i, b in enumerate(blocks[:6]) if "読み終える頃には" in _text(b)), None)
    pos = lead + 1 if lead is not None else next((i for i, b in enumerate(blocks) if b.startswith("<h2")), 1)
    fid = _id()
    fig = (f'<figure name="{fid}" id="{fid}" data-src="{url}" data-identifier="null" embedded-service="youtube" '
           f'embedded-content-key="{embed_key}">{embed_html}</figure>')
    blocks[pos:pos] = [_p(f"📺 図解つきの動画版（約{minutes(ep)}分）もあります。先に動画で全体像をつかむのもおすすめです👇"), fig]
    # 3. 末尾：🎬動画リンクの直後（無ければハッシュタグ段落の前／最後）に回遊導線
    end = next((i + 1 for i in range(len(blocks) - 1, -1, -1) if _text(blocks[i]).strip().startswith("🎬")), None)
    if end is None:
        end = next((i for i in range(len(blocks) - 1, -1, -1) if _text(blocks[i]).strip().startswith("#")), len(blocks))
    tail = [_p(f"📚 第1回から順に見る（全24話の再生リスト）：{_a(PLAYLIST)}"),
            _p(f"🔔 チャンネル登録で新しい回（毎週水・土18時）を受け取る：{_a(CHANNEL + '?sub_confirmation=1')}")]
    if next_info:
        tail.append(_p(next_info))
    blocks[end:end] = tail
    return "".join(blocks)


def next_info(ep, my_notes_by_id, rows):
    """末尾「次の回」段落。動画が公開済みならURL、記事が公開済みなら記事URL、未公開なら公開予定日"""
    nxt = ep + 1
    title = note_title(nxt)
    if not title:
        return None
    vid, st = video_row(nxt)
    parts = []
    if vid and st == "public":
        parts.append(f"動画 {_a('https://youtu.be/' + vid)}")
    row = rows.get(nxt)
    n = my_notes_by_id.get(int(row["note_id"])) if row and row["note_id"].isdigit() else None
    if n and n.get("status") == "published" and n.get("key"):
        parts.append(f"記事 {_a(f'https://note.com/{NOTE_USER}/n/' + n['key'])}")
    if parts:
        return f"▶ 次の回：「{title}」 " + " ／ ".join(parts)
    if st and st.startswith("予約"):
        t = dt.datetime.strptime(st[3:].strip(), "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc).astimezone(JST)
        wd = "月火水木金土日"[t.weekday()]
        return f"▶ 次回「{title}」は {t.month}/{t.day}（{wd}）{t.hour}時に動画公開予定です（チャンネル登録で通知が届きます）"
    return f"▶ 次回は「{title}」です（チャンネル登録で公開の通知が届きます）"
