# Phase 1: Discord投稿取得

この文書は、Phase 1で実装するDiscord投稿取得の仕様を定義します。

## 目的

Discordの指定チャンネルに投稿されたメモを、読み取り専用で取得し、後続Phaseで扱えるローカルファイルとして保存します。

Phase 1では、Discordから取得した内容を分類、要約、転記、タスク化しません。

## 対象範囲

Phase 1で行うこと:

- Discord Bot Tokenを使ってDiscord APIへ接続する
- 環境変数で指定されたチャンネルを読み取る
- Asia/Tokyo基準で指定日の投稿だけを抽出する
- 投稿時刻、投稿者名、本文、添付情報を取得する
- 画像、動画、PDFの添付ファイルをローカル保存する
- MarkdownとJSONを `outputs/` に保存する
- 処理ログを `logs/` に保存する
- 読み取り専用またはDryRun相当の検証として実行する

Phase 1で行わないこと:

- AI分類
- Notion転記
- TickTick登録
- Discordへの投稿、編集、削除
- 投稿本文の要約、整形、意味づけ
- 認証情報やトークンの作成、保存

## 入力

必要な設定は環境変数から読みます。

| 環境変数名 | 役割 |
|---|---|
| `DISCORD_BOT_TOKEN` | Discord Bot Token |
| `DISCORD_CHANNEL_ID` | 取得対象のDiscordチャンネルID |
| `MEMO_WORKFLOW_TIMEZONE` | 日付抽出に使うタイムゾーン。Phase 1では `Asia/Tokyo` を想定 |
| `MEMO_WORKFLOW_TARGET_DATE` | 取得対象日。形式は `YYYY-MM-DD`。空の場合は指定タイムゾーン基準の今日を使う |

`.env.example` には環境変数名だけを記載し、実際の値は記載しません。

## 実装ファイル

Phase 1の最小実装は `discord-ingest/ingest_discord.py` に置きます。

実行時に外部の `.env` を使う場合は、`--env-file` で読み取り専用の参照先を指定します。
スクリプト内に認証情報置き場の固定パスは書きません。

実行例:

```powershell
python discord-ingest/ingest_discord.py --env-file path\to\.env --dry-run
```

`--dry-run` はDiscord APIの読み取り確認を行い、Markdown / JSONファイルは保存しません。

同じ日を再取得し、既存の日付別JSONへ追記分を統合する場合は `--merge-existing` を使います。

```powershell
python discord-ingest/ingest_discord.py --env-file path\to\.env --merge-existing
```

取得済みメッセージを未処理キューにも登録する場合は `--update-queue` を併用します。

```powershell
python discord-ingest/ingest_discord.py --env-file path\to\.env --merge-existing --update-queue
```

キューの保存先を変える場合は `--queue-path` で指定します。

## 日付抽出方針

Discordの投稿時刻はAPIから取得できる時刻を基準にします。

Phase 1では、取得した投稿時刻を `MEMO_WORKFLOW_TIMEZONE` のタイムゾーンへ変換し、対象日と一致する投稿だけを対象にします。

`MEMO_WORKFLOW_TARGET_DATE` に値がある場合は、その日付を対象日にします。
`MEMO_WORKFLOW_TARGET_DATE` が空の場合は、`MEMO_WORKFLOW_TIMEZONE` 基準の今日を対象日にします。

ログには、対象日が環境変数から決まったのか、空欄のため今日にしたのかが分かる情報だけを残します。

日付境界は、Asia/Tokyo基準の `00:00:00` 以上、翌日 `00:00:00` 未満とします。

実装時は、UTCとローカル日付の混同を避けるため、ログには処理段階として「日付抽出」を分けて記録します。

## 取得項目

投稿ごとに以下を取得します。

| 項目 | 内容 |
|---|---|
| `message_id` | DiscordメッセージID |
| `created_at` | Discord APIから取得した投稿時刻 |
| `created_at_local` | 指定タイムゾーンに変換した投稿時刻 |
| `author_name` | 投稿者名 |
| `content` | 投稿本文 |
| `attachment_urls` | 保存対象添付の元URL一覧 |
| `attachments` | 添付ファイルのメタデータ、保存状態、保存先 |

投稿本文は原文を維持します。AIによる補正、分類、要約は行いません。

## 添付ファイルの扱い

Discord直添付は、雑メモとして直接投稿されやすい画像、動画、PDFだけを保存対象にします。

保存対象:

- 画像: `image/*`
- 動画: `video/*`
- PDF: `application/pdf`

保存対象外:

- Word / Excel / PowerPointなどのOfficeファイル
- zip
- exe
- その他不明な形式

保存対象外の添付はファイル本体を保存しません。
JSONには、ファイル名、content type、サイズ、`download_status: "skipped"`、`skip_reason: "unsupported_content_type"` を残します。

