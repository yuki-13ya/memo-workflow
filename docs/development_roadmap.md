# 開発ロードマップ

この文書は、`memo-workflow` プロジェクトのPhase構成と境界を管理します。

## 全体方針

`memo-workflow` は、Discordに投稿した雑文メモを取得し、原文を維持したまま整理して、後続処理へ渡す上流プロジェクトです。

Phase 1では、Discord投稿を読み取り専用で取得し、Markdown / JSONとして保存します。

Phase 2では、Phase 1のJSONを入力にし、原文を維持したままトピック分類します。

Phase 2の分類結果は、後続で2つのルートに分岐します。

1つ目は Notionルートです。
雑文、記録、考えたこと、日報的な内容、添付メモなどを、Notionで見返しやすい形に整えます。

2つ目は TODO候補ルートです。
Discord雑文からタスク候補になりそうな内容だけを抽出し、`ticktick-task` 側が受け取れるTODO候補JSONとして出力します。

`memo-workflow` 側では、TickTickへ直接登録、更新、削除しません。
TickTickへの登録、既存TickTickタスクとの統合判定、人間確認CSV、OK済み候補の反映、作業ブロック化、作業ブロック用タスク出力は `ticktick-task` 側の責務とします。

各Phaseでは、前Phaseで確認できた成果だけを前提にします。

## 全体の流れ

```text
Discord
  ↓
Phase 1: 投稿取得
  ↓
outputs/discord_messages_YYYY-MM-DD.json
  ↓
補助基盤: 未処理キュー管理
  ↓
state/discord_message_queue.json
  ↓
Phase 2: 原文維持のトピック分類
  ↓
outputs/topic_classification_YYYY-MM-DD.json
  ↓
分岐

Notionルート:
  Phase 3: Notion貼り付け用Markdown生成
    ↓
  outputs/notion_markdown_YYYY-MM-DD.md
    ↓
  Phase 4: Notion API転記
    ↓
  Notion

TODO候補ルート:
  Phase 5: TickTick入力用TODO候補JSON生成
    ↓
  outputs/ticktick_todo_candidates_YYYY-MM-DD.json
    ↓
  ticktick-task
```

Phase 3 / Phase 4 は Notionルートです。
Phase 5 は TODO候補ルートです。

Discord投稿の進捗管理は、日付別ファイルだけに依存しません。
昼、夜、翌朝、長期間未処理後の回収に対応するため、`message_id` 単位の未処理キューを補助基盤として追加します。

NotionルートとTODO候補ルートは、Phase 2の分類結果を共通入力として使います。
ただし、Notionへ送ることと、`ticktick-task` 側へ渡すことは別の出口として扱い、同じ処理に混ぜません。

## Phase構成

| Phase | 名称 | 概要 | 現在の扱い |
|---|---|---|---|
| Phase 1 | Discord投稿取得 | 指定チャンネルから指定日の投稿を読み取り専用で取得し、Markdown / JSONに保存する | 実データ確認済み |
| 補助基盤 | Discord未処理キュー管理 | Discord投稿を `message_id` 単位で台帳化し、未TODO候補化、レビュー待ち、反映待ちを追跡する | 仕様追加 |
| Phase 2 | AIによる原文維持のトピック分類 | Phase 1のJSONを入力にし、取得した投稿を原文維持のままトピック分類する | 初期実装・実データ分類確認済み |
| Phase 3 | Notion貼り付け用Markdown生成 | Phase 2の分類結果から、Notionに貼り付けやすいMarkdownを生成する | 予定のみ |
| Phase 4 | Notion API転記 | Notionルートで確認済みの内容を、必要に応じてNotion APIで指定先へ登録する | 予定のみ |
| Phase 5 | TickTick入力用TODO候補JSON生成 | Phase 2の分類結果から、`ticktick-task` 側へ渡すTODO候補JSONを生成する | 予定のみ |

## Phase 1の完了条件

Phase 1では、以下を満たすことを目指します。

- Bot Token、Channel ID、Timezoneを環境変数から読める
- 指定チャンネルの取得に成功または失敗理由をログで切り分けられる
- Asia/Tokyo基準で指定日の投稿だけを抽出できる
- 投稿時刻、投稿者名、本文、添付ファイルURLを取得できる
- MarkdownとJSONを `outputs/` に保存できる
- ログを `logs/` に保存できる
- 認証情報やトークンをログ、出力、文書に出さない
- Discordへの投稿、編集、削除を行わない
- AI分類、Notion転記、TODO候補抽出を混ぜない

## Discord未処理キュー管理

