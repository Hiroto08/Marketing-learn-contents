# 週次アップロード配信ジョブ（毎週月 9:00 JST ／ cron `0 0 * * 1`）

```
週次アップロード配信ジョブ（YouTube配信担当）。

【基点（必須）】git fetch origin && git checkout -B weekly-run origin/<基点ブランチ> を基点にする。詳細は docs/autonomous-operation.md §3.1 に全面的に従う。要点：
1. python3 -m pip install -q requests; python3 _tools/publish/gen_upload_status.py で docs/upload-status.md を YouTube 実体から再生成し、唯一の真実として判断（回の判定は動画タグ <tag_prefix>-epNN / <tag_prefix>-epNN-sM。タイトルに「第N回」は無い）。これ自体が失敗（認証/クォータ）したら何もせず報告して停止。
2. 公開は予約運用：python3 _tools/publish/publish_episode.py --schedule-all を実行（series.json の公開曜日・時刻・EP順・本編＋Shorts同時刻。予約済みは動かさず延長のみ＝冪等）。例外：public最大EP=N の次の EP(N+1) が「予定枠を過ぎたのに非公開・予約なし」なら python3 _tools/publish/publish_episode.py --episode <dir> で即時公開してから --schedule-all。出力に TIMED が出たら報告に明記（過去に一度公開された動画は予約できない→その時刻に --episode で即時公開する単発実行が必要）。飛び級公開は絶対にしない。
3. 未UPのギャップ（本編/Shortsが未UP）があれば §3.1 の優先度で非公開アップ（upload_youtube.py）→ 次回以降の --schedule-all で連鎖に乗る。全話UP済み・予約済みなら新規制作はせず、番外編の企画を1本だけ提案して報告。
4. 付帯処理（非致命・クォータ残に応じて）：今後7日以内に公開される本編を優先して python3 _tools/publish/upload_captions.py --episode <dir>、続けて --all --limit 3（字幕済みは自動スキップ）→ python3 _tools/publish/sync_playlists.py。
5. メール：公開予約済みの本編EPについて _deliverables/broadcast/ep<NN>_*.md が無ければ python3 _tools/repurpose/make_broadcast.py --episode <dir> で生成・コミット。続けて環境変数 KIT_API_KEY があれば python3 _tools/repurpose/schedule_kit_broadcasts.py を実行（動画の publishAt と同時刻に Kit の予約ブロードキャストを登録。登録済みは自動スキップ）。publishAt を持たない TIMED 回は --episode <dir> --send-at <RFC3339> で登録。キー値は絶対に表示しない。
6. QA FAIL 時はアップせず報告して停止。
7. 終了時：gen_upload_status.py で再生成→コミット→ git push origin HEAD:<基点ブランチ> を試みる（non-fast-forward なら fetch→merge して再push。権限で拒否なら作業ブランチへ push -u）。
報告：公開予約カレンダー（upload-status.md の該当節）／今週公開される回／アップした動画ID／字幕・再生リスト結果／Kit予約の結果／TIMED・持ち越し事項。
```
