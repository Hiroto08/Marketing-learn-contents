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
4. mp4/サムネ等の完成物は SendUserFile で納品
5. 完了報告は「Studio URL・尺・A/V差・LUFS・残る手動作業（公開ボタン/関連動画リンク等）」を定型で
6. クォータ超過（quotaExceeded）は翌日16時（JST）以降に同コマンド再実行で継続。ユーザーに続き時刻を伝える
7. 途中で判断に迷う選択肢が出ても、pipeline.md・スキルに既定があるものは**質問せず既定に従う**

## 作業の入口（迷ったらここ）

| 指示の種類 | 使うもの |
|---|---|
| 新規エピソード制作・リニューアル（創作） | `episode-production` スキル（ロール分担表が入口） |
| ビルド・動画化・アップロード（製造） | `.claude/skills/episode-production/pipeline.md` の2コマンド：`bash _tools/pipeline/run_episode.sh <ep_dir> [--upload]` / `bash _tools/pipeline/run_shorts.sh <ep_dir> [--upload]` |
| 個別作業（読み監査だけ・サムネだけ等） | 該当する `yt-*` ロールスキル |
| ツールの部品表 | `_tools/README.md` |

## 絶対則（全モデル共通）

1. **品質判断を発明しない**——ゲートは全て機械検査（verify_episode / verify_shorts /
   postbuild_episode）。FAIL時は pipeline.md のプレイブック表に従う
2. **エンジンを編集しない**——slide.html/stage.html の keyframes・rv-*・`.se`・`#__heartbeat`。
   Shortsの見た目は spec.py だけを編集し gen_stage.py で再生成する
3. **アップロードは常にprivate**。公開ボタンは人間がStudioで押す
4. mp4はコミットしない（gitignore済み）。spec.py / stage.html / thumbnail.png /
   publish_manifest.json / タイムスタンプ修正は**コミットする**
5. ナレーション・タイムスタンプを目分量で書かない（文字一致検査と実測書き戻しがある）
6. YouTube APIクォータ: 動画アップロードは**1日6本まで**（詳細は pipeline.md の表）
7. ビルド系コマンドは重い（本編30分/Short3分）——バックグラウンド実行して通知を待つ

## 環境（claude.ai/code のリモートコンテナ）

- コンテナ再作成で git外のファイルは消える。復旧は `bash _tools/setup_env.sh`（冪等。
  VOICEVOXはGitHubが403のためDocker Hubフォールバック内蔵・~1.9GB）
- YouTube認証は環境Secrets（YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN）で注入済み
- VOICEVOX起動確認: `curl -s http://127.0.0.1:50021/version`