未処理キュー管理は、Phase 1で取得したDiscord投稿を `message_id` 単位で台帳化し、後続処理へ渡す対象を決める補助基盤です。

この補助基盤で行うこと:

- 取得済みDiscord投稿を `state/discord_message_queue.json` へ登録する
- 同じ投稿を何度取得しても `message_id` で重複除外する
- 同じ日を再取得した場合、既存日付ファイルへ新規投稿だけをマージする
- 未TODO候補化メッセージだけを抽出し、既存Phase 2 / Phase 5へ渡せるバッチJSONを作る
- TODO候補化済み、レビュー済み、Confirm済み、Execute済みなどの状態を段階的に持てるようにする

この補助基盤で行わないこと:

- Discordへの投稿、編集、削除
- AI分類やTODO候補抽出そのもの
- TickTickへの登録、更新、削除
- キュー状態だけを根拠にした自動反映

詳細は `docs/discord_unprocessed_queue_spec.md` に定義します。

## Phase 2の入口と役割

Phase 2は、Phase 1が出力する `outputs/discord_messages_YYYY-MM-DD.json` を入力にします。

Phase 2では、投稿本文の原文と添付メタデータを維持したまま、トピック分類のための中間データを作ります。

Phase 2の出力は、NotionルートとTODO候補ルートの共通入力です。

Phase 2では、以下を行います。

- Phase 1 JSONを読む
- 投稿本文を原文のまま維持する
- 添付メタデータを維持する
- 辞書照合とAI分類によりトピック単位へ整理する
- `context_label`、`topic_title`、`category`、`flags` などを付ける
- `task_hint` が付いたトピックを、後続のTODO候補ルートで拾える状態にする
- 分類結果JSONと確認用Markdownを出力する

Phase 2では、以下を行いません。

- 投稿本文の書き換え
- Notion貼り付け用Markdownの最終整形
- Notion API転記
- TODO候補JSON生成
- TickTickへの登録
- Discordへの投稿、編集、削除

AI分類の詳細仕様、プロンプト、出力形式は、Phase 2仕様書で定義します。

## Notionルート

Notionルートは、Discordに投稿した雑文、記録、考えたこと、日報的な内容、添付メモなどを、Notionで見返しやすい形にする流れです。

### Phase 3: Notion貼り付け用Markdown生成

Phase 3では、Phase 2の分類結果を入力にし、Notionに貼り付けやすいMarkdownを生成します。

Phase 3で行うこと:

- Phase 2の分類JSONを読む
- トピック単位で見返しやすいMarkdownを生成する
- 原文を失わずに、Notion貼り付け用の表示へ整える
- 添付情報や分類情報を必要な範囲で残す

Phase 3で行わないこと:

- Notion API転記
- TODO候補抽出
- TickTick入力用TODO候補JSON生成
- TickTickへの登録
- Discordへの投稿、編集、削除

### Phase 4: Notion API転記

Phase 4では、Notionルートで確認済みの内容を、必要に応じてNotion APIで指定先へ登録します。

Phase 4で行うこと:

- Phase 3のMarkdownまたはPhase 2の分類JSONを入力にする
- 指定されたNotion登録先へ転記する
- 転記結果ログを残す
- 対象データ、登録先、実行条件を明示する
- DryRunまたは人間確認を挟んでから実行する

Phase 4で行わないこと:

- TODO候補JSON生成
- TickTickへの登録
- `ticktick-task` への受け渡し
- Discordへの投稿、編集、削除

## TODO候補ルート

TODO候補ルートは、Discord雑文からタスク候補になりそうな内容だけを抽出し、`ticktick-task` 側が受け取れるTODO候補JSONとして出力する流れです。

TODO候補ルートでは、TickTick APIへ直接書き込みません。

### Phase 5: TickTick入力用TODO候補JSON生成

Phase 5では、Phase 2の分類結果から、`ticktick-task` 側へ渡すTODO候補JSONを生成します。

Phase 5で行うこと:

- Phase 2の分類JSONを読む
- `task_hint` が付いたトピックを中心に見る
- `context_label`、`topic_title`、元投稿IDを引き継ぐ
- TODO候補を文脈つきで抽出する
- `outputs/ticktick_todo_candidates_YYYY-MM-DD.json` を出力する
- `ticktick-task` 側が受け取れる標準JSONに整える
- 出力JSONが `ticktick-task` 側の入力仕様と照合できる状態か確認する

Phase 5で行わないこと:

