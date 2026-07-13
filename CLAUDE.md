# AI時代のマーケティング・ラボ — 制作リポジトリ

YouTube教育チャンネルの動画（本編9分＋Shorts3本/話）をエピソード単位で制作・ビルド・配信する。
エピソードは `01_beginner/epNN_*` 〜 のディレクトリ（script.md / slide.html / description.md /
thumbnail.md / shorts.md / shorts_build/shortN/spec.py が1話ぶんの成果物）。

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
