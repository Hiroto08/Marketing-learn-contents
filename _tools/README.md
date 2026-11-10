# _tools — 製造ラインの見取り図

> シリーズ固有の値（チャンネルID・シリーズ名・タグ接頭辞・公開曜日・特典URL・声など）はリポジトリ直下の `series.json` にあり、各ツールは `_tools/series.py` 経由で読む。新しいテーマの立ち上げは `docs/replication-playbook.md`、設定チェックは `python3 _tools/series_doctor.py [--online]`。

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
  verify_episode.py <ep_dir>            本編QAゲート（構造・ナレーション一致・描画）
  verify_shorts.py <short_dir>          Shorts QAゲート（尺・フック・セーフエリア・テロップ同期・48px）
  verify_note.py <file>                 note 記事のゲート（構造＋N1〜N7：自分の呼び方・タイトルの数字・対象読者・冒頭の価値…）
  ── 品質ゲート（基準は .claude/skills/episode-production/quality-gates.md）──
  quality_record.py <ep_dir>            下の検査を全部走らせて <ep_dir>/quality_record.md に実施記録を書く
  check_readings.py <dir> [--built]     読み検査 R1〜R10（固有名詞の台帳・辞書登録・読みの一致・数字と英字の読み・
                                        別辞書との食い違い）。--built はビルド後の音声の読み（built_readings.json）を照合
  proper_nouns.py --verify              固有名詞の台帳（docs/proper-nouns.md）の確認ソースを取得して読みを確かめる
  check_facts.py <dir>                  数字の2ソース検査 F1〜F3（台本の「## 数字の確認」の表）
  check_style.py <dir>                  AI臭さ検査 A1〜A7・T1〜T2（語尾・接続詞・定型句・回をまたぐ同じ文・画面の数字）
  reading_allowlist.txt / reading_confirmed.txt / style_legacy.txt / style_fixed_lines.txt
                                        検査の例外リスト（足してよい条件は各ファイルの冒頭。検査を通すために足さない）
shorts_template/
  vertical_template.html                縦型エンジン（編集禁止。gen_stageのコピー元）
  build_telop_spec.py <uNN_dir>         第2シリーズ：shorts.md のナレーションから spec.py を作る（テロップ同期型）
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
