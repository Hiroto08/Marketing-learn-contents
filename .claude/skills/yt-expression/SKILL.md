---
name: yt-expression
description: 表現コード v1（映像意図・素材の組み込み・アニメーション・音）を、Shorts と長尺に当てる役。台本の各スライドに映像の型を付けて visual_plan.json を作り、ライセンスが明確な写真を取得し、検査を通す。Use when adding visuals/animation/sound design to an episode, creating or fixing visual_plan.json, or when run_shorts.sh / run_episode.sh stops at the expression gate. Triggers - 映像意図, visual_plan, 素材を入れて, 表現コード, 図解を入れて, expr_gate FAIL, check_expr FAIL, check_visual_plan FAIL
---

# 表現コード v1 を当てる（映像意図・素材・アニメーション・音）

**やることは「visual_plan.json を1つ書く」だけ。** 色・文字・配置・動き・BGM・効果音・ラウドネスは、道具が決まった値で当てる。自分で CSS や音を書かない。

- 仕様（数値の合否基準）：`docs/expression/expression-code.md`
- 決裁（2026-11-13）：素材埋め込み・アニメーションありが標準。Shorts も長尺も同じ。
- **本適用は 2026-12-06 の週の制作バッチから**（Shorts は同週のバッチ＝u22 以降、長尺は c03 から）。それより前に作る回は、現行の表現のまま。日付の判定は道具（`expr_gate.py`）がする。自分で判断しない。
- 台本・数字・固有名詞・テロップの文は変えない（`quality-gates.md` の R・F・A・T はそのまま）。

## 0. いつ使うか

| 状況 | すること |
|---|---|
| 12/6 の週以降に、新しい Short（u22〜）・ケースファイル（c03〜）を作る | 下の手順1〜5 |
| `run_shorts.sh`／`run_episode.sh` が「visual_plan.json が無い」で止まった | 下の手順1〜5 |
| `check_visual_plan.py`／`check_expr.py` が FAIL | §4 の表の対処だけ |
| 12/5 までに作る回・u01〜u21・c01・c02・EP01〜24 | **何もしない**（現行の表現で作られる） |
| 道具が正しく動くか確かめたい・環境を作り直した | `bash _tools/expression/selftest.sh`（最後に SELFTEST PASS） |

## 1. 手順（この順に。飛ばさない）

台本と spec.py／slide.html ができて、`verify_shorts.py`／`verify_episode.py` が PASS してから始める。

```bash
# Shorts の場合（<回> は s2_ura/u22_xxx など。N は 1）
D=<回>/shorts_build/short1
python3 _tools/shorts_template/gen_stage.py $D/spec.py $D/stage.html      # stage.html が無ければ
python3 _tools/expression/plan_visuals.py $D/stage.html $D/visual_plan.json   # ① 下書き（TODO が残る）
#   ② visual_plan.json の TODO を、§2 の表を見て埋める
python3 _tools/expression/fetch_assets.py <回> --id <素材ID> --query "<英語の検索語> haslicense:unrestricted"   # ③ 写真を使うスライドだけ
python3 _tools/expression/check_visual_plan.py $D/stage.html $D/visual_plan.json   # ④ PASS するまで直す
bash _tools/pipeline/run_shorts.sh <回>                                      # ⑤ いつものコマンド。v1 で作られ、検査まで走る

# 長尺（ケースファイル）の場合
python3 _tools/expression/plan_visuals.py <回>/slide.html <回>/visual_plan.json
#   TODO を埋める → fetch_assets.py → 
python3 _tools/expression/check_visual_plan.py <回>/slide.html <回>/visual_plan.json
bash _tools/pipeline/run_episode.sh <回>
```

- ビルドのあと、`<回>/…/expr_record.json` と `quality_record.md` の「6. 表現コード v1」が全部 ✓ なら合格。
- コミットするもの：`visual_plan.json`・`expr_record.json`・`expr_mix.json`・`_assets/photos/`（写真と assets.json）・`docs/expression/license-ledger.md`。`stage_expr.html`／`slide_expr.html` はコミットしない（毎回作られる）。
- 元の `stage.html`／`slide.html`／`spec.py` は、表現のために書き換えない。

## 2. 型の選び方（上から順に当てはめ、最初に当たった型を使う）

**Shorts（全スライドに絵が要る。none は使えない）**

