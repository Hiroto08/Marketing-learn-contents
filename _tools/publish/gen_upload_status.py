#!/usr/bin/env python3
"""
gen_upload_status.py — docs/upload-status.md を YouTube の実体から再生成する。

回の判定はタグ mlab-epNN / mlab-epNN-sM（yt_index.py）。タグの無い古い動画のみ
ローカル manifest とタイトルの「第N回」で補完する。ブランチごとに manifest の有無が
食い違っても、YouTube 実体が真実源になる。
"""
import datetime
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yt_index import api, episode_index, privacy, public_max_ep, token  # noqa: E402


def state(v):
    p = privacy(v)
    at = v["status"].get("publishAt")
    return f"予約 {at[:16].replace('T', ' ')}" if (p == "private" and at) else p


def main():
    tok = token()
    ch = api(tok, "channels", {"part": "snippet", "mine": "true"})["items"][0]["snippet"]["title"]
    idx = episode_index(tok)
    dirs = {int(re.search(r"ep(\d+)", os.path.basename(d))[1]): d
            for d in glob.glob("0*/ep*") if os.path.isdir(d)}
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    o = [f"# アップロード状況（{ch}）\n\n",
         f"> 自動生成：{now} ／ ソース＝YouTube実体（タグ mlab-epNN で回を判定）＋ローカル manifest で補完\n",
         "> 生成：`python3 _tools/publish/gen_upload_status.py`。他セッション・ルーティンはこのファイルで到達点を確認する。\n\n",
         "凡例：public=公開済 / private=非公開 / 予約=公開予約済 / 未UP=未アップロード / —=対象物なし\n\n",
         "| EP | ディレクトリ | 本編 | 本編状態 | Shorts | Shorts状態 |\n|----|----|----|----|----|----|\n"]
    counts = {}
    unup = []
    for ep in sorted(set(dirs) | set(idx)):
        d = dirs.get(ep, "")
        s = idx.get(ep, {"main": None, "shorts": {}, "items": {}})
        mv = s["main"]
        ms = state(s["items"][mv]) if mv else "未UP"
        if not mv:
            unup.append(f"EP{ep:02d}")
        sh = [s["shorts"][n] for n in sorted(s["shorts"])]
        has_md = bool(d) and os.path.exists(f"{d}/shorts.md")
        svs = " ".join(f"`{x}`" for x in sh) if sh else ("未UP" if has_md else "—")
        sps = "／".join(sorted({state(s["items"][x]) for x in sh})) if sh else ("未UP" if has_md else "—")
        for v in s["items"].values():
            counts[privacy(v)] = counts.get(privacy(v), 0) + 1
        o.append(f"| EP{ep:02d} | `{os.path.basename(d)}` | {('`' + mv + '`') if mv else '—'} | {ms} | {svs} | {sps} |\n")
    o.append(f"\n**集計**：追跡 {sum(counts.values())}本中 public={counts.get('public', 0)} / "
             f"private={counts.get('private', 0)} / unlisted={counts.get('unlisted', 0)}\n")
    n = public_max_ep(idx)
    o.append("\n## 公開順序（絶対則：飛び級厳禁）\n")
    o.append(f"- 現在 public 済みの最大EP＝**EP{n:02d}**／次に公開してよいのは**EP{n + 1:02d}のみ**"
             f"（`python3 _tools/publish/publish_episode.py --episode <dir>` で本編＋Shortsを同時公開）。\n")
    o.append("- 本編は必ずEP番号の昇順で公開。先のEPが非公開UP済みでも飛ばさない（docs/autonomous-operation.md §3.1）。\n")
    cal = [(ep, s["items"][s["main"]]["status"]["publishAt"]) for ep, s in sorted(idx.items())
           if s["main"] and privacy(s["items"][s["main"]]) == "private" and s["items"][s["main"]]["status"].get("publishAt")]
    o.append("\n## 公開予約カレンダー（本編＋同回Shortsが同時刻）\n")
    if cal:
        jst = datetime.timezone(datetime.timedelta(hours=9))
        for ep, at in cal:
            t = datetime.datetime.fromisoformat(at.replace("Z", "+00:00")).astimezone(jst)
            o.append(f"- EP{ep:02d}：{t:%Y-%m-%d (%a) %H:%M} JST\n")
    else:
        o.append("- なし\n")
    o.append("- 延長・組み直し：`python3 _tools/publish/publish_episode.py --schedule-all [--start <RFC3339>]`"
             "（予約不可の回は TIMED と表示 → その時刻に即時公開する単発スケジュールで対応）\n")
    o.append("\n## 残作業\n"
             "- 次に公開：上記「次に公開してよいEP」を public 化（or `publish_episode.py --schedule-all` で水・土18:00 JSTの枠に予約）\n"
             "- 各Short：Studioで「関連動画」に本編を設定（API不可・docs/shorts-related-video-checklist.md）\n"
             f"- 未UP（本編）：{'／'.join(unup) if unup else 'なし'}\n")
    open("docs/upload-status.md", "w", encoding="utf-8").write("".join(o))
    print(f"regenerated. tracked={sum(counts.values())} public={counts.get('public', 0)} "
          f"private={counts.get('private', 0)} next=EP{n + 1:02d}")


if __name__ == "__main__":
    main()
