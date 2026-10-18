# 横展開プレイブック：別テーマで同じ自動運用を立ち上げる

マーケラボ（AI時代のマーケティング・ラボ）で作った「動画を作る → YouTube に週2本予約公開 → note 記事を毎日公開 → メルマガを動画と同時刻に送る → 毎週数字を見る」の仕組みを、別テーマのチャンネルでそのまま使うための手順書。

- 対象：新しいテーマ（例：経理、採用、英語学習）で、同じ形式の講座チャンネルを立ち上げる人と、その作業をする Claude のセッション。
- 前提：このリポジトリを複製して使う。ツールは共通、テーマ固有の値は `series.json` と各話のディレクトリにだけ置く。

## 1. 仕組みの全体像

```
[制作]  docs/episode-briefs.md（全N話の企画）
          └→ episode-production スキル（台本 → スライド → QA）
               └→ run_episode.sh / run_shorts.sh（VOICEVOX でナレーション → 動画化 → 非公開アップ）
[配信]  publish_episode.py --schedule-all … EP順・本編＋Shorts同時刻で公開予約（series.json の曜日・時刻）
          ├→ upload_captions.py（台本から日本語字幕） ├→ sync_playlists.py（全話・章別・Shortsまとめ）
          └→ make_broadcast.py → schedule_kit_broadcasts.py（Kit に動画と同時刻のメール予約）
[記事]  make_note_article.py → note-production スキル（校了）→ post_note_api.py（下書き → 公開）
          └→ note_cta.py（記事に動画埋め込み・章の時刻リンク・再生リスト・登録・次の回を自動挿入）
[計測]  weekly_stats.py（再生・登録の前週比） ＋ fetch_analytics.py（CTR・維持率）→ スキルのルールに書き戻し
[状態]  docs/upload-status.md（YouTube実体から生成）／ _deliverables/note/note-draft-status.md ／ note-publish-schedule.md
[運転]  定期ジョブ4本（docs/routines/）＋ 手順書 docs/autonomous-operation.md
```

回の識別は、動画に付ける見えないタグ（`<tag_prefix>-ep09`、Short は `<tag_prefix>-ep09-s1`）で行う。タイトルに「第N回」を入れなくても、どの回の動画かを機械が判定できる。

## 2. 部品の分類

| 分類 | 何 | 横展開でやること |
|---|---|---|
| **そのまま使う** | `_tools/` の全ツール（制作・配信・note・Kit・計測）、`yt-*`・`note-*` のロールスキル、検査（verify_*）、パイプライン（run_*.sh）、動画エンジン（slide.html の型・make_video.py）、定期ジョブの雛形 | 何もしない |
| **設定で切り替える** | チャンネルID、シリーズ名、タグ接頭辞、話数、公開曜日・時刻、note のユーザー名、Kit の特典URL、再生リスト、チャンネル説明文、ナレーションの声 | `series.json` を書き換える（§3） |
| **中身を作り直す** | 全話の企画（`docs/episode-briefs.md`）、各話のディレクトリ（`0*/epNN_*`）、`episode-production` スキル内のテーマ別の例と禁止事項、特典PDFの中身、収益化・メルマガ計画（`docs/monetization-strategy.md` ほか） | 新テーマ用に書く（§4 Step 5） |
| **作り直さない（消す）** | 旧テーマの成果物：`_deliverables/`、`docs/upload-status.md`、`docs/stats/`、`docs/shorts-related-video-checklist.md`、各話の `publish_manifest.json` | 複製後に削除（§4 Step 1） |

## 3. series.json

雛形は `_template/series.template.json`。主な項目：