| 順 | そのスライドのセリフ | 型 | 書くもの |
|---|---|---|---|
| 1 | 最後のスライド | 1枚目と同じ型・同じ値 | 1枚目の内容を写し、`"reset": true` を足す。`sync` は書かない |
| 2 | 「N% 減った／増えた」 | `chart_drop` | `value`（N）、増えたなら `"direction":"up"`、`before_label`・`after_label`（**ナレーションにある語**。例：「セール」「毎日安く」） |
| 3 | 同じ単位の数字が2つ（2.65ドルと1.50ドル） | `compare_bars` | `a`・`b`（数値）、`a_text`・`b_text`（台本の表記どおり）、`a_label`・`b_label`（ナレーションにある語） |
| 4 | 「N回・件・人・店・個・社」（N は 1000 まで） | `dot_grid` | `n`。「やめた・消えた」でなければ `"strike": false` |
| 5 | 会社・店・商品・場所の名前が出る | `photo` | `asset`（素材ID）、`focus`（写真のどこを見せるか。例 `"40% 50%"`）。年を言うなら `stamp`（例 `"2012"`） |
| 6 | 西暦だけ（数字の見せ場が無い） | `timeline` | `year` |
| 7 | セール・値引き・定価・割引の話 | `tag_strike` | なし |
| 8 | 「なぜ」「？」の問い | `question` | なし |
| 9 | 「」の発言の引用 | `quote` | なし |
| 10 | 答え・結論を言う（最後のスライド以外） | `check` | なし |

**長尺（絵は文字の後ろに入る。配置は変わらない）**

| 順 | そのスライド | 型 | 書くもの |
|---|---|---|---|
| 1 | 1枚目（題名）と最後の1枚（締め） | `photo` | `asset`・`focus`。事例の会社・店の写真 |
| 2 | 数字のカードが2つ以上あり、**単位が同じ** | `bar_cells` | `values`（カードの順に、数値） |
| 3 | 「N回・件…」（N は 1000 まで） | `dot_grid` | `n`、`"strike": false` |
| 4 | 会社・店・場所の名前が主役 | `photo` | `asset`・`focus` |
| 5 | それ以外 | `none` | `intent` に、絵を足さない理由を書く |

**全部に共通**

- `intent`：なぜその絵か、10字以上。
- `sync`：その絵を動かし始める要素の id（下書きが入れる。数字のあるテロップの id）。1枚目と `reset` の1枚には書かない。
- `answer`：答えの文（**画面の文字**のとおり）。長尺で語りの言い回しが違うときは、`answer_narration` にナレーションの言い回しを書く（例：画面「得した気分を買っていた」／語り「得した気分を買っていました」）。
- **台本に無い数字・文字を、絵に書かない。** `value`・`n`・`year`・`stamp`・`a_text` などは、そのスライドのナレーションか画面にある値だけ。
- Shorts は写真を2枚まで。Shorts も長尺も、**絵のうち半分以上は、写真以外（自作の図解）にする。**
- 迷ったら、数字のあるスライドは図解（`chart_drop`・`dot_grid`・`compare_bars`）、名前のあるスライドは `photo`、どちらも無ければ `question`・`quote`・`check`・`tag_strike` から意味の合うもの。

書き方の見本：`_tools/expression/selftest/u01_visual_plan.json`（Shorts）・`c01_visual_plan.json`（長尺）。

## 3. 写真の決まり

```bash
python3 _tools/expression/fetch_assets.py <回> --id <素材ID> --query "<英語の検索語> haslicense:unrestricted"
```

- 取得元は Wikimedia Commons だけ。使えるライセンスは **CC0／Public domain／CC BY** だけ（道具が検査する。CC BY-SA・NC・ND・不明は落ちる）。
- 素材ID は英小文字と `_`（例 `jcpenney_store`）。同じID が既にあれば、取得せずに使い回す。
- 取得したら、**必ず Read で写真を見る**。次のどれかなら使わない（別の検索語でやり直すか、図解に替える）：人の顔が大きく写っている／事例と関係ない／ロゴだけ／アニメ・映画・テレビの画面／文字だらけ。
- `haslicense:unrestricted` で見つからなければ、`haslicense:attribution -haslicense:share-alike` で CC BY を探す。CC BY を使ったら、`_assets/photos/assets.json` の `credit` の文を、概要欄（description.md）の末尾に足す。
- **見つからなければ、写真をあきらめて図解にする。** ライセンスの分からない画像・ストックサイトの画像・作品の切り抜き（GIF を含む）は、どんな理由でも使わない。
- 台帳（`docs/expression/license-ledger.md`）は、道具が追記する。手で書かない。

