# ライセンス台帳（BGM・効果音・書体・画像）

表現コード（`docs/expression/expression-code.md` §10）の台帳。**ここに無い素材は、動画・サムネイルに使わない。**
写真は `_tools/expression/fetch_assets.py` が取得と同時に追記する（手で足さない）。置き場は `_assets/photos/`（記録は `_assets/photos/assets.json`）。

## 1. 常に使う素材

| 種類 | 素材 | 出どころ | ライセンス | 商用 | クレジット表記 |
|---|---|---|---|---|---|
| BGM | `_assets/audio/v1/bgm_a_calm.wav`・`bgm_b_curious.wav`・`bgm_c_steady.wav` | 自作（`_tools/expression/synth_v1.py` が数式から合成。外部の音源・サンプルは不使用） | 自作（権利は自分。CC0 相当） | 可 | 不要 |
| 効果音 | `_assets/audio/v1/sfx_question.wav`・`sfx_number.wav`・`sfx_answer.wav`・`sfx_turn.wav` | 同上 | 同上 | 可 | 不要 |
| BGM・効果音（旧） | `_assets/audio/bgm_calm_loop.wav`・`sfx_ding.wav`・`sfx_pop.wav`・`sfx_whoosh.wav` | 自作（`_tools/audio/synth_assets.py`） | 同上 | 可 | 不要 |
| 声 | VOICEVOX：玄野武宏（話者ID 11） | VOICEVOX 0.25.2 | VOICEVOX 利用規約・キャラクター利用規約（商用可・クレジット必須） | 可 | 要：概要欄に「VOICEVOX：玄野武宏」（今の概要欄に記載済み） |
| 書体 | Noto Sans JP／Noto Sans CJK JP | Google Fonts・OS 同梱 | SIL Open Font License 1.1 | 可 | 不要 |
| 書体 | Inter | OS 同梱（rsms/inter） | SIL Open Font License 1.1 | 可 | 不要 |
| アイコン | Font Awesome Free 6（長尺の一部） | slide.html に同梱 | アイコン CC BY 4.0／フォント OFL 1.1 | 可 | 不要（同梱ファイルのライセンス表記で足りる） |
| 図解・グラフ | 画面の図（棒・点の並び・値札など） | 自作（`_tools/expression/visuals.py` が台本の数字から描く） | 自作 | 可 | 不要 |

## 2. 取得した写真（自動追記）

使ってよいライセンスは **CC0／Public domain／CC BY** だけ。CC BY-SA・NC・ND・不明は使わない。
アニメ・映画・テレビの切り抜き（作品系 GIF・画像）は使わない。ロゴ・人物の肖像は使わない。

| 取得日 | 使う回 | 素材ID | 種類 | 出典 | 作者 | ライセンス | 商用 | クレジット表記 |
|---|---|---|---|---|---|---|---|---|
| 2026-11-13 | u01_jcpenney-sale（試作）・c01（試作） | jcpenney_store | 写真 | [File:JCPenney - Governor’s Square - Tallahassee, FL.jpg](https://commons.wikimedia.org/wiki/File:JCPenney_-_Governor%E2%80%99s_Square_-_Tallahassee,_FL.jpg) | FLGALine1999 | CC0 | 可 | 不要 |
