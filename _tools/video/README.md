# make_video.py — スライド動画ジェネレーター

`slide.html` から VOICEVOX 合成音声付きの MP4 を自動生成します。

## 特徴

- **ズレない**: 1スライドずつ録画して音声と結合、最後に連結。スライド間でズレが蓄積しない
- **自然な息継ぎ**: ナレーション内の `。！？` 区切りで文ごとに合成し、文間・段落間に無音ポーズを挿入
- **臨場感**: 各アニメーションを対応するナレーション段落の `--lead` 秒前に発火（話題に入る直前に図が動く）
- **高速な再実行**: TTS は文単位の md5 キャッシュ。変更した文だけ再合成
- **部分再録画**: `--slide N` で特定スライドだけ処理して再連結

## 前提条件

```bash
pip install playwright
playwright install chromium

# VOICEVOX ENGINE 起動
cd /opt/voicevox_engine/engine/linux-cpu-x64
nohup ./run --host 127.0.0.1 --port 50021 > /tmp/voicevox.log 2>&1 &
# 起動完了まで30秒ほど待つ（辞書構築のため）
```

## 使い方

```bash
# EP02 を動画化
python3 _tools/video/make_video.py \
  01_beginner/ep02_3c-stp-analysis/slide.html \
  --out /tmp/ep02_video

# スライド3だけ再録画
python3 _tools/video/make_video.py slide.html --out /tmp/ep02 --slide 2

# TTS だけ生成（録画スキップ）
python3 _tools/video/make_video.py slide.html --out /tmp/ep02 --no-record
```

## オプション一覧

| オプション | 既定値 | 説明 |
|---|---|---|
| `--speaker` | `11` | VOICEVOX 話者 ID（11 = 玄野武宏 ノーマル） |
| `--speed` | `1.0` | TTS 速度スケール |
| `--sent-gap` | `0.28` | 文末（。！？）後の息継ぎポーズ（秒） |
| `--para-gap` | `0.45` | 段落（`\n`）間のポーズ（秒） |
| `--lead` | `0.7` | アニメ発火→ナレーション開始の先行時間（秒） |
| `--step-gap` | `0.35` | 同段落内の連続ステップ間隔（秒） |
| `--intro` | `0.6` | 最初のアニメ前のホールド（秒） |
| `--outro` | `1.0` | ナレーション終了後の末尾無音（秒） |
| `--slide N` | 全て | このスライドインデックス（0始まり）だけ処理（繰り返し可） |
| `--no-record` | off | TTS のみ生成、録画はスキップ |
| `--out DIR` | `video_out` | 出力ディレクトリ |
| `--width/--height` | `1280×720` | 解像度 |
| `--crf` | `18` | ffmpeg x264 品質（小さいほど高品質） |

## VOICEVOX 話者 ID

| ID | 話者 |
|----|------|
| 2  | 四国めたん ノーマル |
| **11** | **玄野武宏 ノーマル ← デフォルト** |
| 39 | 玄野武宏 喜び |
| 13 | 青山龍星 ノーマル |

## スライド側の契約

各 `slide.html` が満たす必要がある JS 構造:

```js
const NARRATIONS = [
  `スライド1のナレーション。\n段落2。`,   // \n で段落区切り
  `スライド2のナレーション。`,
  // ...
];

const STEPS = [
  {si: 0, t: 0,   ids: ['s1-title'], anim: 'rv-fade'},
  {si: 0, t: 1.5, ids: ['s1-sub'],   anim: 'rv-up'},
  {si: 1, t: 30,  ids: ['s2-hd'],    anim: 'rv-scale'},
];

const SLIDES_META = [
  {id: 's1', start: 0,  end: 30},
  {id: 's2', start: 30, end: 90},
];

const TOTAL_SECS = 600;
```

- `NARRATIONS[i]` ↔ `SLIDES_META[i]`（1対1対応）
- `STEPS[j].si` は `SLIDES_META` の 0 始まりインデックス
- アニメクラス: `rv-fade` `rv-up` `rv-scale` `rv-pop`

## 処理フロー

```
slide.html
  │
  ├─ extract()        NARRATIONS / STEPS / SLIDES_META を正規表現で抽出
  │
  ├─ gen_tts()        ナレーションごとに:
  │                     \n → 段落分割
  │                     。！？ → 文分割
  │                     VOICEVOX で文ごとに合成（md5 キャッシュ）
  │                     文 + sent_gap + 文 + … + para_gap + 段落 + …
  │                     → .work/audio/narr_NN.wav
  │
  ├─ build_schedule() ステップ → 段落マッピング、アニメ発火時刻を計算
  │
  ├─ record()         スライドごとに Playwright で実時間録画
  │                     アニメを schedule に従い発火 → WebM
  │                     full_audio（intro + narr + outro）と結合 → mp4
  │
  └─ concat()         全スライドを ffmpeg concat → <ep>_final.mp4
```

## TTS キャッシュ

`.work/tts/<md5>.wav` に文単位でキャッシュ（キー: `文テキスト|話者ID|速度`）。
ナレーションを一部修正して再実行した場合、変更された文だけ再合成されます。
全部再生成したい場合は `.work/audio/` と `.work/tts/` を削除してください。
