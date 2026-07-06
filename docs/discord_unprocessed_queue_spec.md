# Discord未処理キュー追加仕様

この文書は、Discord投稿を日付単位だけでなく、未処理メッセージ単位で扱うための追加仕様です。

## 目的

毎日決まった時刻に処理できない運用でも、Discordに投稿済みのメモを取りこぼさず、重複処理せず、後続のTODO候補ルートへ渡せるようにします。

この仕様では、日付を処理の主キーにしません。
処理状態の主キーはDiscordの `message_id` とします。

日付は、取得範囲、表示、絞り込み、出力ファイル名のために使います。

## 背景

従来のPhase 1は、指定日のDiscord投稿を取得し、以下のファイルへ保存します。

```text
outputs/discord_messages_YYYY-MM-DD.json
outputs/discord_messages_YYYY-MM-DD.md
```

この方式は、日次で安定して処理できる場合は扱いやすいです。

一方で、実運用では以下が起きます。

- 昼に一度処理し、夜に追記分だけ処理したい
- 翌朝に前日の追記分を処理したい
- 1週間または1か月処理できないことがある
- 放置期間が長くても、実際の投稿日は数日分だけの場合がある
- 取得済み、TODO候補化済み、レビュー済み、反映済みが同じ状態とは限らない

そのため、日付ファイルだけで進捗を判断せず、Discord投稿ごとに状態を持つキューを追加します。

## 基本方針

Discord APIの読み取りは、指定範囲または必要範囲をまとめて取得してよいものとします。

取得後、ローカル側で `message_id` を使って重複除外します。

同じDiscord投稿は、何度取得してもキュー内では1件として扱います。

後続処理は、日付ではなく、キュー内の状態を見て対象を選びます。

```text
Discord投稿取得
  ↓
message_idでキューへ登録または更新
  ↓
未TODO候補化メッセージだけ抽出
  ↓
Phase 2 / Phase 5 既存フローへ渡す
  ↓
レビュー、Confirm、Executeの進捗を状態として記録
```

## 管理ファイル

キューの正本は以下に置きます。

```text
state/discord_message_queue.json
```

`state/` は、ローカル運用状態を管理する場所です。
認証情報や秘密値は置きません。

Discord取得スクリプトからキューを更新する場合は、以下のオプションを使います。

```powershell
python discord-ingest/ingest_discord.py --merge-existing --update-queue
```

`--merge-existing` は、既存の日付別JSONを `message_id` で統合します。

`--update-queue` は、取得結果を `state/discord_message_queue.json` に登録または更新します。

キュー保存先を変更する場合は `--queue-path path\to\discord_message_queue.json` を使います。

## キューJSON構造

トップレベル:

```json
{
  "schemaVersion": "1.0",
  "updatedAt": "2026-07-04T09:00:00+09:00",
  "messages": {
    "discord_message_id": {
      "messageId": "discord_message_id",
      "createdAt": "2026-07-04T00:10:00+00:00",
      "createdAtLocal": "2026-07-04T09:10:00+09:00",
      "localDate": "2026-07-04",
      "authorName": "Namba",
      "contentHash": "sha256...",
      "attachmentCount": 0,
      "statuses": {
        "fetched": true,
        "todoCandidateGenerated": false,
        "reviewed": false,
        "confirmed": false,
        "executed": false,
        "ignored": false,
        "held": false
      },
      "files": {
        "discordMessagesFile": "outputs/discord_messages_2026-07-04.json",
        "todoCandidatesFile": "",
        "reviewedFile": "",
        "executedFile": ""
      },
      "lastError": "",
      "updatedAt": "2026-07-04T09:00:00+09:00"
    }
  }
}
```

## 状態の意味

| 状態 | 意味 |
|---|---|
| `fetched` | Discordから読み取り、キューに登録済み |
| `todoCandidateGenerated` | TODO候補生成の入力として処理済み |
| `reviewed` | `ticktick-task` 側のレビュー結果に含まれた |
| `confirmed` | TickTick書き込みConfirm済み |
| `executed` | TickTick反映済み |
| `ignored` | TODO候補化または反映対象から除外すると判断済み |
| `held` | 判断保留。後で再確認する |

状態は排他的ではありません。
たとえば、`reviewed = true` かつ `executed = false` は、レビュー済みだが未反映の状態です。

## 取得範囲

取得範囲は、以下の指定を想定します。

```text
--date YYYY-MM-DD
--from YYYY-MM-DD --to YYYY-MM-DD
--since-last-fetch
```

