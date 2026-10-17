#!/usr/bin/env python3
"""
sync_playlists.py — シリーズ再生リスト（全話・章別・Shorts）を YouTube 実体と同期する。

- 再生リストはタイトルで照合し、無ければ作成（public）。
- 回の判定は yt_index（タグ mlab-epNN / mlab-epNN-sM）。
- 既に入っている動画は飛ばし、足りない動画だけを EP順の正しい位置（snippet.position）へ挿入。
  → 何度実行しても安全（冪等）。新しい回をアップした後に1回流せば再生リストに並ぶ。
- 非公開動画も追加される（視聴者には公開された時点から表示される）。

クォータ: 一覧 1単位/ページ、作成・挿入 50単位/件。

使い方:
  python3 _tools/publish/sync_playlists.py            # 同期
  python3 _tools/publish/sync_playlists.py --dry-run  # 追加予定だけ表示
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yt_index import API, api, episode_index, token  # noqa: E402

SUFFIX = ("\n\n▼無料特典：マーケの型 全20話まとめ＆実践チートシート（PDF）\n"
          "https://witty-composer-9473.kit.com/ac0f4ce77b\n\n"
          "※ナレーションはAI音声合成（VOICEVOX:玄野武宏）を使用しています。")

PLAYLISTS = [
    ("マーケティング入門講座 全24話｜売れる仕組みを第1回から順に学ぶ",
     "マーケティングを基礎から実践・AI活用まで、全24話で体系的に学べる講座です。各回8〜9分、実在企業の実話1本で「売れる仕組み」を解説します。"
     "第1回から順に再生すると、STP分析・ペルソナ・価格設定・4P/4C・USP・CPA/LTV・コピーライティング・ABテスト・AI活用・ブランディング・CRMまで一通り身につきます。",
     range(1, 25), "main"),
    ("入門編｜マーケティングとは・STP分析・ペルソナ・ベネフィット（第1〜4回）",
     "マーケティングの入口。「良い商品なのに売れない」理由、売る相手の決め方（STP分析）、ペルソナの作り方と落とし穴、特徴ではなくベネフィットで伝える方法を、実話で学びます。",
     range(1, 5), "main"),
    ("中級編｜カスタマージャーニー・価格設定の心理学・4Pと4C・USP（第5〜8回）",
     "買うまでの道筋（カスタマージャーニー）、安売りせずに選ばれる価格設定の心理学、4Pと4Cのマーケティングミックス、競合と差別化するUSPの作り方を学びます。",
     range(5, 9), "main"),
    ("実践編｜CPAとLTV・コピーライティング・SNS運用・ABテスト（第9〜12回）",
     "広告費を赤字にしないCPAとLTVの考え方、1行で売上が変わるコピーライティング、フォロワー数より大切なSNS運用、正しいABテストのやり方を実践レベルで学びます。",
     range(9, 13), "main"),
    ("AI活用編｜AI市場調査・AI記事作成・ChatGPTで顧客分析・AIチャットボット（第13〜16回）",
     "生成AIをマーケティングに使う実践編。AIで市場調査を速くするプロンプト、AIで量産しても没個性にしない記事作成、ChatGPTでアンケートを分析する方法、嫌われないチャットボット設計を学びます。",
     range(13, 17), "main"),
    ("上級編｜ブランディング・CRM・マーケ組織・グロースハック（第17〜20回）",
     "広告をやめても売れるブランディング、新規より既存客で利益を伸ばすCRM、マーケが機能する組織の作り方、広告費ゼロで伸びるグロースハックを学びます。",
     range(17, 21), "main"),
    ("事例編｜ヒット商品・V字回復・失敗事例・これからのマーケター（第21〜24回）",
     "身近なヒット商品の仕掛け、倒産寸前からのV字回復、良い商品なのに売れなかった失敗事例、AI時代に生き残るマーケターの条件を、実在企業の事例で学びます。",
     range(21, 25), "main"),
    ("1分でわかるマーケティング｜Shorts まとめ",
     "マーケティングの「なるほど」を1本1分以内で。実在企業の事例と数字で、売れる仕組みの核心だけを切り出したShortsです。気になった回は本編（各8〜9分）でじっくりどうぞ。",
     range(1, 25), "shorts"),
]


def post(tok, path, body):
    req = urllib.request.Request(f"{API}/{path}", data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def items(tok, pid):
    out, page = [], None
    while True:
        q = {"part": "contentDetails", "playlistId": pid, "maxResults": "50"}
        if page:
            q["pageToken"] = page
        try:
            r = api(tok, "playlistItems", q)
        except urllib.error.HTTPError:   # 作成直後は404になることがある
            return out
        out += [i["contentDetails"]["videoId"] for i in r["items"]]
        page = r.get("nextPageToken")
        if not page:
            return list(dict.fromkeys(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    tok = token()
    idx = episode_index(tok)
    existing = {p["snippet"]["title"]: p["id"]
                for p in api(tok, "playlists", {"part": "snippet", "mine": "true", "maxResults": "50"})["items"]}
    for title, desc, eps, kind in PLAYLISTS:
        want = []
        for ep in eps:
            s = idx.get(ep)
            if not s:
                continue
            if kind == "main" and s["main"]:
                want.append(s["main"])
            if kind == "shorts":
                want += [s["shorts"][n] for n in sorted(s["shorts"])]
        pid = existing.get(title)
        if not pid:
            if a.dry_run:
                print(f"[dry] 作成予定 {title[:40]}（{len(want)}本）")
                continue
            pid = post(tok, "playlists?part=snippet,status",
                       {"snippet": {"title": title, "description": desc + SUFFIX, "defaultLanguage": "ja"},
                        "status": {"privacyStatus": "public"}})["id"]
        have = items(tok, pid)
        added = 0
        for v in want:
            if v in have:
                continue
            # EP順で直前にあるべき動画の、現在の並びの直後に挿入
            prev = [w for w in want[:want.index(v)] if w in have]
            pos = have.index(prev[-1]) + 1 if prev else 0
            if a.dry_run:
                print(f"[dry] {title[:24]}… に {v} を位置{pos}へ")
                have.insert(pos, v)
                continue
            for attempt in range(3):
                try:
                    post(tok, "playlistItems?part=snippet",
                         {"snippet": {"playlistId": pid, "position": pos,
                                      "resourceId": {"kind": "youtube#video", "videoId": v}}})
                    have.insert(pos, v)
                    added += 1
                    break
                except urllib.error.HTTPError as e:
                    msg = e.read().decode()[:160]
                    if e.code == 403:
                        sys.exit(f"403で停止（quota/権限）: {msg}\n翌日16:00 JST以降に再実行すれば続きから同期する")
                    if e.code == 409 and attempt < 2:   # 一時的な "operation aborted"
                        time.sleep(3)
                        continue
                    print(f"  FAIL {v} {e.code} {msg}")
                    break
        print(f"{pid} +{added}（{len([w for w in want if w in have])}/{len(want)}） {title[:40]}")


if __name__ == "__main__":
    main()
