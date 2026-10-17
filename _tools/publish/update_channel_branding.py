#!/usr/bin/env python3
"""channels.update brandingSettings: 既存値を取得→description/keywords/country だけ差し替えて送り返す（他は保持）"""
import json, sys, urllib.request
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from yt_index import API, api, token

DESC = """マーケティングを「第1回から順に」体系的に学べる、無料のマーケティング入門講座チャンネルです。

各回8〜9分。実在企業の実話1本を軸に、「なぜ売れたのか／なぜ売れなかったのか」を図解で解説します。
STP分析・ペルソナ・カスタマージャーニー・価格設定・4P/4C・USP・CPA/LTV・コピーライティング・SNS運用・ABテスト・ブランディング・CRM・グロースハック、そしてChatGPTなど生成AIのマーケティング活用まで、全24話で一通り身につきます。

▼はじめての方へ
再生リスト「マーケティング入門講座 全24話」を第1回から順に見るのがおすすめです。1分で要点だけ知りたい方は「1分でわかるマーケティング｜Shorts まとめ」へ。

▼こんな人向け
・マーケ担当になったばかりの方／一人で集客を任された方
・個人事業主・副業・スモールビジネスで売上を伸ばしたい方
・AIをマーケティングに使いたいが、何から始めればいいか分からない方

▼無料特典：マーケの型 全20話まとめ＆実践チートシート（PDF）
https://witty-composer-9473.kit.com/ac0f4ce77b

毎週1話ずつ新しい回を公開中。チャンネル登録で続きを見逃さずに受け取れます。
※ナレーションはAI音声合成（VOICEVOX:玄野武宏）を使用しています。"""

KW = ('マーケティング "マーケティング入門" "マーケティング 初心者" "マーケティング講座" "Webマーケティング" '
      'STP分析 ペルソナ "カスタマージャーニー" "価格設定" 4P USP LTV CPA "コピーライティング" "SNS運用" '
      'ABテスト ブランディング CRM "グロースハック" "AIマーケティング" ChatGPT "生成AI" 集客 "売れる仕組み" ビジネス')

tok = token()
dry = "--dry-run" in sys.argv
ch = api(tok, "channels", {"part": "brandingSettings", "mine": "true"})["items"][0]
bs = ch["brandingSettings"]
print("BEFORE:", json.dumps(bs, ensure_ascii=False)[:600])
bs.setdefault("channel", {})
bs["channel"].update({"description": DESC, "keywords": KW, "country": "JP", "defaultLanguage": "ja"})
assert len(DESC) <= 1000 and len(KW) <= 500, (len(DESC), len(KW))
if dry:
    sys.exit(f"[dry] desc={len(DESC)} kw={len(KW)}")
req = urllib.request.Request(f"{API}/channels?part=brandingSettings", method="PUT",
                             data=json.dumps({"id": ch["id"], "brandingSettings": bs}).encode(),
                             headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
r = json.load(urllib.request.urlopen(req, timeout=30))
print("AFTER:", json.dumps(r["brandingSettings"]["channel"], ensure_ascii=False)[:300])
