# 引き継ぎ：公開前の回の修正と、これからのコンテンツ制作（2026-11-10）

品質是正（Issue #2）のうち、スキルと検査ツールの更新は終わった。**コンテンツの修正と新規制作は、別のモデル（セッション）が行う**（社長指示 11/10）。この文書は、その担当への引き継ぎ。

- 合否の基準：`.claude/skills/episode-production/quality-gates.md`
- 何を直したかの全体：`docs/skill-audit-2026-11.md`
- 決裁の記録：`docs/decision-log.md`（2026-11-10）

## 0. 決裁済みのこと（変えない）

| 事項 | 決裁 |
|---|---|
| 公開前の回の差し替え | 承認済み（社長 11/10）。新旧の videoId を Issue #2 に書く |
| 公開済みの回（EP01〜22・その Shorts） | 差し替えない。誤りは検査に型を足して、次から止める |
| 公開スケジュール | 変えない。EP23 11/11、EP24 11/14、第2シリーズ 11/15〜（すべて18:00）。間に合わないときは、遅らせる前に Issue #2 で相談 |
| 基点ブランチ | `claude/build-upload-bqpddd`。push は `claude/note-articles` にも |

## 1. 最初にやること

```bash
cd /home/user/Marketing-learn-contents && git checkout claude/build-upload-bqpddd && git pull
bash _tools/setup_env.sh                                   # VOICEVOX・Playwright・janome
python3 _tools/checks/proper_nouns.py --list | head         # 台帳が読めること
```

## 2. 公開前の回の修正（急ぐ順）

どの回も、**ツール側の修正は済んでいる**。作り直す（ビルドし直す）だけで直る項目と、原稿の修正が要る項目がある。

| 順 | 回 | 公開（18:00） | 今 YouTube にある版の問題 | やること |
|---|---|---|---|---|
| 1 | EP23 の Short 2本目（`7GPZiMWNk1s`） | **11/11** | 「①」を「いちつめ」と読む | 作り直すだけ（ツール修正済み） |
| 2 | EP23 本編（`zA4P9czo8BM`） | **11/11** | 「何でしょうか」→なにでしょうか（1か所） | 作り直すだけ |
| 3 | EP24 本編（`v6ywp-obN_U`） | 11/14 | 西暦が下2桁（2025年5月・2029年）。「何でしょうか」4か所・「何のため」 | 作り直すだけ |
| 4 | u01（`ZJIrnlCjV7s`） | 11/15 | 「2012年のことです」→じゅうにねん（画面は 2012年） | 作り直すだけ |
| 5 | u02・u05・u07・u08 | 11/16〜22 | 西暦が下2桁 | 作り直すだけ |
| 6 | u03 | 11/17 | 「ノースウェスタン」が途中で切れる | 作り直すだけ |
| 7 | u06 | 11/20 | 「TOP5」→トップご | 作り直すだけ（トップファイブになる） |
| 8 | c01 | 11/21 | 西暦が下2桁。並べて→なべて。アンカリング・ルーレットの区切れ | 作り直すだけ。余力があれば §4 の原稿修正 |
| 9 | u14 | 11/28 | 西暦が下2桁。**「アリー」は読みを確認できない名前**（検査 R1 で不合格になる） | 原稿修正が要る（下記） |
| 10 | c02 | 11/28 | 西暦が下2桁。ハーバード・ベインアンドカンパニーの区切れ | 作り直すだけ |

- 読みの問題が無い回（u04・u09〜u13、EP23 の Short 1・3本目、EP24 の Shorts）は、作り直さない。
- EP23 が最優先。**11/11 の正午までに終わらなければ、今の版のまま公開される**（遅らせない）。

**u14 の原稿修正**（`s2_ura/u14_followers-shirts/shorts.md` の S2）

```
旧：「なのに、Tシャツが売れなかった。2019年、アメリカのインフルエンサー、アリーの話です。」
新：「なのに、Tシャツが売れなかった。2019年、アメリカの、あるインフルエンサーの話です。」
```
そのあと `python3 _tools/shorts_template/build_telop_spec.py s2_ura/u14_followers-shirts`（spec.py は手で直さない）。

## 3. 1本を差し替える手順

**24話（EP23・EP24）**

```bash
bash _tools/pipeline/run_episode.sh 06_case-studies/ep23_failure-cases        # 本編（約30分・バックグラウンド）。読み検査と実施記録まで入っている
ONLY=short2 bash _tools/pipeline/run_shorts.sh 06_case-studies/ep23_failure-cases   # Short は2本目だけ作り直す
python3 _tools/publish/upload_youtube.py --episode 06_case-studies/ep23_failure-cases   # 新しい videoId で private アップ（--replace-old は付けない）
python3 _tools/publish/upload_youtube.py --shorts  06_case-studies/ep23_failure-cases   # 中身が変わった Short だけが上がる（同じ mp4 は自動で飛ばす）※下の注意
python3 _tools/publish/retire_superseded.py 06_case-studies/ep23_failure-cases          # 旧版の予約とタグを外す（削除しない）
python3 _tools/publish/publish_episode.py --schedule-all --dry-run && python3 _tools/publish/publish_episode.py --schedule-all
python3 _tools/publish/upload_captions.py --episode 06_case-studies/ep23_failure-cases
python3 _tools/publish/sync_playlists.py
python3 _tools/repurpose/schedule_kit_broadcasts.py --refresh                           # 予約メールの動画リンクを新しい URL に
```

