#!/usr/bin/env python3
"""
upload_captions.py — 台本のナレーションから日本語字幕(SRT)を作り、YouTubeにアップロードする。

本編 : script.md の各「### スライド N：…（M:SS〜M:SS）」見出し（postbuildで実測値に更新済み）と
       「**ナレーション：**」本文から、スライド内の文を文字数比で時間配分して字幕化。
Shorts: shorts.md の「### S1（…・0.0〜3.5秒）」と本文から同様に生成（--shorts 指定時のみ）。

目的: 自動字幕より正確な字幕で検索インデックス・ミュート視聴・用語の正確さを確保する。
クォータ: captions.insert は1本400単位（1日10,000）。本編を優先し、Shortsは任意。
既に（自動字幕以外の）字幕がある動画はスキップする（videos.contentDetails.caption で判定）。

使い方:
  python3 _tools/publish/upload_captions.py --episode 03_practical/ep09_cpa-ltv            # 本編のみ
  python3 _tools/publish/upload_captions.py --episode <dir> --shorts                      # Shortsも
  python3 _tools/publish/upload_captions.py --all --dry-run --out /tmp/srt               # 全話SRTを書き出すだけ
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yt_index import episode_index, token  # noqa: E402

MAX_CHARS = 28   # 1キューの最大文字数（スマホで2行以内）
LEAD = 0.15      # 発話開始の微小オフセット（秒）


def _t(s: str) -> float:
    s = s.strip()
    if ":" in s:
        m, sec = s.split(":")
        return int(m) * 60 + float(sec)
    return float(s)


def _chunks(sentence: str):
    """1文を MAX_CHARS 以下に、読点で区切って分割"""
    if len(sentence) <= MAX_CHARS:
        return [sentence]
    parts, cur = [], ""
    for piece in re.split(r"(?<=、)", sentence):
        if cur and len(cur) + len(piece) > MAX_CHARS:
            parts.append(cur)
            cur = piece
        else:
            cur += piece
    if cur:
        parts.append(cur)
    out = []
    for p in parts:   # 読点が無く長すぎる塊は機械的に割る
        while len(p) > MAX_CHARS + 6:
            out.append(p[:MAX_CHARS])
            p = p[MAX_CHARS:]
        out.append(p)
    return out


def _cues_for_span(text: str, start: float, end: float):
    text = text.replace("\n", "")
    sents = [s for s in re.split(r"(?<=[。！？])", text) if s.strip()]
    pieces = [c for s in sents for c in _chunks(s.strip())]
    total = sum(len(p) for p in pieces) or 1
    span = max(end - start - LEAD, 0.5)
    cues, t = [], start + LEAD
    for p in pieces:
        dur = span * len(p) / total
        cues.append((t, t + dur, p))
        t += dur
    return cues


def main_cues(ep_dir: str):
    md = open(f"{ep_dir}/script.md", encoding="utf-8").read()
    cues = []
    for m in re.finditer(r"^###[^\n]*スライド\s*\d+[^\n]*（(\d+:\d+(?:\.\d+)?)〜(\d+:\d+(?:\.\d+)?)）\s*\n(.*?)(?=^### |\Z)",
                         md, re.S | re.M):
        start, end, body = _t(m[1]), _t(m[2]), m[3]
        n = re.search(r"\*\*ナレーション：\*\*\s*\n「(.*?)」\s*(?:\n|$)", body, re.S)
        if n:
            cues += _cues_for_span(n[1], start, end)
    return cues


def short_cues(ep_dir: str):
    md = open(f"{ep_dir}/shorts.md", encoding="utf-8").read()
    out = {}
    for sm in re.finditer(r"^## Short (\d+)[：:](.*?)(?=^## Short |\Z)", md, re.S | re.M):
        n, block, cues = int(sm[1]), sm[2], []
        for m in re.finditer(r"^### S\d+（[^）]*?([\d.]+)〜([\d.]+)秒）\s*\n(.*?)(?=^### |\Z)", block, re.S | re.M):
            nar = re.search(r"\*\*ナレーション：\*\*\s*\n「(.*?)」", m[3], re.S)
            if nar:
                cues += _cues_for_span(nar[1], float(m[1]), float(m[2]))
        if cues:
            out[n] = cues
    return out


def srt(cues) -> str:
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    return "".join(f"{i}\n{ts(a)} --> {ts(b)}\n{t}\n\n" for i, (a, b, t) in enumerate(cues, 1))


def upload(tok: str, video_id: str, body: str) -> str:
    import requests
    meta = {"snippet": {"videoId": video_id, "language": "ja", "name": "日本語", "isDraft": False}}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/captions",
                      params={"part": "snippet", "uploadType": "multipart"},
                      headers={"Authorization": f"Bearer {tok}"},
                      files={"metadata": (None, json.dumps(meta), "application/json; charset=UTF-8"),
                             "file": ("captions.srt", body.encode("utf-8"), "application/octet-stream")},
                      timeout=120)
    if r.status_code == 200:
        return "OK"
    if r.status_code == 403 and "quota" in r.text.lower():
        raise SystemExit(f"quotaExceeded: 翌日16:00 JST（PT0時）以降に同じコマンドで再開（{video_id} 未処理）")
    if r.status_code == 403 and "insufficient" in r.text.lower():
        raise SystemExit("権限不足（youtube.force-ssl スコープが無い）：手元PCで get_refresh_token.py を再実行し"
                         " Secret YT_REFRESH_TOKEN を更新すると字幕をアップロードできる（アナリティクスも同時に有効化）")
    return f"FAIL {r.status_code} {r.text[:200]}"


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--episode", help="エピソードディレクトリ")
    g.add_argument("--all", action="store_true", help="全話（EP番号順）")
    ap.add_argument("--shorts", action="store_true", help="Shortsにも字幕を付ける（1本400単位）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", help="SRTを書き出すディレクトリ（dry-run時の確認用）")
    ap.add_argument("--limit", type=int, default=0, help="アップロード本数の上限（クォータ配分用）")
    a = ap.parse_args()
    dirs = sorted((d for d in glob.glob("0*/ep*") if os.path.isdir(d)),
                  key=lambda d: int(re.search(r"ep(\d+)", os.path.basename(d))[1]))
    if a.episode:
        dirs = [a.episode.rstrip("/")]
    tok = token()
    idx = episode_index(tok)
    done = 0
    for d in dirs:
        ep = int(re.search(r"ep(\d+)", os.path.basename(d))[1])
        s = idx.get(ep, {"main": None, "shorts": {}, "items": {}})
        jobs = []
        if s["main"] and os.path.exists(f"{d}/script.md"):
            jobs.append((s["main"], main_cues(d), f"ep{ep:02d}_main"))
        if a.shorts and os.path.exists(f"{d}/shorts.md"):
            sc = short_cues(d)
            jobs += [(s["shorts"][n], sc[n], f"ep{ep:02d}_short{n}") for n in sorted(sc) if n in s["shorts"]]
        for vid, cues, name in jobs:
            v = s["items"][vid]
            if not cues:
                print(f"  {name} {vid}: ナレーション/時刻を抽出できない → スキップ")
                continue
            body = srt(cues)
            if a.out:
                os.makedirs(a.out, exist_ok=True)
                open(f"{a.out}/{name}.srt", "w", encoding="utf-8").write(body)
            if v["contentDetails"].get("caption") == "true":
                print(f"  {name} {vid}: 字幕あり → スキップ")
                continue
            if a.dry_run:
                print(f"  [dry] {name} {vid}: {len(cues)}キュー 末尾{cues[-1][1]:.1f}s")
                continue
            if a.limit and done >= a.limit:
                print(f"  --limit {a.limit} 到達。残りは次回")
                return
            print(f"  {name} {vid}: {upload(tok, vid, body)}")
            done += 1


if __name__ == "__main__":
    main()
