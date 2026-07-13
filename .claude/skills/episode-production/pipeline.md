# 一気通貫パイプライン（判断不要の製造ライン手順書）

**対象読者：このリポジトリで動画を作る全モデル（Opus/Sonnet含む）。**
制作（台本・スライド・パッケージングの創作判断）と製造（ビルド・検証・アップロードの機械作業）を
分離してある。**製造フェーズは下のコマンドを順に叩くだけ**で完走できる。ゲートは全て機械検査で、
FAILしたら出力に修正指示が出る。自分で品質判断を発明しないこと。

## 全体フロー

```
[制作フェーズ]（創作判断あり。episode-production SKILL.md 本文の工程）
  企画GO判定(yt-producer) → 台本(yt-scriptwriter) → スライド(yt-slide-designer)
  → 読み監査(yt-voice-director) → 概要欄/サムネ設計/Shorts台本(yt-publisher)
  → Shorts spec作成(yt-shorts-designer: spec.py)
        ↓ 成果物: script.md / slide.html / description.md / thumbnail.md /
        ↓          shorts.md / shorts_build/shortN/spec.py   ←★全部コミット
[製造フェーズ]（判断不要。このファイルの手順）
  bash _tools/pipeline/run_episode.sh <ep_dir> --upload     # 本編（約30分）
  bash _tools/pipeline/run_shorts.sh  <ep_dir> --upload     # Shorts3本（約10分）
  git add/commit/push（タイムスタンプ・thumbnail.png・publish_manifest.json）
```

## 実行規約（ユーザーのプロンプトに書かれていなくても常に適用）

ユーザーは「EPNNをビルドしてアップまで」程度しか書かない。以下は**このファイルが内包する
デフォルトの段取り**であり、指示がなくても順に全部実行する（CLAUDE.mdの解釈規約と同一）：

1. run_episode.sh → （必要なら）run_shorts.sh の順で**バックグラウンド実行**し完了を待つ
2. サムネPNGは生成後に必ずReadで目視確認（折返し・つぶれ）。悪ければ再生成してから先へ
3. 各工程が終わるたびに mp4 以外の成果物を**コミット・プッシュ**する
4. mp4・サムネは SendUserFile で納品する。**Shortsは1エピソードずつ（3本単位）で送り、
   captionに各本のタイトル（shorts.mdのタイトル案）を番号付きで列挙**して識別できるようにする
   （ファイル名は `<episode>_short<N>_final.mp4` でエピソードと番号は自明。captionで各本の中身を補う）
5. 完了報告の定型: Studio URL／尺／A/V差／LUFS／残る手動作業（公開ボタン・関連動画リンク・
   エンドスクリーン）。FAILで止まった場合は、どのゲートで何を直せば良いかを報告
6. quotaExceeded は「翌日16時(JST)に同コマンド再実行」で継続し、その旨をユーザーに伝える
7. このファイルとスキルに既定がある事項は**ユーザーに質問せず既定に従う**

## 製造フェーズの実行手順（コピペで順に）

```bash
# 1. 本編: QA→ビルド→A/V検証→タイムスタンプ実測修正→サムネ生成→privateアップロード
bash _tools/pipeline/run_episode.sh 02_intermediate/ep06_pricing-psychology --upload

# 2. サムネの目視確認（必須。折返し・文字つぶれがないかReadツールでPNGを見る）
#    → 悪ければ thumbnail.md に「## サムネ生成データ」(main:/sub:)を書いて
#      python3 _tools/publish/make_thumbnail.py <ep_dir> で再生成。
#      アップ済みでも upload_youtube.py --episode <ep_dir> の再実行だけで差し替わる

# 3. Shorts: spec→stage生成→QA→縦型ビルド→A/V検証→privateアップロード
bash _tools/pipeline/run_shorts.sh 02_intermediate/ep06_pricing-psychology --upload

# 4. コミット（mp4はgitignore済みなので入らない。それ以外の変更は全部入れる）
git add <ep_dir> && git commit -m "EPNN: build+upload (videoId等をメッセージに)" && git push -u origin <branch>
```

