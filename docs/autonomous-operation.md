# 週次自律運転ランブック（v1.0）

作成日：2026-07-22 ／ 位置づけ：`docs/monetization-strategy.md` M1「16週連続配信」を人手ほぼゼロで回すための運用手順。
Routine（スケジュール起動）で「毎週：次話をL3制作 → QA → 非公開アップロード＋公開予約」を自動化する。

> **⚙️ 運用ステータス（2026-07-23 更新・重要）**
> - **アップロード状況の正＝ `docs/upload-status.md`**（各話 manifest の videoId を YouTube 実照会した権威ある状態表）。本ランブック内の在庫判定は必ずこれを基準にする。
> - 現状：**EP01〜06 は本編＋Shorts が公開済み(public)**、EP07〜17 は private（公開待ち）、EP18〜20 未UP（18/19ビルド済・20要再UP）、EP21〜24 未制作。
> - **YouTube配信の一括キャッチアップは専用セッションが実施中で、完了後に停止する予定**。恒常運用の担い手が別途必要。
> - **本ランブックの §3 のRoutineは「ready状態のスペック」**（YouTube担当セッションが `create_trigger` で立ち上げて使う）。**このセッション（マネタイズ＝YouTube以外担当）では起動しない**。以前ここで作った2本のRoutineは誤った stale 前提だったため削除済み。
> - 必要ツールは実装済み：AI合成開示（`upload_youtube.py`）・実測取得（`fetch_analytics.py`）・`yt-analytics.readonly` スコープ。

> **正直な前提**：これは「完全放置」ではなく **監督付き自律** です。制作・検品・アップロード・公開予約までは自動、
> 残る人手は**週あたり数分**（下の§4のStudio作業のみ）。YouTube APIに存在しない操作（A/Bサムネ・Shorts関連動画リンク）は原理的に人が押します。

---

## 1. 全体像：2つの定期ジョブ

| ジョブ | 周期 | 中身 | 成果物 |
|--------|------|------|--------|
| **制作ジョブ** | 週1 | 次の未制作EPをL3制作→QA→本編＋Shorts3本を非公開アップロード＋公開予約 | privateの動画（publishAt付き） |
| **分析ジョブ** | 週1 | 直近公開回の実測取得→§7へ書き戻し。月初回は`--channel`でYPP進捗も | retention-packaging.md §7追記 |

制作ジョブは配信の1〜2週間先行して走らせ、**公開待ちのストックを常に持つ**（1本詰まっても配信が途切れない）。

## 2. 前提条件（初回1回だけ・これが揃うまで自動化は始めない）

- [ ] `YT_CLIENT_ID` / `YT_CLIENT_SECRET` / `YT_REFRESH_TOKEN` が環境Secretsに登録済み
- [ ] リフレッシュトークンが **`yt-analytics.readonly` スコープ込み**（分析ジョブの前提。`get_refresh_token.py`を1回再実行）
- [ ] **OAuth同意画面を「本番」に昇格**（テストのままだとトークンが7日で失効し、無人運転が止まる）
- [ ] 公開先プレイリストID・サムネ運用の方針が決まっている
- [ ] 制作ジョブが走る環境に VOICEVOX / ffmpeg / Playwright 等のビルド依存が入っている（`_tools/setup_env.sh` 済み）

## 3. Routineプロンプト（そのまま登録して使う）

### 3.1 制作・配信ジョブ（週1・例：毎週月曜）※upload-status.md基準

```
週次配信ジョブ。まず docs/upload-status.md（＝各話 publish_manifest.json の videoId を YouTube videos.list で実照会した状態表）を最新化し、それを唯一の真実として次の1本を決める。優先順位：
(1) Shorts が「未UP」の既アップロード本編（現状 EP07/EP08/EP17）→ 該当EPの Shorts を3本制作・動画化して非公開アップロード。
(2) 本編が「未UP」で slide.html 完成済み（現状 EP18/EP19、EP20は要再UP）→ 本編＋Shortsを非公開アップロード。
(3) 未制作EP（現状 EP21〜24）→ docs/episode-briefs.md に従い L3 新規制作（verify_episode.py が RESULT: PASS まで）→ 動画化→非公開アップロード。
アップロードは yt-uploader（upload_youtube.py・AI合成開示 既定ON）。本編は必要に応じ --publish-at で次の土曜18:00 JST に公開予約。
完了後、publish_manifest.json をコミット・push し、python3 _tools/publish/gen_upload_status.py で docs/upload-status.md を再生成してコミット（次回ジョブの真実源になる）。
QA（verify_episode / verify_shorts）が一度でも FAIL したらアップロードせず、原因と現状を報告して停止（不完全な動画は上げない）。
git はその回専用の新ブランチで作業し push -u origin まで行う。
```

> **注意（stale事故の教訓）**：`publish_manifest.json` は作業ブランチによって有無が食い違う。必ず `docs/upload-status.md`（実照会済み）を真実源にすること。ローカルに manifest が無い＝未UP とは限らない。

### 3.2 分析ジョブ（週1・例：毎週火曜）

```
週次分析ジョブ。直近1〜2週間で公開されたEPについて yt-analyst を実行：
python3 _tools/publish/fetch_analytics.py --episode <ep_dir> --days 28 でKPI比較と急落地点を取得し、
retention-packaging.md §7 に「- YYYY-MM-DD EP◯◯: 事象 → ルール変更」形式で書き戻してコミット。
毎月最初の実行時は python3 _tools/publish/fetch_analytics.py --channel --days 28 も実行し、
monetization-strategy.md §4.2 の表とYPP進捗（総再生時間/登録者）を突合して報告。
異常（CTR<2% や 30秒残存<60%）があれば次回への具体的な変更指示を1〜3件添えて報告。
```

