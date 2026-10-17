#!/usr/bin/env python3
"""note_publish_schedule.py — note 記事の公開スケジュール（追いつき＋動画同期）を作る。

ルール:
- 1日1本・毎日 20:00 JST（--hour で変更可）。EP番号の昇順。
- EPn の note は、YouTube の EPn 本編が公開される日より前には出さない（記事CTAの動画リンクが非公開で切れるため）。
  → 動画が公開済みの回は毎日の枠で順に追いつき、追いついた後は動画の公開日（水・土）に揃う。
- 既に note で公開済みの回（note-draft-status.md の status＝公開済み）は枠を使わない。
- 動画の公開日は docs/upload-status.md（public／予約 publishAt）。非公開で予約なしの回は
  publish_episode.py と同じ「水・土 18:00 JST」の連鎖を仮定して見積もる。

出力: _deliverables/note/note-publish-schedule.md（日付・EP・タイトル・編集URL・動画公開日）
  python3 _tools/publish/note_publish_schedule.py [--start 2026-10-18] [--hour 20]
"""
import argparse
import datetime as dt
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from publish_episode import JST, next_slot  # noqa: E402

STATUS = "_deliverables/note/note-draft-status.md"
OUT = "_deliverables/note/note-publish-schedule.md"


def video_dates(now):
    """{ep: datetime|None(=公開済み)}"""
    rows = re.findall(r"^\| EP(\d+) \| [^|]*\| `?([\w-]+)?`? \| ([^|]+)\|", open("docs/upload-status.md", encoding="utf-8").read(), re.M)
    out, last = {}, now + dt.timedelta(hours=1)   # publish_episode.py --schedule-all と同じ起点
    for ep, vid, st in sorted(rows, key=lambda r: int(r[0])):
        ep, st = int(ep), st.strip()
        if st == "public":
            out[ep] = None
        elif st.startswith("予約"):
            t = dt.datetime.strptime(st[3:].strip(), "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc)
            out[ep] = last = t
        elif st in ("private", "unlisted"):
            last = next_slot(last, {2, 5})   # 水・土 18:00 JST の連鎖を仮定
            out[ep] = last
    return out


def drafts():
    """[(ep, status, edit_url, file)]"""
    out = []
    for ep, f, st, nid, url in re.findall(r"^\| EP(\d+) \| ([^|]+)\| ([^|]+)\| ([^|]+)\| ([^|]+)\|", open(STATUS, encoding="utf-8").read(), re.M):
        out.append((int(ep), st.strip(), url.strip(), f.strip()))
    return sorted(out)


def title(f):
    p = f"_deliverables/note/{f}"
    if not os.path.exists(p):
        return "（未作成）"
    m = re.search(r"^#\s+(.+)$", open(p, encoding="utf-8").read(), re.M)
    return m[1].strip() if m else f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", help="最初の枠の日付 YYYY-MM-DD（省略：今日の枠が過ぎていれば明日）")
    ap.add_argument("--hour", type=int, default=20)
    a = ap.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    vd = video_dates(now)
    if a.start:
        slot = dt.datetime.fromisoformat(a.start).replace(hour=a.hour, tzinfo=JST)
    else:
        slot = now.astimezone(JST).replace(hour=a.hour, minute=0, second=0, microsecond=0)
        if slot <= now + dt.timedelta(minutes=30):
            slot += dt.timedelta(days=1)
    rows = []
    for ep, st, url, f in drafts():
        if st.startswith("公開済み"):
            rows.append((ep, "公開済み", title(f), url, vd.get(ep), st))
            continue
        v = vd.get(ep)
        if v is not None:   # 動画公開日より前には出さない（同日なら動画の後の枠でよい）
            vday = v.astimezone(JST).replace(hour=a.hour, minute=0, second=0, microsecond=0)
            slot = max(slot, vday)
        rows.append((ep, slot, title(f), url, v, st))
        slot += dt.timedelta(days=1)
    o = ["# note 公開スケジュール\n\n",
         f"> 自動生成 {now.astimezone(JST):%Y-%m-%d %H:%M} JST（`python3 _tools/publish/note_publish_schedule.py`）。"
         f"毎日{a.hour}:00 JSTに1本・EP順。EPnの記事は動画EPnの公開日より前に出さない（追いついた後は動画と同日）。\n"
         "> 公開は note 編集画面の「公開に進む → 投稿する」（見出し画像は `_deliverables/note/thumbnails/epNN.png` を設定）。"
         "公開したら note-draft-status.md の status を「公開済み YYYY-MM-DD」に書き換える。\n\n",
         "| 公開予定 | EP | タイトル | 動画公開日 | 下書きstatus | 編集URL |\n|---|---|---|---|---|---|\n"]
    for ep, s, t, url, v, st in rows:
        when = s if isinstance(s, str) else f"{s:%m/%d(%a) %H:%M}"
        vs = "公開済み" if v is None else f"{v.astimezone(JST):%m/%d(%a)}"
        o.append(f"| {when} | EP{ep:02d} | {t[:40]} | {vs} | {st} | {url} |\n")
    open(OUT, "w", encoding="utf-8").write("".join(o))
    print("".join(o[3:]))


if __name__ == "__main__":
    main()