- **注意（Shorts）**：run_shorts.sh は、その回の Shorts を全部作り直す。作り直した mp4 はバイトが変わり、アップロードで「中身が変わった」と判定される。**直す1本だけを作り直すには `ONLY=short2 bash _tools/pipeline/run_shorts.sh <dir>`** を使う（他の Short は触らないので、アップロードでも飛ばされる）。
- 本編を差し替えたら、同じ回の Shorts の概要欄にある長編リンクと、`_deliverables/note/ep<NN>_*.md`・`_deliverables/broadcast/ep<NN>_*.md`・`docs/shorts-related-video-checklist.md` の旧 videoId を、新しいものに置き換える（11/9 の EP23・24 差し替えと同じ作業。コミット f483bcb を参照）。
- 旧版を再生リストから外す（`sync_playlists.py` は外さない。11/9 は手で外した）。

**第2シリーズ（uNN・cNN）**

```bash
bash _tools/pipeline/run_shorts.sh  s2_ura/u01_jcpenney-sale                  # Short（約3分）
bash _tools/pipeline/run_episode.sh s2_ura/c01_jcpenney-fair-and-square       # ケースファイル（約15分）
python3 _tools/publish/upload_youtube.py --shorts  s2_ura/u01_jcpenney-sale   # Drive のレビュー便へ _r3 で自動送付
python3 _tools/publish/upload_youtube.py --episode s2_ura/c01_jcpenney-fair-and-square
python3 _tools/publish/upload_captions.py --episode s2_ura/c01_jcpenney-fair-and-square
python3 _tools/publish/ura_schedule.py --apply --playlist                     # 旧版の予約を外し、新版に同じ日時。再生リストも入れ替え
```

**共通**

- アップロードは1日6本まで（回復は冬時間17:00 JST）。11/10 17:00 以降の枠はまだ使っていない。
- 1本ごとに `quality_record.md` と `built_readings.json` ができる。コミットする。
- 新旧の videoId の表を Issue #2 に書く（関連動画の代行バッチが参照する。c01・c02 の ID が変わると、u01〜u14 の関連先も変わる）。
- `docs/decision-log.md` に記録し、両ブランチへ push。

## 4. 余力があれば（原稿の修正。必須ではない）

公開前の回は「旧基準の回」（`_tools/checks/style_legacy.txt`）なので、文章（A）・数字（F）・テロップ（T）の検査は参考表示にとどまり、不合格にはならない。直すなら、次が候補。

| 回 | 項目 | 内容 |
|---|---|---|
| c01 | T2 | 画面の「3種類」がナレーションに無い（ナレーションは「3つだけ」）。どちらかに合わせる |
| c01・c02 | A4 | 2本に同じ文がある（「ただ、ここで1つ、疑問が残ります。」「売れる仕組みの裏側は、ショート動画を毎日18時に公開しています。」）。片方を書き換える |
| c02 | A1・A5 | 「ます」で終わる文が4つ続く。文の長さがそろいすぎ（ばらつき0.34） |
| u01〜u14・c01・c02 | F1 | 台本に `## 数字の確認` の表が無い。各数字に2サイトの出典を付ける |
| EP24 の note 記事 | N3・N5・N6 | 対象読者の指定が無い。定型句2つ。体言止めが4文続く |
| EP23 の note 記事 | N1 | 「自社」が2か所 |

原稿を直した回は、`style_legacy.txt` からその行を消す（以後は新基準で合格が必要になる）。

## 5. これから作る回（u15〜・c03〜・次の note 記事）

最初から新基準で作る。手順は `docs/routines/ura-weekly-production.md` と `s2_ura/README.md` §2。要点だけ書く。

1. **固有名詞**：使う名前を `docs/proper-nouns.md` に足し、`python3 _tools/checks/proper_nouns.py --verify` で確認日を入れる。確認できない名前は使わない。
2. **数字**：台本に `## 数字の確認` の表（数字｜何の数字か｜ソース1｜ソース2）。2つの別のサイトで一致した数字だけを使う。
3. **文章**：過去の回と同じ文を使わない。同じ接続詞は Shorts で1回・ケースファイルで3回まで。
4. **検査**：`python3 _tools/checks/quality_record.py <回のフォルダ>` が PASS。run_shorts.sh／run_episode.sh は、ビルドの前後に自動で走らせる。
5. 検査で止まったら、`.claude/skills/episode-production/pipeline.md` のプレイブック表に従う。**`style_legacy.txt`・`reading_confirmed.txt`・`reading_allowlist.txt` に行を足して通さない**（足してよい条件は各ファイルの冒頭）。

## 6. 耳で確かめる項目（人にお願いすること）

AI は音声を聞けない。抑揚・間・平坦さ（V1〜V4）は、レビュー便で聞いた人が `quality_record.md` の「5. 耳で確かめる項目」に書く。Issue #2 に書かれた感想は、制作側が記録に写し、型を検査に足す。

## 7. まだ決まっていないこと

| 事項 | 今の扱い |
|---|---|
| EP22 のコメント（森岡毅さんの読みの指摘）への返信 | 返信していない。文案を Issue #2 に出して、承認を受けてから返信する |
| EP22 の「成功確率 30%→97%」の出典が1つ（STUDY HACKER）だけ | 公開済みなので直さない。同じ数字を今後使うときは、2つめの出典を取る |
| 「アプリ収益化の実験ノート」の記事 | このリポジトリに下書きが無い。置き場所が決まれば、`verify_note.py`（N1〜N7）をそのまま使える |
| 声の設定（抑揚の強さ・文の間） | 変えていない。変えるなら、設定ごとのサンプルをレビュー便に置いて、耳で選んでもらう |
