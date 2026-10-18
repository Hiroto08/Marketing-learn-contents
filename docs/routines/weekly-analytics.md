# 週次アナリティクス分析ジョブ（毎週水 9:00 JST ／ cron `0 0 * * 3`）

```
週次アナリティクス分析ジョブ。詳細手順は docs/autonomous-operation.md §3.2。

【基点】git fetch origin && git checkout -B weekly-analytics origin/<基点ブランチ>。python3 -m pip install -q requests。
1. 必ず最初に python3 _tools/publish/weekly_stats.py（公開統計のスナップショット docs/stats/YYYY-MM-DD.json と前週比 docs/weekly-stats.md）。
2. python3 _tools/publish/gen_upload_status.py で直近1〜2週に公開された本編EPを特定。
3. 各EPについて python3 _tools/publish/fetch_analytics.py --episode <ep_dir> --days 28。403 なら「get_refresh_token.py で再認可して YT_REFRESH_TOKEN を更新」と1行添えて Analytics 工程はスキップ（停止扱いにしない）。
4. 取れた場合：CTR・30秒残存・平均維持率・急落地点・流入元を .claude/skills/episode-production/retention-packaging.md §7 に「- YYYY-MM-DD EP◯◯: 事象 → ルール変更」形式で追記。毎月最初の実行時は --channel --days 28 も。CTR<2% または 30秒残存<60% の回には次回への具体的な変更指示を1〜3件。
5. 報告：登録者・総再生の前週比、伸びた本編/Shorts上位3本と伸びなかった新作、気づき1〜3件。
6. 成果物をコミット → git push origin HEAD:<基点ブランチ>（拒否なら作業ブランチへ push -u）。
```
