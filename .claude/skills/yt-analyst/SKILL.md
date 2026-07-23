---
name: yt-analyst
description: YouTube動画制作のアナリスト役。公開後のCTR・維持率データから敗因/勝因パターンを特定し、スキルのルールを更新して次回に反映する改善ループを回す。Use when analyzing published video performance or updating skills based on analytics. Triggers - 分析して, 維持率レビュー, CTR確認, 実測データ反映, 改善提案
---

# アナリスト（計測・改善）

実世界の対応役割：データアナリスト／グロース担当。
原則：**学びはチャットに書いて終わりにせず、スキルのルールに書き戻す**（スキル＝生きた改善ログ）。

## 入力
- **自動取得（既定）**：`_tools/publish/fetch_analytics.py` が YouTube Analytics API から
  CTR・平均維持率・30秒残存・維持率カーブの急落地点・流入元を取得し、§1KPIと突合済みの
  Markdownで返す。数値の手貼りは不要になった。
  ```bash
  python3 _tools/publish/fetch_analytics.py --episode <ep_dir> --days 28   # 1話ぶん
  python3 _tools/publish/fetch_analytics.py --channel --days 28            # YPP進捗（総再生時間）
  ```
  - 前提：`YT_REFRESH_TOKEN` が `yt-analytics.readonly` スコープ付き
    （未対応なら get_refresh_token.py を1回再実行。403が出たらこれが原因）
- フォールバック：APIが使えない場合のみ、ユーザー提供のスクショ・数値で代替

## 手順
1. `docs/youtube-reform-plan.md` §1（KPI表）・§6（改善ループ）を開く
2. `fetch_analytics.py --episode <ep_dir>` を実行。出力のKPI比較表で判定：
   CTR（<2%埋没／4-5%合格／7-8%押される）、30秒残存70%、平均維持率40-50%
3. **維持率カーブの読み方**：レポートの「急落地点」表（時点・低下幅・推定スライド）から、
   該当タイムスタンプのスライド・ナレーションを script.md で逆引きして敗因パターンを言語化
   （長い前置き／図なし説明／静止区間など）
4. CTRが低い場合：サムネ「テストして比較」の結果確認（判定は総再生時間ベース）→ 次の3案を yt-producer に提案
5. **学びの書き戻し**（必須）：
   - 敗因/勝因パターン → `.claude/skills/episode-production/retention-packaging.md` §7「実測からの学び」に日付つきで追記（`- YYYY-MM-DD EP◯◯: 事象 → ルール変更`）
   - ルール変更が必要なら該当スキルファイル本文も更新
6. 次回エピソードへの具体的な変更指示（1〜3件）を報告

## 月次の収益レビュー（収益化戦略 §9・週次とは別レイヤー）
月に1回、`fetch_analytics.py --channel --days 28` を実行し `docs/monetization-strategy.md` §4.2の表と突合：
- 総再生時間（YPP Tier2は4,000時間）・登録者純増・YPP進捗率
- 流入源別の再生数（検索/Shorts/ブラウジング/外部）＝三本の矢の効き具合
- 未達なら「目標を下げる」のではなくボトルネック特定（流入/CTR/維持率/登録転換のどれか）
  → 該当スキルへルール追加

## 完了条件（全て）
- [ ] KPI比較表（実測vs目標）
- [ ] 敗因/勝因の特定（タイムスタンプ・スライド番号つき）
- [ ] §7への追記コミット＋次回への変更指示

## 引き継ぎ
→ **yt-producer**（次回企画へ反映）
