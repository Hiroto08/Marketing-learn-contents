# 第2シリーズ「売れる仕組みの裏側」— 制作・公開の手順

作戦は `docs/post-series-strategy.md` v0.2（2026-11-04 承認）。24話（`0*/epNN_*`）とは別のフォルダ・タグ・公開ルールで回す。

## 1. 置き場所とタグ

| 種類 | ディレクトリ | 中身 | 動画のタグ |
|---|---|---|---|
| Short（毎日1本） | `s2_ura/uNN_<slug>/` | `shorts.md`（`## Short 1` 1本だけ）・`shorts_build/short1/spec.py`・`stage.html`・`publish_manifest.json` | `mlab-ura` `mlab-uNN` |
| ケースファイル（本編・週1本） | `s2_ura/cNN_<slug>/` | `script.md`・`slide.html`・`description.md`・`thumbnail.md`・`thumbnail.png`・`publish_manifest.json` | `mlab-ura` `mlab-cNN` |
| 公開予定 | `s2_ura/schedule.json` | `{"id": "u01", "date": "2026-11-15"}` の並び | — |
| 状態表 | `s2_ura/STATUS.md` | 自動生成（`ura_schedule.py`） | — |

タグが `mlab-epNN` ではないので、24話側の公開ガード・状態表（`publish_episode.py`・`gen_upload_status.py`）には影響しない。

## 2. 作る（創作）

**Short（uNN）** は `.claude/skills/episode-production/shorts-production.md` に従う（尺15〜30秒・4〜6枚・合計150字以内・ループ）。そのうえで、このシリーズでは次を守る。

- **題材の型**：見る人自身の困りごと・違和感（買い物・職場・SNS）を冒頭で突き、その犯人・秘密・理由を、実在の企業・商品と数字1つで明かす。
  - **ハウツー型（やり方・書き方・直し方・準備・紙1枚・たった1行）にしない**（v0.2 §3-3）。ハウツーはケースファイルで扱う。
- **数字・事実は一次情報で確かめる**（yt-researcher）。確かめられない数字は使わず、題材を差し替える。出典は shorts.md の `**出典：**` に書く。
- **S1 の最初の要素**に、シリーズ名の帯 `{"cls":"k-tag","html":"売れる仕組みの裏側 #NN"}` を置く（t=0.0）。
- **最終スライド**：
  - ナレーションは「冒頭のループの一文」＋「続きは、明日。」にする。CTA 検査は「続きは」で通る。
  - 画面テキストに `{"cls":"cta-line","html":"明日：◯◯はなぜ？"}` を置く。次の回の問いを1行で予告する。
  - 続きのケースファイルがある回は、ナレーションを「続きは、下の長編リンクへ。」にしてもよい。
- `shorts.md` の書式は24話と同じ（`**タイトル案：**`・`**ナレーション：**` ブロック）。追加の欄は次の3つ。
  - `**ハッシュタグ：** #… #…`（ニッチ2個まで。#Shorts・#売れる仕組み・#マーケティング は自動で付く）
  - `**続きの本編：** cNN`（ある回だけ）
  - `**出典：**`
- 見た目は `spec.py` だけを編集する。アクセント色はシリーズ共通の `#E11D48`（glow `rgba(225,29,72,.25)`）。ケースファイルの slide.html は回ごとに一意の色（検査が重複を拒否）。

**ケースファイル（cNN）** は episode-production スキルの本編の作り方で作るが、尺と枚数は短い版にする。検査（`verify_episode.py`）はディレクトリ名 `cNN_` を見て、自動でケースファイルの基準に切り替わる。

| 項目 | ケースファイルの基準 |
|---|---|
| 枚数 | 8〜12枚 |
| 尺 | 推定3:30〜5:00、実測3:20〜5:10 |
| S1 冒頭 | 最初の1文（約10秒・68字以内）で、Short の問いへの答えを**数字つきで言い切る**。前置き・自己紹介・目次は置かない |
| 問いかけ・逆接 | 問いかけは2回以上、逆接・因果は4回以上。最後のスライドに開いた問いを置く |
| 題名 | 検索される言葉（「〇〇 なぜ」「〇〇 理由」＋会社名・商品名）。サムネの帯は「CASE FILE #NN」で自動表示 |
| 最後 | 「自分の仕事で使うなら」を1つだけ示す。ハウツーはここで扱う |

- **slide.html は手で書かない**。`cNN/case.json`（各スライドのステージ HTML・STEPS の要素順・ナレーション）を書き、`python3 _tools/video/build_case_slide.py <cNN>/case.json 06_case-studies/ep22_v-shaped-recovery/slide.html <cNN>/slide.html` で生成する（エンジン部分は既存本編のまま、ステージとデータだけ差し替える）。script.md のナレーションは case.json と同じ文にする（検査が文字単位で照合）。
- note 記事・Kit メールは、ケースファイルには当面付けない（v0.2 §3-8：どちらも今は入口になっていない。工数は YouTube に寄せる）。週次分析で note→YouTube の流入が増えたら見直す。

## 3. 作る（製造）— 24話と同じ2コマンド

```bash
bash _tools/pipeline/run_shorts.sh  s2_ura/u01_<slug> --upload     # Short 1本（約3分）
bash _tools/pipeline/run_episode.sh s2_ura/c01_<slug> --upload     # ケースファイル（約15分）
```

- アップロードは常に private。1日6本まで（16:00 JST に回復）。
- 成果物（spec.py・stage.html・shorts.md・publish_manifest.json・thumbnail.png）はコミットする。mp4 はコミットしない。

## 4. 公開予約

```bash
python3 _tools/publish/ura_schedule.py --apply --dry-run   # 確認
python3 _tools/publish/ura_schedule.py --apply             # schedule.json の日付の18:00に publishAt を付ける
python3 _tools/publish/ura_schedule.py --playlist          # シリーズの再生リスト（初回に作成・以後は追加だけ）
```

- 同じ種類（u／c）の中で番号順に昇順でない予定は、全体を拒否する。同じ日にまとめて出すのは可。
- 前の回が未アップ・未予約なら、その回から後ろは予約しない（飛び級しない）。
- 公開済みの動画には触らない。
- 公開後、Studio で各 Short の「関連動画」に、同じ話のケースファイル（無ければ最新のケースファイル）を設定する（API なし）。
