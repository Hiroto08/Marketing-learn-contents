#!/usr/bin/env python3
"""schedule_kit_broadcasts.py — メール草稿（make_broadcast.py の出力）を Kit に「予約ブロードキャスト」として登録する。

送信時刻＝その回の YouTube 本編の公開予約時刻（publishAt）。動画の公開と同時にメールが届く。
- 自動モード（引数なし）：YouTube 上で公開予約済み（private＋publishAt が未来）の本編すべてについて、
  _deliverables/broadcast/ep<NN>_*.md を Kit に予約登録する。
- 手動モード：--episode <dir> --send-at <RFC3339>（publishAt を使えない回＝TIMED 回など）
- 冪等：Kit 上の既存ブロードキャストを description のマーカー「mlab-epNN」で照合し、登録済みの回は飛ばす
  （送信時刻が動画とずれていれば WARN を出す。直すのは Kit 画面で）。
- 安全：送信時刻が現在＋15分より前の回は登録しない。--dry-run で中身（件名・時刻・宛先）だけ確認できる。

必要な環境変数（Secrets）:
  KIT_API_KEY      … Kit → Settings → Developer の v4 API キー（値は表示・ログ出力しない）
  KIT_SEGMENT_ID / KIT_TAG_ID（任意）… 宛先を絞る場合。未設定なら全購読者
  YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN … 自動モードで publishAt を読むため

  python3 _tools/repurpose/schedule_kit_broadcasts.py --dry-run
  python3 _tools/repurpose/schedule_kit_broadcasts.py
  python3 _tools/repurpose/schedule_kit_broadcasts.py --episode 05_advanced/ep20_growth-hack --send-at 2026-10-31T18:00:00+09:00
"""
import argparse
import datetime as dt
import glob
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import series as S  # noqa: E402  シリーズ固有の値（series.json）

KIT = "https://api.kit.com/v4"
MARK = S.PREFIX + "-ep{:02d}"


def kit(method, path, body=None):
    key = os.environ.get("KIT_API_KEY")
    if not key:
        raise SystemExit("KIT_API_KEY が未設定（Kit → Settings → Developer で v4 API キーを作り、環境Secretに登録）")
    req = urllib.request.Request(f"{KIT}/{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-Kit-Api-Key": key, "Content-Type": "application/json",
                                          "Accept": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Kit API {method} {path}: {e.code} {e.read().decode()[:300]}")


def existing():
    """{ep: broadcast} — description にマーカーを持つ既存ブロードキャスト"""
    out, after = {}, None
    while True:
        q = "broadcasts?per_page=500&slim=true" + (f"&after={after}" if after else "")
        r = kit("GET", q)
        for b in r.get("broadcasts", []):
            m = S.MARK_RE.search(b.get("description") or "")
            if m and b.get("status") != "aborted":
                out[int(m[1])] = b
        pg = r.get("pagination", {})
        if not pg.get("has_next_page"):
            return out
        after = pg["end_cursor"]


def draft(ep):
    p = sorted(glob.glob(f"_deliverables/broadcast/ep{ep:02d}_*.md"))
    if not p:
        return None
    t = open(p[0], encoding="utf-8").read()
    subject = re.search(r"^件名:\s*(.+)$", t, re.M)[1].strip()
    body = t.split("\n---\n", 1)[1].strip()
    paras = [x.strip() for x in re.split(r"\n\s*\n", body) if x.strip()]

    def para(x):
        x = html.escape(x).replace("\n", "<br>")
        x = re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', x)
        return f"<p>{x}</p>"
    preview = next((x for x in paras[2:] if not x.startswith(("🎬", "続きは"))), paras[0])
    return {"path": p[0], "subject": subject, "content": "".join(para(x) for x in paras),
            "preview_text": re.sub(r"\s+", " ", preview)[:90]}


def youtube_schedule():
    """{ep: publishAt datetime} — 公開予約済みの本編"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "publish"))
    from yt_index import episode_index, token
    out = {}
    for ep, s in episode_index(token()).items():
        v = s["items"].get(s["main"]) if s["main"] else None
        if v and v["status"]["privacyStatus"] == "private" and v["status"].get("publishAt"):
            out[ep] = dt.datetime.fromisoformat(v["status"]["publishAt"].replace("Z", "+00:00"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode")
    ap.add_argument("--send-at", help="RFC3339（--episode と併用）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.episode:
        if not a.send_at:
            sys.exit("--episode には --send-at が必要")
        ep = int(re.search(r"ep(\d+)", os.path.basename(a.episode.rstrip("/")))[1])
        plan = {ep: dt.datetime.fromisoformat(a.send_at.replace("Z", "+00:00"))}
    else:
        plan = youtube_schedule()
    if not plan:
        print("公開予約済みの本編なし → 登録対象なし")
        return
    have = existing() if os.environ.get("KIT_API_KEY") else {}
    if not os.environ.get("KIT_API_KEY"):
        print("（KIT_API_KEY 未設定：既存照合なしの dry-run）")
        a.dry_run = True
    seg, tag = os.environ.get("KIT_SEGMENT_ID"), os.environ.get("KIT_TAG_ID")
    filt = ([{"all": [{"type": "segment", "ids": [int(seg)]}], "any": None, "none": None}] if seg else
            [{"all": [{"type": "tag", "ids": [int(tag)]}], "any": None, "none": None}] if tag else None)
    now = dt.datetime.now(dt.timezone.utc)
    jst = dt.timezone(dt.timedelta(hours=9))
    for ep in sorted(plan):
        at = plan[ep]
        label = f"EP{ep:02d} {at.astimezone(jst):%m/%d(%a) %H:%M} JST"
        if ep in have:
            b = have[ep]
            sa = b.get("send_at")
            same = sa and dt.datetime.fromisoformat(sa.replace("Z", "+00:00")) == at
            print(f"{label}: 登録済み（id={b['id']} status={b.get('status')}）" +
                  ("" if same or b.get("status") == "completed" else f"  WARN 送信時刻 {sa} が動画と不一致"))
            continue
        if at < now + dt.timedelta(minutes=15):
            print(f"{label}: 送信時刻が近すぎる/過去 → 登録しない")
            continue
        d = draft(ep)
        if not d:
            print(f"{label}: メール草稿なし（make_broadcast.py --episode <dir> で生成）→ スキップ")
            continue
        body = {"subject": d["subject"], "preview_text": d["preview_text"], "content": d["content"],
                "description": f"{MARK.format(ep)} 自動予約（YouTube公開と同時刻）",
                "public": False, "published_at": at.isoformat(), "send_at": at.isoformat()}
        if filt:
            body["subscriber_filter"] = filt
        if a.dry_run:
            print(f"[dry] {label}: 「{d['subject']}」 宛先={'segment ' + seg if seg else 'tag ' + tag if tag else '全購読者'}"
                  f"  preview={d['preview_text'][:40]}…")
            continue
        r = kit("POST", "broadcasts", body)["broadcast"]
        print(f"{label}: 予約登録 id={r['id']} status={r.get('status')} send_at={r.get('send_at')}「{d['subject']}」")


if __name__ == "__main__":
    main()