**登録方法**：`create_trigger` で cron（最小粒度は毎時、**UTCで指定**）。fresh-session（`create_new_session_on_fire=true`）で毎回クリーンに走らせるのが安全。
JST(UTC+9)→UTCは9時間引く（引いて日をまたぐ場合は曜日もずらす）。
例）月曜9:00 JST ＝ 月曜0:00 UTC → cron `0 0 * * 1`／水曜9:00 JST ＝ 水曜0:00 UTC → cron `0 0 * * 3`。

## 3.3 Routineの立ち上げ方（YouTube担当セッションが実施）

このセッションはYouTube以外を担当するため**ここではRoutineを作らない**。YouTube配信の恒常運用を引き継ぐセッションが、下記スペックで `create_trigger` すれば即稼働する。

| Routine | 推奨cron(UTC) | 起動(JST) | プロンプト | 通知 |
|---------|--------------|-----------|-----------|------|
| 配信ジョブ | `0 0 * * 1` | 毎週月 9:00 | §3.1 | push+mail |
| 分析ジョブ | `0 0 * * 3` | 毎週水 9:00 | §3.2 | push |

- **fresh-session推奨**（`create_new_session_on_fire=true`）。毎回クリーンな環境で起動しビルド成果物を残さない
- **前提**：Routineを作る側の環境に §2 の Secrets／ビルド依存が入っていること。fresh-sessionにはMCPコネクタ（GitHub等）が渡らないため、git操作は`git push`コマンドで行う（本ランブックのプロンプトはそう設計済み）
- JST→UTC変換：9時間引く（日をまたぐ場合は曜日もずらす）。例）月9:00 JST＝月0:00 UTC→`0 0 * * 1`／水9:00 JST＝水0:00 UTC→`0 0 * * 3`
- 変更・停止：`update_trigger`／`delete_trigger`／一時停止は`enabled=false`

> **参考**：以前このセッションで作った2本（`trig_01RmfF…`／`trig_018EMU…`）は、stale前提かつ担当分離のため**削除済み**。上記スペックで作り直すこと。

## 4. 毎週残る人手（Studio・APIで自動化不可）※合計数分

- [ ] 本編に **エンドスクリーン／カード**（テンプレ流用で30秒）
- [ ] 各Shortsに **「関連動画」＝本編リンク**（送客の本命導線。Studioでしか設定できない）
- [ ] 固定コメントの **ピン留め**（投稿は自動・ピン留めだけ手動）
- [ ] サムネ **「テストして比較」** 3案の投入（A/Bテスト。APIなし）
- [ ] 公開予約された動画をStudioで一目確認（誤りがあれば公開前に直せる）

> この5点は「自動化できない」のではなく「YouTubeがAPIを提供していない」。将来APIが増えたら§4から§1へ移す。

## 5. 失敗時の設計（無人でも壊れない）

- **QA FAIL**：公開予約しない。半端な動画は絶対に上げない（制作ジョブのプロンプトに明記済み）
- **トークン失効**：分析/アップロードが403/401 → ジョブは報告して停止。§2の「本番昇格」で再発防止
- **冪等性**：アップロードは publish_manifest.json のSHA-256で二重投稿を自動スキップ。ジョブ再実行は安全
- **ディスク枯渇**：ビルド成果物（mp4/キャッシュ）はfresh-session方式なら毎回破棄されるため蓄積しない
- **ネタ切れ**：EP01〜24を消化したら制作ジョブは「番外編（フローD）を1本提案して止まる」に切り替える

## 6. 段階的に任せる（いきなり全自動にしない）

1. **手動キック**：まず制作ジョブのプロンプトを人が打って1本通す（現状ここまで可能）
2. **半自動**：Routineで制作ジョブだけ自動化、アップロードは人が最終実行
3. **監督付き自律**：制作＋アップロード＋公開予約まで自動、§4だけ人手（本ランブックの完成形）
4. 分析ジョブを追加し、改善ループも無人化

各段でKPI（改革計画§1）が維持されているかを確認してから次段へ。**自律の範囲は品質が担保できる範囲でしか広げない**。

## 7. YouTube担当セッションへの引き継ぎ（このセッションが用意した資産）

YouTube以外担当のこのセッションが、YouTube運用に使えるツールを実装済み。YouTube配信を引き継ぐセッションは以下を取り込むこと（ブランチ `claude/youtube-monetization-strategy-lxii6n` のコミット `b471a09`）：

| ファイル | 内容 | 取り込み方 |
|---------|------|-----------|
| `_tools/publish/upload_youtube.py` | `status.containsSyntheticMedia=True` を既定申告（VOICEVOX開示の自動化）。`--no-synthetic-disclosure` で解除 | 現行版とは小さな差分。AI開示の数行を当てる |
| `_tools/publish/fetch_analytics.py`（新規） | CTR・維持率・急落地点・流入元を §1 KPIと突合してMarkdown出力（yt-analyst の入力自動化） | ファイルごとコピー可 |
| `_tools/publish/get_refresh_token.py` | `yt-analytics.readonly` スコープを追加（分析ジョブの前提） | スコープ行を当てる＋トークン再取得 |

- 分析ジョブ（§3.2）はこの `fetch_analytics.py` が前提。
- 事業KPI（登録者/総再生時間/YPP進捗）の突合先は `docs/monetization-strategy.md` §4.2。