初期実装では、`--date` または `--from` / `--to` の指定を優先します。

`--since-last-fetch` は、キュー内の最大 `message_id` または最大 `createdAt` を参考にして取得範囲を決めます。
ただし、取りこぼしを避けるため、境界付近は重複取得してよいものとします。
重複はローカルの `message_id` で除外します。

## 既存日付ファイルとの関係

既存の `outputs/discord_messages_YYYY-MM-DD.json` は維持します。

キュー導入後も、日付別ファイルは人間確認、再実行、後続Phaseとの互換のために残します。

同じ日を再取得した場合は、既存日付ファイルと新規取得結果を `message_id` でマージします。

マージ時の方針:

- 同じ `message_id` は1件にする
- 新規メッセージは追加する
- 既存メッセージの本文や添付メタデータが変わっていた場合は、本文を自動上書きせず確認用ログに残す
- 添付ファイル本体は既存のPhase 1方針どおり、同名ファイルがあれば再ダウンロードしない

日付別JSONには、マージ結果の確認用に `merge_summary` を含めます。

## 後続Phaseへの渡し方

初期実装では、既存のPhase 2 / Phase 5を大きく変更しません。

まず、キューから未TODO候補化メッセージを抽出し、一時的な日付または範囲別JSONを作って既存フローへ渡します。

想定出力:

```text
outputs/discord_messages_queue_batch_YYYYMMDD_HHMMSS.json
outputs/discord_messages_queue_batch_YYYYMMDD_HHMMSS.md
```

このバッチJSONは、Phase 1の `discord_messages_YYYY-MM-DD.json` と同じ `messages[]` 構造を持ちます。

バッチJSONの生成だけでは、キュー上の `todoCandidateGenerated` は変更しません。

後続Phaseで正常にTODO候補化できたメッセージは、Phase 5のTODO候補JSON、または元バッチJSONを指定して、明示的にキュー上の `todoCandidateGenerated = true` にします。

実行例:

```powershell
python discord-ingest/queue_batch.py export-pending
python discord-ingest/queue_batch.py mark-todo-generated --source-file outputs\todo_candidates_YYYY-MM-DD.json
```

## TickTick側の進捗反映

`memo-workflow` はTickTickへ直接書き込みません。

ただし、`ticktick-task` 側のレビュー済み、Confirm済み、Execute済みレポートを読み、元Discord `message_id` に対応するキュー状態を更新する補助処理は、出力形式が安定してから検討します。

初期実装では、少なくとも `todoCandidateGenerated` までを `memo-workflow` 側で管理します。

`reviewed`、`confirmed`、`executed` の同期は、`ticktick-task` 側の出力形式が安定してから追加します。

## UI運用

将来的なローカルアプリでは、以下の入口を想定します。

```text
未処理を取得
未TODO候補化を処理
レビュー待ちを開く
反映待ちを確認
```

日付フィルタは補助機能として扱います。

想定フィルタ:

- 今日
- 昨日
- 過去7日
- 未TODO候補化
- レビュー待ち
- 反映待ち
- 保留

## エラー時の扱い

途中で失敗しても、成功済みの状態を失わないようにします。

- Discord取得に失敗した場合、キューは更新しない
- 一部メッセージの添付保存に失敗した場合、メッセージ自体は `fetched = true` とし、添付側に失敗状態を残す
- TODO候補化に失敗した場合、該当メッセージの `todoCandidateGenerated` は `false` のままにする
- エラー内容は `lastError` とログへ残す

## この仕様で行わないこと

- Discordへの投稿、編集、削除
- Notion転記
- TickTickへの登録、更新、削除
- AIによる自動確定
- キュー状態だけを根拠にした自動Execute

## 初期実装の最小範囲

最初に実装する範囲:

1. `state/discord_message_queue.json` を作成、読み込み、保存できる
2. Discord取得結果を `message_id` でキューへ登録できる
3. 同じ日を再取得しても重複登録しない
4. 既存日付ファイルへ `message_id` ベースでマージできる
5. 未TODO候補化メッセージだけをバッチJSONへ出力できる
6. Phase 5のTODO候補JSON、または元バッチJSONを根拠に、対象メッセージを `todoCandidateGenerated = true` にできる

後続で追加する範囲:

- `ticktick-task` 側レビュー結果から `reviewed` を更新する
- Confirm結果から `confirmed` を更新する
- Execute結果から `executed` を更新する
- ローカルUIでキュー状態を一覧、フィルタ表示する
