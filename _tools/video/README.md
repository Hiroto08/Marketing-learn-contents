# 動画ジェネレーター（make_video.py）

スライドHTML（このリポジトリ共通のスライドエンジン）から、**合成音声ナレーション付きの動画**を自動生成するツールです。

## 特徴

- **ズレない**: 1スライドずつ録画して音声と結合 → 最後に連結。スライド間でズレが蓄積しない
- **臨場感**: 各アニメーションを対応するナレーション段落の **0.7秒前** に発火（話題に入る直前に図が動く）
- **高速な再実行**: TTSはテキストのハッシュでキャッシュ。ナレーションを少し直して再実行しても変更段落だけ再合成
- **部分再録画**: `--slides 3 7` のように指定スライドだけ録画し直して結合できる

## 前提条件

| 必要なもの | 確認方法 |
|---|---|
| VOICEVOX ENGINE | `curl http://127.0.0.1:50021/version` |
| ffmpeg / ffprobe | `ffmpeg -version` |
| playwright (Python) | `python3 -c "import playwright"` |
| Chromium | `/opt/pw-browsers/chromium-*/chrome-linux/chrome`（自動検出）|

VOICEVOX ENGINE の起動例:

```bash
cd /opt/voicevox_engine/engine/linux-cpu-x64
nohup ./run --host 127.0.0.1 --port 50021 > /tmp/voicevox.log 2>&1 &
# 起動完了まで30秒ほど待つ（辞書構築のため）
```

## 使い方

```bash
# 基本（EP02 を動画化）
python3 _tools/video/make_video.py \
  --slide 01_beginner/ep02_3c-stp-analysis/slide.html \
  --out /tmp/EP02.mp4

# スライド3と7だけ録画し直して再結合（スライド修正後など）
python3 _tools/video/make_video.py \
  --slide 01_beginner/ep02_3c-stp-analysis/slide.html \
  --out /tmp/EP02.mp4 --slides 3 7

# 話者・速度を変える（話者IDは VOICEVOX の /speakers で確認）
python3 _tools/video/make_video.py \
  --slide ... --out ... --speaker 8 --speed 1.0
```

主なオプション:

| オプション | 既定値 | 説明 |
|---|---|---|
| `--speaker` | 2（四国めたんノーマル） | VOICEVOX 話者ID |
| `--speed` | 1.1 | 読み上げ速度 |
| `--lead` | 0.7 | アニメ発火→ナレーション開始の秒数 |
| `--gap` | 0.35 | 段落間の無音 |
| `--width/--height` | 1280×720 | 解像度（1920×1080 も可） |
| `--crf` | 18 | 映像品質（小さいほど高品質） |
| `--workdir` | `<出力名>.work` | 中間ファイル置き場 |

## スライド側の契約（このツールが前提とするもの）

このリポジトリの全エピソード slide.html が満たしている共通エンジン構造:

- `NARRATIONS` — スライドごとのナレーション文字列の配列。**`\n` 区切りの段落**がTTS・アニメ同期の単位
- `STEPS` — `{si, t, ids, anim}` のアニメーションステップ配列（siはSLIDES_META順のインデックス）
- `SLIDES_META` — `{id, start, end, dotContainerId}` の配列。**この配列の順序が上映順**（DOM順ではない）
- 関数 `advanceStep()` / `resetSlideElements(si)` / `SLIDE_FIRST_STEP` / `state`
- UI要素 `#ctrl` `#prog-wrap` `#narr-panel`（録画時に非表示化される）

**ステップ⇔段落の対応**: ステップ数Sと段落数Pが異なる場合、ステップjは段落 `floor(j*P/S)` に割り当てられます。段落とステップの数を揃えると最も自然な同期になります。

## 処理の流れ

```
slide.html
  │ 1. extract   Playwright で NARRATIONS / STEPS を抽出
  │ 2. tts       段落ごとに VOICEVOX で WAV 合成（md5キャッシュ）
  │ 3. schedule  ステップ発火時刻とナレーション開始時刻を計算
  │              音声トラック（無音含む）をスライド単位で組み立て
  │ 4. record    スライドごとに実時間録画（UI非表示・1280×720）
  │              スケジュールに従い advanceStep() を発火
  │ 5. mux       録画webmの頭を切り落として音声と結合 → mp4
  └ 6. concat    全スライドを無劣化連結 → 完成
```

## トラブルシューティング

- **「VOICEVOX ENGINE に接続できません」** → 上記の起動コマンドを実行し、30秒待ってから再試行
- **声がスライドとずれる** → スライドのアニメーションが多すぎて段落数と乖離していないか確認（`STEPS` と段落数を揃える）
- **特定スライドだけ直したい** → スライド修正後に `--slides N` で部分再録画（workdirが残っている必要あり）
- **README記載のフォント警告/外部フォントエラー** → オフライン環境でのGoogle Fonts読込失敗は無害（埋め込みフォントで描画される）
