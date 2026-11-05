# 第2シリーズ 週2回の制作ジョブ（月・木 10:47 JST）

作戦 v0.2 §5.1（最新事例ファースト・予約は3〜5日先まで）を回す。月曜は「水〜土」の4本＋その週の土曜のケースファイル、木曜は「日〜火」の3本を作る。

```
第2シリーズ「売れる仕組みの裏側」の制作ジョブ。手順と型は s2_ura/README.md、方針は docs/post-series-strategy.md §5.1。

0. cd リポジトリ && git checkout <基点ブランチ> && git pull。VOICEVOX が落ちていれば bash _tools/setup_env.sh。
1. 題材の補充：s2_ura/topic-pool.md の候補が10本未満なら、README の情報源から直近3〜6か月の実例を探して足す（各候補に：冒頭の問い・事例・数字・情報源2つ以上のURL・日付）。数字が2つの情報源で一致しないものは「保留」にする。
2. 作る枠を決める：s2_ura/schedule.json を見て、2026-11-29 以降で「今日＋5日」までの日付のうち Short が入っていない日を埋める（1日1本、18時）。土曜にケースファイルが無い週は、月曜のジョブで前の週の公開7日後の再生が最も多い Short の続きを cNN として作る。埋める枠が無ければ 1 だけで終了し、通知しない。
3. 各枠：topic-pool から1本選ぶ（同じ会社・同じ研究を2週以内に使わない）→ uNN（次の番号）で shorts.md（**鮮度：** 時事（YYYY-MM）を書く）と spec.py → gen_stage → verify_shorts PASS → VOICEVOX の読み確認（audio_query の kana）→ 使った候補を topic-pool から「使用済み」に移す。
4. ビルドとアップ：bash _tools/pipeline/run_shorts.sh <dir> --upload（ケースファイルは case.json → build_case_slide.py → verify_episode → run_episode.sh --upload）。動画のアップは1日6本まで（17:00 JST に回復）。超えた分は send_later で翌日17:10に回す。
5. schedule.json に {"id": "uNN", "date": "YYYY-MM-DD"} を足す → python3 _tools/publish/ura_schedule.py --apply --playlist（番号順に昇順でないと拒否される。ずれたら日付を直す）。
6. 成果物をコミット → 基点ブランチと claude/note-articles へ push。
7. 報告（3行以内）：作った回（番号・題名・公開日）、使った事例の日付、残る手作業（公開後に関連動画を設定）。
```
