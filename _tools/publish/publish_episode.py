#!/usr/bin/env python3
"""
publish_episode.py — 既に非公開(private)でアップロード済みのエピソードを
「本編＋その回のShorts」まとめて公開／公開予約する。

設計思想（EP20飛び級公開事故の再発防止 2026-08）:
- 公開は必ずEP番号の昇順。EPn を公開する前に EP1..(n-1) の本編が全て public
  であることを確認し、そうでなければ拒否（--force で上書き可）。
  予約（--at）の場合は「EP(n-1) が public か、EPn より前の時刻で公開予約済み」なら可。
- 本編とその回の Shorts は必ず同時に同じ状態へ（public / 同じ publishAt）。

回の判定は動画タグ mlab-epNN / mlab-epNN-sM（yt_index.py。公開タイトルに「第N回」は入れない）。

使い方:
  python3 _tools/publish/publish_episode.py --episode 03_practical/ep10_copywriting-5laws
  python3 _tools/publish/publish_episode.py --episode <ep_dir> --at 2026-10-24T18:00:00+09:00
  python3 _tools/publish/publish_episode.py --episode <ep_dir> --dry-run
  # 非公開UP済みの回を EP順に毎週1本ずつ一括予約（既定：毎週土曜18:00 JST）
  python3 _tools/publish/publish_episode.py --schedule-all [--start 2026-10-24T18:00:00+09:00] [--every-days 7] [--dry-run]
    --start 省略時：既存の予約の最後の回の次の枠から延長（予約済みの回は動かさない＝冪等。毎週流してよい）
    --start 指定時：未公開の回を全てその日時から組み直す
必要スコープ: https://www.googleapis.com/auth/youtube（videos.update）
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yt_index import API, episode_index, privacy, public_max_ep, token  # noqa: E402

JST = dt.timezone(dt.timedelta(hours=9))


def when(v):
    """private かつ publishAt があればその日時（aware datetime）"""
    at = v["status"].get("publishAt")
    if privacy(v) == "private" and at:
        return dt.datetime.fromisoformat(at.replace("Z", "+00:00"))
    return None


def parse(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def next_saturday_18(after):
    t = after.astimezone(JST).replace(hour=18, minute=0, second=0, microsecond=0)
    t += dt.timedelta(days=(5 - t.weekday()) % 7)
    return t if t > after + dt.timedelta(hours=1) else t + dt.timedelta(days=7)


def expected_shorts(ep):
    d = next((d for d in glob.glob(f"0*/ep{ep:02d}_*") if os.path.isdir(d)), None)
    if not d or not os.path.exists(f"{d}/shorts.md"):
        return 0
    return len(re.findall(r"^## Short \d+", open(f"{d}/shorts.md", encoding="utf-8").read(), re.M))


def set_privacy(tok, v, at=None, dry=False):
    vid, st, title = v["id"], v["status"], v["snippet"]["title"][:34]
    status = {"selfDeclaredMadeForKids": st.get("selfDeclaredMadeForKids", False),
              "license": st.get("license", "youtube"), "embeddable": st.get("embeddable", True),
              "publicStatsViewable": st.get("publicStatsViewable", True)}
    if at:
        status["privacyStatus"] = "private"
        status["publishAt"] = at
    else:
        status["privacyStatus"] = "public"
    if dry:
        return f"[dry] {vid} [{title}] -> {'予約 ' + at if at else 'public'}"
    req = urllib.request.Request(f"{API}/videos?part=status", data=json.dumps({"id": vid, "status": status}).encode(),
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"},
                                 method="PUT")
    try:
        s = json.load(urllib.request.urlopen(req, timeout=30))["status"]
        return f"{vid} [{title}] -> {s['privacyStatus']}" + (f" @ {s.get('publishAt')}" if s.get("publishAt") else "")
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:150]
        if e.code == 403 and "quota" in body.lower():
            raise SystemExit(f"quotaExceeded: 翌日16:00 JST以降に同じコマンドで再開（{vid} 未処理）")
        return f"{vid} [{title}]: FAIL {e.code} {body}"


def apply(tok, s, ep, at, dry):
    """本編＋Shortsを同じ状態へ。既に同じ状態の動画は飛ばす。本編が失敗したらShortsは触らず False"""
    shorts = [s["shorts"][n] for n in sorted(s["shorts"])]
    print(f"EP{ep:02d} を{'予約公開(' + at + ')' if at else '公開'}（本編＋Shorts{len(shorts)}本 同時）")
    for kind, vid in [("本編 ", s["main"])] + [("Short", x) for x in shorts]:
        v = s["items"][vid]
        if (at and when(v) and when(v) == parse(at)) or (not at and privacy(v) == "public"):
            print(f"  {kind}: {vid} 変更なし")
            continue
        r = set_privacy(tok, v, at, dry)
        print(f"  {kind}:", r)
        if kind.startswith("本編") and ": FAIL" in r:
            print("  ! 本編の状態変更に失敗 → Shorts は変更しない（単独公開を防ぐ）")
            return False
    if not shorts:
        print("  ! この回の Shorts が見つからない（未UP）。本編のみ処理した。")
    return True


def schedule_all(tok, idx, start, every, dry):
    pub = public_max_ep(idx)
    now = dt.datetime.now(dt.timezone.utc)
    prev_t, plan = None, []
    ep = pub + 1
    while ep in idx and idx[ep]["main"]:
        s = idx[ep]
        exp = expected_shorts(ep)
        if len(s["shorts"]) < exp:
            print(f"EP{ep:02d}: Shorts が {len(s['shorts'])}/{exp} 本しか無い → 本編と同時公開できないので、ここで予約の連鎖を止める")
            break
        cur = when(s["items"][s["main"]])
        if start is None and cur and (prev_t is None or cur > prev_t):
            t = cur                                   # 既存予約は維持（延長モード）
        elif start is not None:
            t = start + dt.timedelta(days=every * len(plan))
        else:
            t = (prev_t + dt.timedelta(days=every)) if prev_t else next_saturday_18(now)
        plan.append((ep, t))
        prev_t = t
        ep += 1
    if not plan:
        print(f"予約対象なし（public最大=EP{pub:02d}、EP{pub + 1:02d} は未UP）")
        return
    print("予約計画（EP順・本編とShortsは同時刻）:")
    for ep, t in plan:
        print(f"  EP{ep:02d}  {t.astimezone(JST):%Y-%m-%d (%a) %H:%M JST}")
    timed = []
    for ep, t in plan:
        if not apply(tok, idx[ep], ep, iso(t), dry):
            timed.append((ep, t))
    for ep, t in timed:
        # 一度でも公開された動画は publishAt を受け付けない（例：EP20 は8/8に誤公開→非公開に戻した）。
        # その枠の時刻に「publish_episode.py --episode <dir>（即時公開）」を走らせる単発スケジュールが必要。
        print(f"TIMED EP{ep:02d} {iso(t)}  ← 予約不可。この時刻に publish_episode.py --episode で即時公開する単発実行を登録すること")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--episode", help="エピソードディレクトリ")
    g.add_argument("--schedule-all", action="store_true", help="非公開UP済みの回をEP順に一括予約")
    ap.add_argument("--at", help="RFC3339の公開予約日時（例 2026-10-24T18:00:00+09:00）。省略で即時public")
    ap.add_argument("--start", help="--schedule-all の最初の枠（RFC3339）。省略で既存予約から延長")
    ap.add_argument("--every-days", type=int, default=7)
    ap.add_argument("--force", action="store_true", help="EP順ガードを無視して公開する")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    tok = token()
    idx = episode_index(tok)
    if a.schedule_all:
        schedule_all(tok, idx, parse(a.start) if a.start else None, a.every_days, a.dry_run)
        return
    ep = int(re.search(r"ep(\d+)", os.path.basename(a.episode.rstrip("/"))).group(1))
    s = idx.get(ep)
    if not s or not s["main"]:
        sys.exit(f"EP{ep:02d} の本編がYouTube上に見つからない（未アップロード？）: {a.episode}")
    mx = public_max_ep(idx)
    if ep > mx + 1 and not a.force:
        prev = idx.get(ep - 1, {}).get("main")
        pt = when(idx[ep - 1]["items"][prev]) if prev else None
        ok = a.at and pt and pt < parse(a.at) and all(
            idx.get(e, {}).get("main") and (privacy(idx[e]["items"][idx[e]["main"]]) == "public"
                                            or when(idx[e]["items"][idx[e]["main"]]))
            for e in range(mx + 1, ep))
        if not ok:
            sys.exit(f"公開順序ガード: EP{ep:02d} は公開できません。現在 public 済み最大は EP{mx:02d}。"
                     f"即時公開は EP{mx + 1:02d} のみ、予約は直前の回が全て予約済みかつそれより後の時刻のみ可（--force で上書き可）。")
    apply(tok, s, ep, a.at, a.dry_run)


if __name__ == "__main__":
    main()