| 項目 | 意味 | 例（マーケラボ） |
|---|---|---|
| `series_name` | チャンネル名。メール・記事・サムネに入る | AI時代のマーケティング・ラボ |
| `tag_prefix` | 動画の識別タグの接頭辞。**他シリーズと重複させない** | mlab |
| `total_episodes` | 全話数 | 24 |
| `schedule.days` / `youtube_hour_jst` | 動画の公開曜日と時刻 | ["wed","sat"] / 18 |
| `schedule.note_hour_jst` | note 記事の公開時刻 | 20 |
| `youtube.channel_id` | UC で始まるチャンネルID | UCZm9m37… |
| `youtube.master_playlist_id` | 全話の再生リストID（`sync_playlists.py` 実行後に入れる） | PLazN5XmDSQHo |
| `youtube.channel_description` / `channel_keywords` | チャンネル説明（1000字以内）とキーワード（500字以内） | — |
| `youtube.playlists` | 再生リストの定義（タイトル・説明・対象EP範囲・main/shorts） | 全話＋章別6本＋Shorts |
| `note.urlname` | note のユーザー名 | marketing_lab_jp |
| `kit.optin_url` / `lead_magnet` | Kit の特典LPと特典名 | — |
| `voice.speaker_id` / `speaker_name` | VOICEVOX の話者（概要欄のクレジットにも入る） | 11 / 玄野武宏 |

書いたら `python3 _tools/series_doctor.py` で抜け・範囲外・文字数を確認する。

## 4. 立ち上げ手順

### Step 1　リポジトリを複製する
1. GitHub で新しいリポジトリを作り、このリポジトリの基点ブランチ（現在は `claude/build-upload-bqpddd`）の内容を丸ごと入れる（「Use this template」か、clone → 新リモートへ push）。
2. 旧テーマの成果物を消す：`0*/ep*`（各話）、`_deliverables/`、`docs/upload-status.md`、`docs/stats/`、`docs/weekly-stats.md`、`docs/shorts-related-video-checklist.md`、`_factcheck/`。
3. `series.json` を `_template/series.template.json` から作り直す。
4. CLAUDE.md の冒頭（チャンネル名・ディレクトリ構成）を新テーマに合わせる。

### Step 2　YouTube（Google Cloud）
1. YouTube チャンネルを作る（ブランドアカウント推奨）。チャンネルIDを `series.json` へ。
2. Google Cloud でプロジェクトを作り、**YouTube Data API v3** と **YouTube Analytics API** を有効化。
3. OAuth 同意画面：外部、テストユーザーに自分を追加 → **「本番環境に公開」へ切り替える**（テストのままだとリフレッシュトークンが7日で切れる）。
4. 認証情報 → OAuth クライアントID（種類：デスクトップアプリ）。
5. 手元のPCで `python3 _tools/publish/get_refresh_token.py <ID> <SECRET>` → 権限は**全部にチェック**（アップロード・管理・字幕〈force-ssl〉・アナリティクス）。

### Step 3　note と Kit
- **note**：アカウントを作る。ブラウザでログインし、Cookie `_note_session_v5` の値を控える（開発者ツール → Application → Cookies → note.com）。期限が切れたら同じ手順で更新。
- **Kit**：アカウント、特典LP（フォーム）、送信元アドレスの確認、住所（Physical address）を設定。Settings → Developer で v4 API キーを作る。

### Step 4　Claude の環境（claude.ai/code）
1. 環境の設定（セッション上部の環境メニュー → Edit）で **Environment variables** に入れる：
   `YT_CLIENT_ID` / `YT_CLIENT_SECRET` / `YT_REFRESH_TOKEN` / `_note_session_v5` / `KIT_API_KEY`
   （**Network secrets ではなく環境変数**。Network secrets だと Kit は認証方式が合わず 401 になる）
2. ネットワーク：`api.kit.com`、`note.com`、`editor.note.com`、`*.googleapis.com`、`accounts.google.com`、`assets.st-note.com` に出られること。
3. 新しいセッションで `bash _tools/setup_env.sh`（ffmpeg・フォント・VOICEVOX）→ `python3 _tools/series_doctor.py --online` が「問題なし」になるまで直す。

