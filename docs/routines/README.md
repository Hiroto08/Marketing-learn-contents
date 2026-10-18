# 定期ジョブ（Routines）のプロンプト雛形

マーケラボで実際に動いている4本の定期ジョブを、別テーマにそのまま登録できる形にしたもの。
`<基点ブランチ>` を新リポジトリで作業の正とするブランチ名（例 `main`）に置き換えて使う。
シリーズ固有の値（チャンネル・公開曜日・タグ接頭辞など）はプロンプトに書かず、`series.json` から各ツールが読む。

| ファイル | いつ（JST） | cron（UTC） | 何をする |
|---|---|---|---|
| [weekly-upload.md](weekly-upload.md) | 毎週月 9:00 | `0 0 * * 1` | YouTube の公開予約の延長、字幕、再生リスト、メール予約 |
| [weekly-note-drafts.md](weekly-note-drafts.md) | 毎週火 9:00 | `0 0 * * 2` | note 記事2話を仕上げて下書き保存 |
| [weekly-analytics.md](weekly-analytics.md) | 毎週水 9:00 | `0 0 * * 3` | 再生数・登録者・CTR・維持率の週次レポート |
| [daily-note-publish.md](daily-note-publish.md) | 毎日 19:55 | `55 10 * * *` | 予定日の note 記事を公開 |

## 登録のしかた（重要）

- **claude.ai の Routines 画面から、リポジトリを付けて作る。** セッションの中から `create_trigger` で「毎回新しいセッション」方式にすると、リポジトリが付かず git もツールも使えないまま空振りする（2026-10-18 に実際に発生）。
- 環境は、`series.json` に対応する Secrets（`YT_CLIENT_ID` / `YT_CLIENT_SECRET` / `YT_REFRESH_TOKEN` / `_note_session_v5` / `KIT_API_KEY`）を**環境変数**として持つものを選ぶ。Network secrets（API credentials）に入れるとヘッダーの付き方が合わず Kit が 401 になる。
- 通知は push（必要ならメールも）をオン。各ジョブは失敗時に理由を書いて止まるので、通知が「人が見る唯一の窓口」になる。
- 登録後、`python3 _tools/series_doctor.py --online` を1回流して、権限と接続を確認する。