ビルドは重いので、対話セッションでは `run_in_background` で実行し Monitor/通知で待つのが正しい。
`--upload` を外せばアップロード以外を実行する（クォータ節約・検品だけしたい時）。

## クォータ（YouTube Data API・1日10,000単位、太平洋時間0時=日本時間16時リセット）

| 操作 | 単位 | 備考 |
|---|---|---|
| 動画アップロード (videos.insert) | 1,600 | **1日6本まで**が上限目安 |
| サムネ設定 (thumbnails.set) | 50 | 差し替えは安い |
| プレイリスト追加 | 50 | |
| 1話フルセット（本編1+Shorts3） | 6,600 | 1日で2話は不可能 |

複数エピソードを一気に作った場合、アップロードは6本/日で分割する。
publish_manifest.json による冪等化があるので**同じコマンドの再実行は常に安全**
（アップ済み動画はスキップされ、サムネ差分だけ適用される）。

## FAIL時プレイブック（この表以外の独自対処をしない）

| 症状 | 対処 |
|---|---|
| VOICEVOXが起動しない/50021応答なし | `bash _tools/setup_env.sh`（GitHub 403時はDocker Hubフォールバックが自動で走る。~1.9GB・数分） |
| `github.com ... 403 not enabled for this session` | このセッションのリポジトリスコープ外へのアクセス。**リトライ禁止**。VOICEVOXならsetup_env.shのフォールバックに任せる |
| verify_episode / verify_shorts FAIL | 出力の✗行が具体的な修正対象。該当ファイルを直して再実行（ナレーション不一致→NARRATIONS/spec.pyをmdに合わせる、セーフエリア侵犯→`<br>`位置や文言短縮） |
| postbuild「A/V 単体超過」 | 表示されたコマンド通り該当slide_NN.mp4を消して `--slide N` 付きで再ビルド→postbuild再実行 |
| postbuild「LUFS帯外」 | ビルドコマンドの `--bgm/--sfx-dir` 指定漏れが典型。run_episode.sh経由なら起きない |
| Shortsのvideoストリーム欠落 | エンジンが3回まで自動再録画する。それでも残ればverify出力の指示通り`--slide N`で再録画。stage.htmlの`#__heartbeat`を消していないか確認 |
| アップロードで`quotaExceeded` | 本日分終了。翌日16時（JST）以降に同じコマンドを再実行（冪等なので安全） |
| トークン更新失敗 | Secrets（YT_CLIENT_ID/SECRET/REFRESH_TOKEN）未設定か、OAuth同意画面がテストのまま7日失効。yt-uploader SKILL.md参照 |
| ディスク`no space left` | 大きい不要物を消す: `/tmp/vv_layer.tgz`、過去EPの `video_build/out/.work` |

## やってはいけない（事故防止の不変則）

- `vertical_template.html`・stage.htmlの**エンジン部分**（keyframes / rv-* / `.se` / `#__heartbeat`）を編集しない。Shortsの見た目は**spec.pyだけ**をいじって`gen_stage.py`で再生成する
- mp4をコミットしない（gitignore済み）。stage.html / spec.py / thumbnail.png / publish_manifest.json は**コミットする**
- `--privacy public` にしない。公開は人間がStudioで押す
- NARRATIONSやタイムスタンプを目分量で書かない（前者はshorts.mdと文字一致、後者はpostbuildが実測で書く）
- クォータの日次上限を超えて連投しない（quotaExceededを見てからでよい）

## 公開前の手動作業（APIで不可能・ユーザーに引き渡す定型リスト）

- [ ] Studioで各動画の最終確認 → 公開 or 公開予約
- [ ] **各Shortの「関連動画」に本編を設定**（唯一のクリック可能な送客導線）
- [ ] 固定コメントのピン留め／エンドスクリーン・カード
- [ ] AI音声（VOICEVOX）利用の開示申告
