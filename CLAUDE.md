# AI時代のマーケティング・ラボ — 制作リポジトリ

YouTube教育チャンネルの動画（本編9分＋Shorts3本/話）をエピソード単位で制作・ビルド・配信する。
エピソードは `01_beginner/epNN_*` 〜 のディレクトリ（script.md / slide.html / description.md /
thumbnail.md / shorts.md / shorts_build/shortN/spec.py が1話ぶんの成果物）。

## 短い指示の解釈規約（ユーザーは詳細を書かない。以下を暗黙に含める）

ユーザーの指示は短い（例:「EP07を作って」「EP07をビルドしてアップまで」「ショート続き」）。
**次のデフォルトを毎回、指示されなくても実行する**：

| 短い指示 | 実行内容（全部やる） |
|---|---|
| 「EPNNを作って／新規作成」 | episode-productionのロール順で創作→QA PASS→コミット→`run_episode.sh --upload`→`run_shorts.sh --upload`→コミット→報告 |
| 「EPNNをビルドして」「動画化して」 | `run_episode.sh <ep_dir>`（アップロードなし）→コミット→mp4納品 |
| 「アップ(ロード)まで」「上げて」 | 上記に `--upload` を付け、Shortsも指示に含まれるなら `run_shorts.sh --upload` |
| 「ショート(だけ)」「Shorts作って」 | `run_shorts.sh <ep_dir> [--upload]` |
| 「続き」「再開」 | publish_manifest.json と直近コミットから未完了工程を特定して再開（全コマンド冪等） |
| 「サムネ直して/変えて」 | thumbnail.md の `## サムネ生成データ` を編集→make_thumbnail.py→目視→`upload_youtube.py --episode` 再実行で差し替え→コミット |

**常に適用する実行規約**（プロンプトに書かれていなくても守る）：
1. ビルド系は**バックグラウンド実行**し完了を待つ（対話をブロックしない）
2. FAILは `.claude/skills/episode-production/pipeline.md` のプレイブック表の対処のみ。解決したら同じコマンドを再実行
3. 工程が終わるたびに**成果物をコミット・プッシュ**（mp4以外。コミットメッセージにvideoId等の要点）
4. mp4/サムネ等の完成物は SendUserFile で納品（第2シリーズは Drive のレビュー便へ自動送付）
5. 完了報告は「Studio URL・尺・A/V差・LUFS・品質検査の結果（quality_record.md）・残る手動作業（24話の Shorts の関連動画リンク等）」を定型で
6. クォータ超過（quotaExceeded）は翌日のリセット時刻（太平洋時間0時＝日本時間で夏16時・冬17時）以降に同コマンド再実行で継続。ユーザーに続き時刻を伝える
7. 途中で判断に迷う選択肢が出ても、pipeline.md・スキルに既定があるものは**質問せず既定に従う**

## 記録の規約（GitHub でやりとりする。2026-11-05 ユーザー指示）

- 考え・判断・提案・確認したいことは、**チャットだけで終わらせず文書にしてコミット・プッシュ**する。
  入口は `docs/decision-log.md`（確認待ち／進行中の仮説／決定の記録）。中身が長いものは該当文書（作戦なら
  `docs/post-series-strategy.md`、第2シリーズなら `s2_ura/README.md` 等）に書き、判断ログからリンクする。
- 自分で判断したこと（題材の差し替え・既定値の選択など）も「私の判断」と明記して理由とともに残す。
- 定期ジョブも、方針を変えた・判断した・ユーザーに確認したいことが出たときは判断ログに追記してコミットする。
- 動画（mp4）はリポジトリに入れない。

## 作業の入口（迷ったらここ）