## 4. 検査で止まったとき（この表の対処だけ。独自の回避をしない）

| 検査 | 症状 | 対処 |
|---|---|---|
| expr_gate | 「visual_plan.json が無い」 | 手順1〜5 を行う。`expr_legacy.txt` に行を足して通さない |
| check_visual_plan P1 | 型が無い・TODO が残っている | §2 の表で型を選ぶ |
| P2・P3 | 絵が足りない／写真が多い | 写真を図解に替える。長尺は `none` を減らす |
| P4 | 写真が台帳に無い・ライセンス不可 | `fetch_assets.py` で取り直す。だめなら図解に替える |
| P5・P6 | 数字・ラベルが台本に無い | 台本にある値・語に直す。台本のほうを変えない |
| P7 | sync の要素が無い | エラーに出ている id の一覧から選ぶ |
| P8 | 最後の1枚が1枚目と違う | 1枚目の内容を写して `reset: true` |
| P9 | answer が無い | 画面の文字のとおりに書く。長尺は `answer_narration` も |
| check_expr S1・S2 | ラウドネス・ピーク | もう一度ビルドする。直らなければ `exmix.py` の不具合として Issue #2 に書く（数値を手で変えない） |
| S3・S6・S7 | 冒頭の音・効果音・つなぎ目 | `--expr v1` が付いていない。`run_shorts.sh`／`run_episode.sh` から作り直す |
| M1 | 最初の動きが2秒より遅い | 1枚目の型を、動く型（`chart_drop`・`dot_grid`・`photo`）にする |
| M2 | 動きの無い時間が長い（Shorts 3秒・長尺 12秒） | そのスライドの型を替える（`photo` か、動きの長い `dot_grid`）。長尺は `none` を `photo` に |
| D1・D2 | 文字が小さい・数字が小さい | テロップの文字サイズは `build_telop_spec.py` が決める。spec を手で直していないか確かめて作り直す |
| V4 | 最後と最初の絵が違う | P8 と同じ |
| 画面にコードの文字が並ぶ | CSS に `</` を書いた | `_tools/expression/*.css` を直す（コメントにも閉じタグを書かない） |
| fetch_assets が 429 | Wikimedia が混んでいる | 10分おいて同じコマンド。待てなければ図解にする |

## 5. 最後に目で確かめる（Fable でも Opus でも、必ず行う）

機械検査が PASS しても、次を Read で見る。1つでも当てはまれば、型を替えて作り直す。

```bash
f=$(ls <ビルド先>/*_final.mp4)
ffmpeg -v error -y -i $f -vf "fps=2,scale=180:-1,tile=11x5" -frames:v 1 /tmp/sheet.jpg    # Shorts。長尺は fps=1/8,scale=480:-1,tile=5x6
```

| 見ること | だめな例 |
|---|---|
| 絵が表示されている | 枠が空・コードの文字が出ている・写真が真っ黒 |
| 数字と絵が同じタイミング | テロップの数字が出たのに、棒・点がまだ動いていない |
| 絵がセリフと合っている | 「増えた」のに棒が下がる・関係ない店の写真 |
| 文字が読める | 絵と文字が重なる・写真の上の文字が読めない |
| 最後のコマ＝最初のコマ（Shorts） | 最後に別の絵のまま終わる |

- 耳で確かめる項目（V1〜V4 と、BGM・効果音の感じ）は、AI は判定しない。レビュー便で人が書く。

## 6. やってはいけないこと

1. `expr_v1_*.css`・`exmix.py`・`synth_v1.py` の数値を、合格させるために変える（仕様書と同じコミットで、社長決裁を受けたときだけ変える）
2. `expr_legacy.txt`・`style_legacy.txt` に新しい回を足して通す
3. `EXPR_FORCE=1` を、本番の回（`s2_ura/`・`0N_*/`）で使う（試作と selftest だけ）
4. 公開済み・予約済みの動画を、表現を変えて作り直す・差し替える（社長決裁）
5. 台帳に無い写真・音・書体を使う。作品系の切り抜きを使う
6. slide.html／stage.html のエンジン（keyframes・rv-*・`.se`・`#__heartbeat`）を書き換える