同じ日を再実行した場合、同じ保存名の添付ファイルが既にあるものは再ダウンロードしません。
保存名は `message_id_attachment_id_元ファイル名` とし、既存ファイルは取得済みとして扱います。
添付ファイル本体の上書きや差分判定はPhase 1では行いません。

Google Driveなどの外部リンクは本文内URLとして保存し、リンク先の自動取得やダウンロードは行いません。

Phase 1では、保存した添付ファイルの中身を解析しません。
OCR、PDF読解、動画解析、AI分類は後続Phaseで扱います。

## 出力

出力先は `outputs/` とします。

想定ファイル名:

- `outputs/discord_messages_YYYY-MM-DD.md`
- `outputs/discord_messages_YYYY-MM-DD.json`
- `outputs/attachments/YYYY-MM-DD/`

Markdownは人間が確認しやすい形式、JSONは後続Phaseが機械的に読みやすい形式として扱います。

JSONには、取得日時、対象チャンネルID、対象日、タイムゾーン、メッセージ一覧、添付メタデータを含めます。

`--merge-existing` を指定した場合、同じ `outputs/discord_messages_YYYY-MM-DD.json` が既にあれば `message_id` をキーに統合します。
同じ `message_id` の本文や添付メタデータが変わっている場合、既存JSONの本文を自動上書きせず、`merge_summary.changed_existing_count` とログに件数を残します。

`--update-queue` を指定した場合、取得結果を `state/discord_message_queue.json` に登録または更新します。
キューはローカル状態管理であり、Git管理対象の実データにはしません。

## Phase 1出力JSON仕様

後続Phaseは、Phase 1が出力した `outputs/discord_messages_YYYY-MM-DD.json` を入力として扱います。

同日再取得、追記分処理、長期間未処理後の回収は、日付ファイルだけで判断しません。
`message_id` 単位の未処理キュー管理は [Discord未処理キュー追加仕様](discord_unprocessed_queue_spec.md) で扱います。

トップレベルの主な項目:

| 項目 | 内容 |
|---|---|
| `generated_at` | Phase 1出力を生成したUTC時刻 |
| `channel_id` | 取得対象チャンネルID |
| `channel_name` | 取得対象チャンネル名 |
| `target_date` | 抽出対象日。形式は `YYYY-MM-DD` |
| `target_date_source` | 対象日の決定元。`env` または `default_today` |
| `timezone` | 日付抽出に使ったタイムゾーン |
| `message_count` | `messages` の件数 |
| `messages` | 抽出した投稿一覧 |

`messages[]` の主な項目:

| 項目 | 内容 |
|---|---|
| `message_id` | DiscordメッセージID |
| `created_at` | Discord APIから取得したUTC時刻 |
| `created_at_local` | `timezone` に変換した投稿時刻 |
| `author_name` | 投稿者名 |
| `content` | 投稿本文。本文なしの場合は空文字 |
| `attachment_urls` | 保存対象添付の元URL一覧。長期参照先ではなく取得時の参考情報 |
| `attachments` | 添付ファイルのメタデータ一覧 |

`attachments[]` の主な項目:

| 項目 | 内容 |
|---|---|
| `attachment_id` | Discord添付ID |
| `filename` | Discord上の元ファイル名 |
| `content_type` | Discord APIから取得したcontent type |
| `size` | Discord APIから取得したサイズ |
| `download_status` | `downloaded`、`already_exists`、`skipped`、`failed` のいずれか |
| `local_path` | 保存対象添付のローカル保存先。未保存の場合は存在しない、または `null` |
| `skip_reason` | `skipped` の理由 |
| `download_error` | `failed` のエラー種別 |

後続Phaseでは、`content` と `attachments[].local_path` を主な入力として扱います。
`attachment_urls` はDiscord CDNの期限や状態に依存するため、長期参照の前提にしません。

## ログ

ログ出力先は `logs/` とします。

想定ファイル名:

- `logs/discord_ingest_YYYY-MM-DD.log`

失敗時は、以下のどこで失敗したか分かるように記録します。

- 環境変数の読み込み
- 認証
- チャンネル取得
- メッセージ取得
- 日付抽出
- 添付ファイル保存
- 出力保存
- キュー更新

ログには、Bot Token、認証情報、秘密値を出しません。

投稿本文をログに出す場合は最小限にし、通常は件数、メッセージID、処理段階を中心に記録します。

## DryRun / 読み取り専用検証

Phase 1の検証は読み取り専用で行います。

Discord APIに対して、投稿、編集、削除、リアクション追加、チャンネル設定変更を行いません。

DryRun相当の確認では、以下を確認できればよいものとします。

- 環境変数を読み込める
- Discord APIの認証結果を確認できる
- 対象チャンネルにアクセスできる
- 対象日の投稿件数を取得できる
- 出力予定のMarkdown / JSON構造を確認できる