| 指示の種類 | 使うもの |
|---|---|
| これまでの判断・確認待ち・進行中の仮説 | `docs/decision-log.md` |
| 第2シリーズ「売れる仕組みの裏側」（Shorts単独 uNN・ケースファイル cNN） | `s2_ura/README.md`（置き場所・型・2コマンド・`ura_schedule.py`） |
| 新規エピソード制作・リニューアル（創作） | `episode-production` スキル（ロール分担表が入口） |
| ビルド・動画化・アップロード（製造） | `.claude/skills/episode-production/pipeline.md` の2コマンド：`bash _tools/pipeline/run_episode.sh <ep_dir> [--upload]` / `bash _tools/pipeline/run_shorts.sh <ep_dir> [--upload]` |
| 品質の合否基準（読み・数字・AI臭さ・テロップ・note・差し替え） | `.claude/skills/episode-production/quality-gates.md`／固有名詞の台帳 `docs/proper-nouns.md`／1コマンド `python3 _tools/checks/quality_record.py <dir>` |
| 個別作業（読み監査だけ・サムネだけ等） | 該当する `yt-*` ロールスキル |
| ツールの部品表 | `_tools/README.md` |
| 別テーマへの横展開・シリーズ固有の設定 | `docs/replication-playbook.md`／`series.json`（チャンネルID・シリーズ名・タグ接頭辞・公開曜日・特典URL等。**ツールに直書きしない**） |

## 絶対則（全モデル共通）

1. **品質判断を発明しない**——ゲートは全て機械検査（verify_episode / verify_shorts / postbuild_episode ／
   品質ゲート：check_readings・check_facts・check_style・verify_note）。合否の基準は
   `.claude/skills/episode-production/quality-gates.md` が正。FAIL時は pipeline.md のプレイブック表に従う
2. **エンジンを編集しない**——slide.html/stage.html の keyframes・rv-*・`.se`・`#__heartbeat`。
   Shortsの見た目は spec.py だけを編集し gen_stage.py で再生成する
3. **アップロードは常にprivate**。公開は `publish_episode.py`（`--schedule-all` の週次予約連鎖 or `--episode`）経由でのみ行い、
   **EP番号の昇順・本編＋同回Shorts同時**を厳守（飛び級厳禁。docs/autonomous-operation.md §3.1）。
   例外：第2シリーズ「売れる仕組みの裏側」（`s2_ura/`）は Shorts 毎日・本編週1で、同時公開は求めない（2026-11-04 承認）。
   公開は `ura_schedule.py --apply` 経由のみ・同じ種類（uNN/cNN）の中で番号順・飛び級厳禁（`s2_ura/README.md`）
4. mp4はコミットしない（gitignore済み）。spec.py / stage.html / thumbnail.png /
   publish_manifest.json / タイムスタンプ修正は**コミットする**
5. ナレーション・タイムスタンプを目分量で書かない（文字一致検査と実測書き戻しがある）
6. YouTube APIクォータ: 動画アップロードは**1日6本まで**（詳細は pipeline.md の表）
7. ビルド系コマンドは重い（本編30分/Short3分）——バックグラウンド実行して通知を待つ
8. **固有名詞は、読みを確かめたものだけを使う**（社長指示 2026-11-10・Issue #2）——人名・企業名・商品名・地名は
   `docs/proper-nouns.md`（台帳）に、読みと確認ソース（公式サイト・出版社の著者紹介）を書いてから原稿に使う。
   確認できない名前は使わない。ビルドの前後に `check_readings.py` が台帳と音声の読みを照合する
   （きっかけ：EP22 で森岡毅さんを「もりおか あつし」と読んで公開した。正しくは「つよし」）
9. **数字は2つ以上の別のサイトで確かめる**。台本の `## 数字の確認` の表に書く（`check_facts.py`）
10. **公開済みの動画は差し替えない。公開前の動画の差し替えは、社長の承認を受けてから**（Issue #2 に修正版と新旧の videoId を書く）。
    公開済みの回で見つけた誤りは、検査（`check_readings.py` の BAD・`check_style.py`）に型を足して、次から機械で止める
11. **動画・記事ごとに実施記録を残す**——ビルドで `quality_record.md` が書かれる。コミットする。
    抑揚・間など耳でしか分からない項目（V1〜V4）には、AI が ✓ を付けない

## 環境（claude.ai/code のリモートコンテナ）

- コンテナ再作成で git外のファイルは消える。復旧は `bash _tools/setup_env.sh`（冪等。
  VOICEVOXはGitHubが403のためDocker Hubフォールバック内蔵・~1.9GB）
- YouTube認証は環境Secrets（YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN）で注入済み
- VOICEVOX起動確認: `curl -s http://127.0.0.1:50021/version`
