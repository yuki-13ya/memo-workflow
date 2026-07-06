# システム設計図

この文書は、`memo-workflow` の全体像を人間が読みやすい形で整理する設計図です。

Phase仕様書は各部屋の詳細、この文書は家全体の間取りとして扱います。
実装を増やす前に、この設計図とずれていないかを確認します。
ただし、毎回すべてを深掘りするのではなく、作業の影響範囲に応じて確認の深さを調整します。

## 1. このプロジェクトで作るもの

Discordに雑に投稿したメモを、後から見返しやすい形に整理し、Notion向けの記録データと、`ticktick-task` 向けのTODO候補データへ渡せる小さな上流自動化を作ります。

最終的な狙いは、メモを投稿する人間の負担を増やさずに、以下をできるようにすることです。

- Discordに投稿した原文を失わず保存する
- 日付ごとのメモを分類する
- Notionに貼り付けやすい形に整える
- 必要なものだけNotion APIへ転記する
- タスク候補を文脈つきで拾う
- `ticktick-task` 側が受け取れるTODO候補JSONとして出力する

TickTickへの登録、統合判定、人間確認、反映、作業ブロック化は `ticktick-task` 側で扱います。

## 2. 全体の流れ

```text
Discord
  ↓
Phase 1: 投稿取得
  ↓
outputs/discord_messages_YYYY-MM-DD.json
  ↓
補助基盤: message_id単位の未処理キュー
  ↓
state/discord_message_queue.json
  ↓
Phase 2: 辞書照合 + AI分類
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

Phase 2の分類結果から、NotionルートとTODO候補ルートへ分岐します。
Notionルートでは、Discordに投稿した雑文、記録、考えたこと、日報的な内容、添付メモなどを、Notionで見返しやすい形にします。
TODO候補ルートでは、Discord雑文からタスク候補になりそうな内容だけを抽出し、`ticktick-task` 側が受け取れる標準JSONとして出力します。

Discord投稿の進捗管理は、日付だけでなく `message_id` 単位の未処理キューで扱います。
日付別ファイルは人間確認と既存Phase互換のために残し、重複除外、追記分処理、長期間未処理後の回収は `state/discord_message_queue.json` を正として扱います。

Notionルートでは、以下を扱います。

- Phase 2の分類結果を読む
- Notion貼り付け用Markdownを生成する
- 必要に応じてNotion APIへ転記する
- 原文を失わない形で記録として残す

TODO候補ルートでは、以下を扱います。

- Phase 2の分類結果を読む
- `task_hint` が付いたトピックを中心に見る
- `context_label`、`topic_title`、元投稿IDを引き継ぐ
- TODO候補を文脈つきで抽出する
- `outputs/ticktick_todo_candidates_YYYY-MM-DD.json` を作る
- `ticktick-task` 側へ渡せる入力データに整える

```text
memo-workflow 側の責務:
- Discord投稿の取得
- 原文維持のトピック分類
- Notion向けMarkdown生成
- Notion API転記
- ticktick-task向けTODO候補JSON生成

