# _tools — 製造ラインの見取り図

制作（創作判断）は `.claude/skills/` のロールスキル、製造（機械作業）はここのツール。
**一気通貫の入口は `pipeline/` の2本**。個別ツールはその部品。
FAIL時の対処・クォータ・禁止事項は `.claude/skills/episode-production/pipeline.md` が正。

```
pipeline/
  run_episode.sh <ep_dir> [--upload]   本編: QA→ビルド→A/V検証→タイムスタンプ→サムネ→(アップ)
  run_shorts.sh  <ep_dir> [--upload]   Shorts: spec→stage生成→QA→縦型ビルド→検証→(アップ)
setup_env.sh                            環境復旧（ffmpeg/playwright/VOICEVOX。GitHub 403時は
                                        Docker Hubレイヤー取得へ自動フォールバック）
video/
  make_video.py                         スライドHTML→mp4 レンダリングエンジン
  postbuild_episode.py <ep_dir>         ビルド後処理（A/V・LUFSゲート、実測タイムスタンプ書き戻し、
                                        video_build/ へのmp4ステージング）
checks/
  verify_episode.py <ep_dir>            本編QAゲート（7項目）
  verify_shorts.py <short_dir>          Shorts QAゲート（9項目）
shorts_template/
  vertical_template.html                縦型エンジン（編集禁止。gen_stageのコピー元）
  gen_stage.py <spec.py> <stage.html>   spec（宣言的データ）→stage.html 生成。spec形式はdocstring参照
publish/
  make_thumbnail.py <ep_dir>            thumbnail.md→1280x720 PNG 自動生成
  upload_youtube.py --episode/--shorts  private アップロード（サムネ自動設定・manifest冪等）
  get_refresh_token.py                  初回OAuth（ユーザーの手元PCで実行）
audio/                                  BGM/SFXアセット関連
```

新しいエピソード（EP07以降）の製造は、成果物（script.md / slide.html / description.md /
thumbnail.md / shorts.md / shorts_build/shortN/spec.py）が揃っていれば:

```bash
bash _tools/pipeline/run_episode.sh <ep_dir> --upload
bash _tools/pipeline/run_shorts.sh  <ep_dir> --upload   # クォータ: 動画6本/日
```

の2コマンドで完了する。