実装時にDryRunオプションを設ける場合は、外部への書き込み操作が存在しないことを前提に、ファイル保存を行うかどうかだけを切り替える形を基本とします。

`--dry-run` でも、接続確認と件数確認のためDiscord APIの読み取りは行います。
Discordへの書き込み操作は行いません。

## 例外時の扱い

| 失敗箇所 | ログに残す内容 | 秘密情報の扱い |
|---|---|---|
| 環境変数不足 | 不足している環境変数名 | 値は出さない |
| 対象日未指定 | 指定タイムゾーン基準の今日を対象日にしたこと | 環境変数の値は出さない |
| 認証失敗 | 認証失敗の段階とエラー種別 | Tokenは出さない |
| チャンネル取得失敗 | チャンネルIDの取得失敗 | Tokenは出さない |
| メッセージ取得失敗 | API取得失敗の段階 | Tokenは出さない |
| 日付抽出失敗 | 対象日、タイムゾーン、変換処理の失敗 | 投稿本文の過剰出力を避ける |
| 添付保存失敗 | メッセージID、添付ID、保存失敗の種別 | URLや秘密値の過剰出力を避ける |
| 添付既存スキップ | メッセージID、添付ID、既存ファイル利用 | URLや秘密値は出さない |
| 出力保存失敗 | 保存先パス、ファイル種別 | 秘密値を含めない |

## 完了条件

Phase 1は、以下を満たした時点で完了候補とします。

- 指定チャンネルから読み取り専用で投稿を取得できる
- Asia/Tokyo基準で指定日の投稿だけを抽出できる
- Markdown / JSONを保存できる
- 画像、動画、PDFの添付を保存できる
- 保存対象外の添付をスキップとして記録できる
- 失敗箇所をログで切り分けられる
- 認証情報やトークンがログ、出力、文書に含まれない
- Phase 2以降の処理を混ぜていない

## Phase 1確認状況

2026-06-28時点の確認状況です。

| 項目 | 状況 | 確認内容 |
|---|---|---|
| Discord Bot TokenでAPI接続 | 確認済み | Bot認証に成功 |
| 環境変数読み込み | 確認済み | 外部 `.env` を `--env-file` で読み込み |
| `MEMO_WORKFLOW_TARGET_DATE` 空欄時の対象日決定 | 確認済み | Asia/Tokyo基準の今日を対象日にした |
| `MEMO_WORKFLOW_TARGET_DATE` 明示時の対象日決定 | 確認済み | `2026-06-27` を明示指定して再取得 |
| 指定チャンネル取得 | 確認済み | 対象チャンネルへのアクセスに成功 |
| 指定日の投稿抽出 | 確認済み | `2026-06-27` の投稿8件を抽出 |
| 投稿時刻取得 | 確認済み | UTCとAsia/Tokyo変換後の時刻をJSONに保存 |
| 投稿者名取得 | 確認済み | Markdown / JSONに保存 |
| 本文取得 | 確認済み | 原文をMarkdown / JSONに保存 |
| 添付メタデータ取得 | 確認済み | filename、content_type、size、download_status、local_pathをJSONに保存 |
| 画像添付保存 | 確認済み | jpg 1件を `outputs/attachments/2026-06-27/` に保存 |
| 動画添付保存 | 確認済み | mov 1件を `outputs/attachments/2026-06-27/` に保存 |
| PDF添付保存 | 確認済み | pdf 2件を `outputs/attachments/2026-06-27/` に保存 |
| Office添付スキップ | 確認済み | docx 1件、xlsx 1件を `skipped` として記録 |
| 既存添付の再取得スキップ | 確認済み | 同じ保存名の画像、動画、PDFを `already_exists` として記録 |
| Markdown出力 | 確認済み | `outputs/discord_messages_2026-06-27.md` を保存 |
| JSON出力 | 確認済み | `outputs/discord_messages_2026-06-27.json` を保存 |
| ログ出力 | 確認済み | `logs/discord_ingest_2026-06-27.log` を保存 |
| DryRun | 確認済み | Discord読み取り確認のみ行い、Markdown / JSONを保存しない |
| 秘密情報の混入防止 | 確認済み | Token、外部 `.env` パス、認証情報の混入チェックで該当なし |
| Discordへの投稿・編集・削除をしない | 確認済み | 実装なし |
| AI分類 | 対象外 | Phase 2以降で扱う |
| Notion転記 | 対象外 | Phase 4以降で扱う |
| TODO候補JSON生成 | 対象外 | Phase 5で扱う |
| 添付ファイル本体破損時の自動修復 | Phase 1対象外 | 既存ファイルは取得済みとして扱い、差分判定や上書きは行わない |

未確認事項、確認待ち、判断待ちは `docs/issues.md` で管理します。