ticktick-task 側の責務:
- TODO候補JSONの受け取り
- 既存TickTickタスクとの統合判定
- 人間確認CSV
- OK済み候補のTickTick反映
- TickTick未完了タスクの作業ブロック分類
- 作業ブロック用タスクのTickTick出力
- Googleカレンダー空き時間参照と配置候補作成に関係するTickTick側処理
```

Phase 4のNotion転記と、Phase 5のTODO候補JSON生成は別の出口として扱います。
Notionへ送ることと、`ticktick-task` 側へ渡すことを同じ処理に混ぜません。
TODO候補ルートでは、TickTickタスク化や作業ブロック化を扱いません。
memo-workflow 側では、TickTickへ直接書き込みません。

`ticktick-task` への受け渡し確認は、Phase 5の完了条件として扱います。

## 3. 処理主体

このプロジェクトでは、誰が何をするかを固定します。

| 主体 | 役割 |
|---|---|
| Codex | 開発支援、仕様整理、コード作成、検証支援 |
| Pythonスクリプト | ファイル読み書き、ログ、辞書照合、外部API操作 |
| 実行時AI | 投稿本文の分類やタスク候補抽出など、文章判断が必要な処理を担当する。Phase 2ではGeminiを第一候補にする |
| 人間 | 辞書、カテゴリ、要確認項目、最終判断 |

Codexはこのプロジェクトを作るための開発パートナーです。
完成後の自動処理で、Codexが分類エンジンとして動く前提にはしません。

実行時AIは、投稿本文の分類やタスク候補抽出など、文章判断が必要な処理で使います。
Phase 2では、既存利用があり、構造化出力を扱えるGeminiを第一候補にします。
ただし、AIがNotionやTickTickへ直接書き込むことはしません。

外部サービスへの読み書きはPythonスクリプトが担当します。
AIは判断案を返し、保存、登録、更新、削除はアプリ側で制御します。

## 4. データの考え方

このプロジェクトでは、前のPhaseの出力を次のPhaseの入力にします。

各Phaseは、入力ファイルを読み、出力ファイルを作る形を基本にします。
これにより、途中で失敗しても、どこまでできたかを確認しやすくします。

| データ | 役割 |
|---|---|
| `outputs/discord_messages_YYYY-MM-DD.json` | Discordから取得した原文と添付情報 |
| `state/discord_message_queue.json` | Discord投稿ごとの取得、TODO候補化、レビュー、反映状態を管理する未処理キュー |
| `config/context_aliases.csv` | 文脈ラベル、別名、関連名、TickTickリスト名候補の辞書 |
| `outputs/topic_classification_YYYY-MM-DD.json` | Phase 2の分類結果 |
| `outputs/notion_markdown_YYYY-MM-DD.md` | Notion貼り付け用Markdown |
| `outputs/ticktick_todo_candidates_YYYY-MM-DD.json` | `ticktick-task` 側へ渡すTODO候補JSON |

原文は、最初に取得したPhase 1 JSONを基準にします。
後続Phaseでは、原文を書き換えず、分類、ラベル、候補を別項目として追加します。
Phase 2出力は、NotionルートとTODO候補ルートの共通入力です。
Notionルートでは記録として残すためのMarkdownやNotion転記に使い、TODO候補ルートでは `ticktick-task` 側へ渡すTODO候補JSONの生成に使います。

日付別処理だけを前提にしないため、未処理キューから未TODO候補化メッセージを抽出したバッチJSONも、Phase 2以降の入力として扱えるようにします。
このバッチJSONは既存のPhase 1出力と同じ `messages[]` 構造を持つものとします。

## 5. 辞書とAIの順番

分類処理では、先に人間が管理する辞書を使います。

1. Pythonが `config/context_aliases.csv` を読む
2. 投稿本文に辞書の正式名、別名、関連名が含まれるか確認する
3. 1件に確定できるものは `context_label` を付ける
4. 複数候補があるものは `needs_review` にする
5. 辞書で決まらない部分だけAI判断に渡す

AIの推測だけで、TickTickリスト名や外部連携先を確定しません。
特にTickTickリスト名は、既存リスト名と完全一致できるものだけ自動連携候補にします。

## 6. Phaseごとの役割

| Phase | 役割 | 主な入力 | 主な出力 | 外部サービスへの書き込み |
|---|---|---|---|---|
| Phase 1 | Discord投稿取得 | Discord API | Discord投稿JSON / Markdown | なし |
| 補助基盤 | Discord未処理キュー管理 | Phase 1取得結果、既存キュー | `state/discord_message_queue.json`、キューバッチJSON | なし |
| Phase 2 | 辞書照合とAI分類 | Phase 1 JSON、辞書CSV | 分類JSON / 確認Markdown | なし |
| Phase 3 | Notion貼り付け用Markdown生成 | Phase 2 JSON | Notion用Markdown | なし |
| Phase 4 | Notion API転記 | Phase 3 MarkdownまたはPhase 2 JSON | Notion登録結果ログ | Notionのみ |
| Phase 5 | TickTick入力用TODO候補JSON生成 | Phase 2 JSON | `ticktick-task` 向けTODO候補JSON | なし |

Phase 2では、Notion転記、TODO候補JSON生成、Discord書き込みを行いません。
Phase 5では、`ticktick-task` 側へ渡すTODO候補JSONを作るだけで、TickTick APIへの登録、更新、削除は行いません。
`ticktick-task` への受け渡し確認は、Phase 5の完了条件として扱います。
TickTickへの登録、統合判定、人間確認、反映、作業ブロック化は `ticktick-task` 側で扱います。

## 7. 実装前の確認ルール

新しい実装を追加する前に、以下を確認します。

- どのPhaseの作業か
- 入力ファイルは何か
- 出力ファイルは何か
- 外部サービスへ読み取りだけか、書き込みもするのか
- AIが判断する範囲はどこか
- Python側で確定する範囲はどこか
- 人間の確認が必要な範囲はどこか
- 認証情報や秘密値を扱うか
- 失敗時にどこで止まったか分かるか

確認の深さは、以下のように分けます。

| 確認レベル | 対象作業 | 確認内容 |
|---|---|---|
| 軽い確認 | 誤字修正、表示文言、既存仕様内の小変更 | 対象ファイルと対象Phaseだけ確認する |
| 通常確認 | 既存Phase内の機能追加、出力項目追加、検証スクリプト追加 | 対象Phase仕様、入出力、関連する設計図の該当箇所を確認する |
| 深い確認 | Phase境界、外部API、AI利用、認証情報、データフロー変更 | `docs/system_design.md`、対象Phase仕様、`docs/app_policy.md` を確認し、必要なら先に設計を更新する |

この確認が曖昧なまま、実装を増やしません。
ただし、未解決事項が今回の作業に直接関係しない場合は、存在するだけで作業を止めません。

## 8. 現時点のプロトタイプの扱い

`topic-classifier/test_context_aliases.py` は、Phase 2本体ではありません。

これは、`config/context_aliases.csv` の形式と、辞書照合の考え方を実データで確認するための検証用スクリプトです。
Phase 2本体を作る場合は、この検証結果を参考にしつつ、Phase 2仕様とこの設計図に沿って整理し直します。

検証用スクリプトを、そのまま完成版の中心処理に昇格させる場合も、先に責務、入力、出力、ログ方針を見直します。

## 9. 未解決事項の扱い

未解決事項、確認事項、判断待ちは `docs/issues.md` に集約します。

この設計図には、確定した全体フロー、処理主体、データ受け渡し、Phase間の関係を記載します。
未確定の詳細をここに直接増やすと、固定の設計と作業中の確認事項が混ざるため、必要な場合は `docs/issues.md` への参照に留めます。

未解決事項は推測で実装せず、判断が確定してから対象Phase仕様書、設計図、ロードマップ、変更履歴へ反映します。