- TickTick APIへの登録、更新、削除
- 既存TickTickタスクとの統合判定
- 人間確認CSVの作成
- OK済み候補のTickTick反映
- 作業ブロック化
- 作業ブロック用タスクの出力
- Notion API転記
- Discordへの投稿、編集、削除

Phase 5の出力は、`ticktick-task` 側の入力として扱います。

想定出力:

```text
outputs/ticktick_todo_candidates_YYYY-MM-DD.json
```

このJSONには、TODO候補タイトル、文脈ラベル、元投稿ID、根拠、確認要否、候補ステータスなど、`ticktick-task` 側で統合判定に使う情報を含める方針です。

詳細な項目名と値は、Phase 5仕様書で定義します。

### Phase 5の完了条件

Phase 5では、以下を満たすことを目指します。

- Phase 2の分類JSONを入力として読める
- `task_hint` が付いたトピックを中心にTODO候補を抽出できる
- TODO候補が短いタスク名だけにならず、`context_label`、`topic_title`、元投稿IDを引き継いでいる
- `outputs/ticktick_todo_candidates_YYYY-MM-DD.json` を出力できる
- `ticktick-task` 側の入力仕様に合うJSONを出力できる
- 必須項目が揃っている
- 値の候補が定義済みである
- サンプルJSONで `ticktick-task` 側との受け渡し確認ができている
- TickTick APIへの登録、更新、削除を行っていない
- Notionルートの処理を混ぜていない

## 後続Phaseの安全ルール

### 共通ルール

後続Phaseでは、Phase 1で取得した原文を失わないようにします。

AIが分類、抽出、候補化を行う場合でも、元投稿本文、元投稿ID、投稿時刻、添付メタデータを追跡できる形にします。

AIは判断案、分類案、候補案を返すだけです。
外部サービスへの保存、登録、更新、削除はPythonスクリプト側が制御します。

### Notionルートの安全ルール

Notion API転記は、Phase 4で扱います。

Notionへ送る内容は、Phase 3のMarkdownまたはPhase 2の分類JSONをもとにします。

Notion API転記を行う場合は、対象データ、登録先、実行条件、DryRunまたは人間確認、ログ方針をPhase 4仕様書で定義します。

### TODO候補ルートの安全ルール

Phase 5でタスク候補を抽出する場合は、短いタスク名だけでなく、Phase 2の `context_label`、`topic_title`、元投稿IDを引き継ぎます。

Phase 5では、TODO候補を `ticktick-task` 側へ渡せるJSONとして生成するだけです。

Phase 5では、TickTickへ直接登録しません。

TickTickへの登録、既存TickTickタスクとの統合判定、人間確認、OK済み候補の反映、作業ブロック化は `ticktick-task` 側の責務です。

## Phaseごとの非対象

この節では、各Phaseで混ぜないものを管理します。

ここに書かれた内容は、そのPhaseの境界を示すものであり、後続Phaseで作ることを禁止するものではありません。
ただし、TickTickへの登録、統合判定、人間確認、反映、作業ブロック化は `memo-workflow` 側では扱わず、`ticktick-task` 側の責務として扱います。

| Phase | そのPhaseで作らないもの |
|---|---|
| Phase 1 | AI分類、Notion転記、TODO候補JSON生成、TickTick連携、Discordへの投稿・編集・削除 |
| Phase 2 | Notion貼り付け用Markdownの最終整形、Notion API転記、TODO候補JSON生成、TickTick連携、Discordへの投稿・編集・削除 |
| Phase 3 | Notion API転記、TODO候補JSON生成、TickTick連携、Discordへの投稿・編集・削除 |
| Phase 4 | TODO候補JSON生成、TickTick連携、Discordへの投稿・編集・削除 |
| Phase 5 | TickTickへの登録、既存TickTickタスクとの統合判定、人間確認CSV、OK済み候補のTickTick反映、作業ブロック化、Notion転記、Discordへの投稿・編集・削除 |

Phaseが進んだ後も、過去Phaseで「そのPhaseでは作らなかった」ことは履歴として矛盾しません。

現在の状態は `Phase構成` の表と各Phase仕様書で管理します。

## 今後作成するPhase仕様書

今後、必要に応じて以下のPhase仕様書を作成します。

```text
docs/phase3_notion_markdown.md
docs/phase4_notion_api_export.md
docs/phase5_ticktick_todo_candidates.md
```

各Phase仕様書では、以下を定義します。

- 目的
- 入力
- 出力
- 対象範囲
- 対象外
- 出力項目
- 実行条件
- 例外時の扱い
- ログ方針
- 完了条件

詳細仕様は、各Phaseへ着手する直前に作成します。
