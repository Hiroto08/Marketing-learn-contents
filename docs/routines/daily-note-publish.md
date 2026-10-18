# note 毎日公開ジョブ（毎日 19:55 JST ／ cron `55 10 * * *`）

公開時刻の5分前に起動する（記事の予定枠は series.json の `schedule.note_hour_jst`、既定 20:00）。

```
note 毎日公開ジョブ。_deliverables/note/note-publish-schedule.md の予定どおり、今日（JST）までが予定日の未公開記事を公開する。

1. git fetch origin && git checkout -B note-daily origin/<基点ブランチ> && python3 -m pip install -q requests
   export NOTE_COOKIE="_note_session_v5=${_note_session_v5}"（値は絶対に表示しない）
2. python3 _tools/publish/post_note_api.py --sync-status（手動公開の取り込み。401/403 なら Cookie 更新が必要と報告して停止）
3. python3 _tools/publish/gen_upload_status.py（YouTube本編の公開状態。失敗しても続行）
4. note-publish-schedule.md で予定日が今日以前かつ note-draft-status.md が「公開済み」でない回を EP 番号順に最大2本。無ければ何もせず終了（通知しない）。
5. 各回 python3 _tools/publish/post_note_api.py --publish-ep <N>（見出し画像・YouTube導線の差し込み・前の回の「次の回」更新まで自動。下書き未保存・動画未公開・Cookie失効・仕様変化のときは自動で拒否/停止）。見出し画像が無ければ make_note_thumbnail.py で生成して再実行。--force は使わない。エンドポイントを推測で変えない。
6. 変更をコミット → git push origin HEAD:<基点ブランチ>（拒否なら作業ブランチへ push -u）
7. 報告（1〜2行）：公開した回（EP・タイトル・note URL）／失敗とその理由。
```

公開スケジュールそのものは `python3 _tools/publish/note_publish_schedule.py --start <最初の日>` で作る（動画が公開済みの回は毎日1本で追いつき、追いついた後は動画と同日）。