### Step 5　コンテンツを設計する
1. `docs/episode-briefs.md` に全N話の企画（各話のテーマ・実話の事例・学びの約束）を書く。`yt-producer`・`yt-researcher` スキルが手伝える。
2. `.claude/skills/episode-production/` のテーマ別の例（マーケの実例・用語）を新テーマに置き換える。18枚構成・維持率の型（retention-packaging.md）はテーマに依存しないので残す。
3. `_template/`（script.md・description.md・thumbnail.md）の例文を新テーマに合わせる。

### Step 6　最初の回を作る
- セッションで「EP01を作って」→ 制作・QA・非公開アップ・Shorts まで自動（CLAUDE.md の短い指示規約）。
- 動画のアップロードは1日6本まで（1本1,600単位、1日約10,000単位、16:00 JST にリセット）。ストックを貯めてから公開予約を始める。
- 数話たまったら `python3 _tools/publish/sync_playlists.py` → 作られた全話の再生リストIDを `series.json` の `master_playlist_id` に入れる。`update_channel_branding.py` でチャンネル説明を反映。

### Step 7　定期ジョブを登録する
- `docs/routines/` の4本を、**claude.ai の Routines 画面からリポジトリ付きで**登録する（`<基点ブランチ>` を置き換え）。
- note の公開スケジュールは `python3 _tools/publish/note_publish_schedule.py --start <最初の日>` で作る。

### Step 8　初週の確認
- 月曜の配信ジョブの通知で、公開予約カレンダーと Kit 予約を確認。
- 公開のたびに、Studio で各 Short の「関連動画」に本編を設定（API なし。チェックリストは `upload-status.md` から作れる）。

## 5. 運用で実際に起きた問題と、組み込み済みの対策

| 起きたこと | 対策（今の仕組み） |
|---|---|
| 公開の順番が飛んだ（EP8 の次に EP20 が公開） | `publish_episode.py` が EP順以外の公開・予約を拒否。本編が失敗したら Shorts も動かさない |
| 古い状態表を見てジョブが止まる／二重アップ | 状態は毎回 YouTube の実体からタグで判定（`gen_upload_status.py`）。全ジョブが同じ基点ブランチを読み、終わったら書き戻す |
| 一度公開した動画は公開予約（publishAt）が使えない | `--schedule-all` が `TIMED` と表示 → その時刻に `--episode` で即時公開する単発の予定を入れる |
| セッションから作った定期ジョブが空振り（リポジトリ無し） | 定期ジョブは Routines 画面でリポジトリ付きで作る（または運用セッションに紐づける） |
| Kit が 401 | キーは Network secrets ではなく環境変数 `KIT_API_KEY`（ヘッダー `X-Kit-Api-Key` で送る） |
| 字幕・アナリティクスが 403 | OAuth の権限に `youtube.force-ssl` と `yt-analytics.readonly` を含めて再認可 |
| note に公式APIが無い | 実際のブラウザ操作の記録（HAR）と editor のコードで確定した手順だけを使う。失敗時は推測で直さず停止 |
| 記事の動画リンクが非公開で切れる | note は同じ回の動画が公開された後にしか公開しない |
| Shorts から本編へ人が流れない | Shorts の「関連動画」設定（Studio のみ）、Shorts まとめ再生リスト、note・メールの末尾導線 |
| タイトルの「第N回」で検索に弱い | タイトルから外し、回の識別はタグで行う |

## 6. まだテーマ固有のまま残っているもの

- `episode-production` スキル内の例文・用語・禁止事項（Step 5 で書き換え）。
- 特典PDFの見出し（`make_lead_magnet.py` の「マーケティング超入門」）と、メール・記事の文面の言い回し。
- サムネイル・note 見出し画像のデザイン（配色は `series.json` の `brand.bg_color` を持っているが、CSS 側はまだ固定色）。
- `docs/autonomous-operation.md` の運用履歴（マーケラボの実例。新テーマでは §1〜§3 の手順部分だけ使う）。
