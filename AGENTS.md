# AGENTS.md

このファイルは、Codexが `memo-workflow` プロジェクト内で作業するときに守るルールをまとめたものです。

## 1. 基本方針

このプロジェクトでは、Discordに投稿されたメモを段階的に取得、整理し、後続処理へ渡せる形にします。

`memo-workflow` は、Discord投稿を取得し、原文を維持したまま分類し、Notion向けの記録データと、`ticktick-task` 向けのTODO候補データへ分岐させる上流プロジェクトです。

作業はPhase単位で進めます。

指定されたPhaseまたは対象作業の範囲を超えて、実装や文書整理を広げません。

短期的な動作確認だけでなく、後から人間が読んで修正できる文書構成、設定管理、ログ方針、Phase境界を優先します。

### 未決定事項と仕様の扱い

- 未決定事項は推測で補完しません。
- 正本仕様書に存在しない要件を、実装時に追加しません。
- 実装に必要な仕様が未決定の場合は実装を止め、未解決事項または確認事項として提示します。
- 「こうした方がよい」という提案と、ユーザーが決定して正本へ反映した仕様を明確に区別します。提案だけを根拠に実装しません。

仕様として確定した内容は、対象Phaseの正本文書へ反映します。提案、検討案、参考文書、未解決事項は、決定済み仕様として扱いません。

## 2. プロジェクト責務

`memo-workflow` 側の責務は、以下です。

- Discord投稿の取得
- 原文維持のトピック分類
- Notion向けMarkdown生成
- Notion API転記
- `ticktick-task` 向けTODO候補JSON生成

`ticktick-task` 側の責務は、以下です。

- TODO候補JSONの受け取り
- 既存TickTickタスクとの統合判定
- 人間確認CSV
- OK済み候補のTickTick反映
- TickTick未完了タスクの作業ブロック分類
- 作業ブロック用タスクのTickTick出力
- Googleカレンダー空き時間参照と配置候補作成に関係するTickTick側処理

`memo-workflow` 側では、TickTick APIへの登録、更新、削除を実装しません。

TickTickへの登録、既存TickTickタスクとの統合判定、人間確認CSV、OK済み候補の反映、作業ブロック化、作業ブロック用タスク出力は、`ticktick-task` 側の責務として扱います。

## 3. 作業対象

作業対象は、このプロジェクトフォルダ内だけです。

認証情報置き場、別プロジェクト、既存のTickTick関連プロジェクトは、明示的な依頼がない限り読み取り、編集、参照を行いません。

`ticktick-task` は別プロジェクトです。

`memo-workflow` 側の作業中に、`ticktick-task` 側のファイルを推測で編集しません。

`ticktick-task` 側との接続が必要な場合は、`memo-workflow` 側ではTODO候補JSONの出力仕様と受け渡し条件だけを扱います。

`memo-automation-suite` 全体の開発方針、Phase構成、上流ワークフローの整理は、原則として `memo-workflow` 側で扱います。

TickTickタスクの登録、統合、レビュー、分解、差し戻し、作業ブロック分類など、タスク関連に特化した設計と実装は、兄弟プロジェクトの `ticktick-task` 側で扱います。

`memo-workflow` と `ticktick-task` の間で共有する申し送り、受け渡しメモ、移行メモは、親フォルダ直下の `D:\Automation-Projects\memo-automation-suite\handoff` に格納します。

## 4. 作業前に確認する文書

作業前に、必要に応じて以下を確認します。

- `README.md`
- `docs/document-index.md`
- `docs/app_policy.md`
- `docs/system_design.md`
- `docs/development_roadmap.md`
- `docs/issues.md`
- `docs/change-log.md`
- 対象Phaseの仕様書

文書の役割や参照ルールは、`docs/document-index.md` に従います。

設計、AI利用、外部連携、認証情報管理、ログ方針は、`docs/app_policy.md` を上位方針として扱います。

作業開始時は、まず `docs/document-index.md` を見出し索引として使い、関連しそうな文書を選びます。

毎回すべての文書を全文で深掘りするのではなく、作業の影響範囲に応じて確認の深さを調整します。

実装を追加する前に、`docs/system_design.md` でアプリ全体の流れと現在の作業位置を確認します。

設計図が粗い、または今回の作業に関係する未解決事項がある場合は、先に設計やイシューを整理してから実装します。

## 5. 文書の扱い

README.mdはプロジェクトの入口案内として扱い、詳細仕様を詰め込みません。

`docs/system_design.md` は全体設計図として扱います。

`docs/development_roadmap.md` はPhase構成と境界を管理する文書として扱います。

Phase固有の仕様、入力、出力、例外処理、確認方法は、対象Phaseの仕様書に記載します。

仕様変更や判断変更が発生した場合は、`docs/change-log.md` に記録します。

未解決事項、確認事項、判断待ちは、固定仕様や全体設計に混ぜ込まず、`docs/issues.md` に集約します。

判断が確定したら、該当する仕様書、設計図、ロードマップへ反映し、理由と影響範囲を `docs/change-log.md` に残します。

基本情報、全体フロー、実装状況、未解決事項は混ぜずに扱います。

Phase境界を示す場合は、「未実装だから書く」のではなく、「このPhaseで作るもの」「このPhaseで作らないもの」として書きます。

後続Phaseで実装が進んでも、過去Phaseの境界説明として意味が壊れない形を優先します。

ファイル名、見出し、Phase番号は、推測で変更しません。

## 6. 実装の進め方

実装前に、以下を確認します。

- どのPhaseの作業か
- 入力ファイルは何か
- 出力ファイルは何か
- 外部サービスへ読み取りだけか、書き込みもするのか
- AIが判断する範囲はどこか
- Python側で確定する範囲はどこか
- 人間確認が必要な範囲はどこか
- 認証情報や秘密値を扱うか
- 失敗時にどこで止まったか分かるか
- 今回の変更が `docs/system_design.md` と `docs/development_roadmap.md` に合っているか

一度に大きな範囲を実装しません。

Phase 1では、Discord投稿取得だけを小さく通します。

Phase 2以降のAI分類、Notion転記、`ticktick-task` 向けTODO候補JSON生成は、ロードマップ上の予定として扱います。

対象Phaseの詳細仕様がない場合は、先に仕様書を作成してから実装します。

## 7. ルート構造

Phase 2の分類結果は、後続で2つのルートに分岐します。

- Notionルート
- TODO候補ルート

Notionルートでは、分類結果をNotionで見返しやすい形に整え、必要に応じてNotion API転記を行います。

TODO候補ルートでは、Discord雑文からタスク候補になりそうな内容を抽出し、`ticktick-task` 側が受け取れるTODO候補JSONを生成します。

NotionルートとTODO候補ルートを同じ処理に混ぜません。

Notion向けMarkdown生成、Notion API転記、`ticktick-task` 向けTODO候補JSON生成は、それぞれ別の責務として扱います。

## 8. Discord連携の制限

Phase 1ではDiscordの読み取りだけを対象にします。

Discordへの投稿、編集、削除、リアクション追加、チャンネル設定変更は実装しません。

Bot Token、Channel ID、Timezoneは環境変数から読みます。

実際の値をコード、文書、ログに書きません。

## 9. AI利用の扱い

AI分類はPhase 2以降の予定です。

Phase 1ではAIを使った分類、要約、加工を実装しません。取得した本文は原文を維持して保存します。

AIを使うPhaseを追加する場合は、AIが担当する範囲、出力形式、失敗時の扱い、人間の確認範囲を仕様に分けて記載します。

AIは分類案、抽出案、判断補助を返すだけです。

AIにDiscord、Notion、TickTickへ直接書き込ませません。

外部サービスへの保存、登録、更新、削除はPythonスクリプト側で制御します。

## 10. Notion連携の制限

Notion API転記は、Notionルートの対象Phaseで扱います。

Notion API転記を実装する場合は、対象データ、登録先、実行条件、DryRunまたは人間確認、ログ方針を対象Phase仕様書に明記します。

環境変数にNotion認証情報が存在していても、それだけでNotion API転記を実行しません。

Phase仕様で許可され、かつ実行時に明示オプションが指定された場合だけ、Notionへの書き込みを行います。

## 11. TickTick関連の制限

`memo-workflow` 側では、TickTick APIへの登録、更新、削除を実装しません。

`memo-workflow` 側で扱うTickTick向け処理は、`ticktick-task` 側へ渡すTODO候補JSONの生成までです。

以下は `memo-workflow` 側では実装しません。

- TickTick APIへのタスク登録
- TickTick APIへのタスク更新
- TickTick APIへのタスク削除
- 既存TickTickタスクとの統合判定
- 人間確認CSVの生成
- OK済み候補のTickTick反映
- TickTick未完了タスクの作業ブロック分類
- 作業ブロック用タスクのTickTick出力
- Googleカレンダー空き時間参照とTickTick配置候補作成

TODO候補JSONの項目名、値、必須項目は、Phase 5仕様書で定義します。

`ticktick-task` 側との受け渡し確認は、Phase 5の完了条件として扱います。

## 12. ログと認証情報

ログには、認証情報、Bot Token、秘密値、環境変数の実値を出しません。

失敗時は、どの段階で失敗したか分かるように記録します。

Phase 1では、少なくとも以下を区別します。

- 環境変数の不足
- 認証
- チャンネル取得
- メッセージ取得
- 日付抽出
- 出力保存

後続Phaseでは、必要に応じて以下も区別します。

- 入力JSON読み込み
- 辞書照合
- AI呼び出し有無
- AI出力検証
- Notion向け出力生成
- Notion API転記
- `ticktick-task` 向けTODO候補JSON生成
- 出力保存

エラー原因を追える範囲で記録しつつ、秘密値や投稿本文の過剰な出力は避けます。

`memo-workflow` 側ではTickTick API書き込みを扱わないため、TickTick登録、更新、削除の実行ログは扱いません。

## 13. 出力管理

取得結果、分類結果、後続Phase向けの成果物は `outputs/` に保存します。

ログは `logs/` に保存します。

主な出力は以下です。

| 出力 | 役割 |
|---|---|
| `outputs/discord_messages_YYYY-MM-DD.json` | Discordから取得した原文と添付情報 |
| `outputs/topic_classification_YYYY-MM-DD.json` | Phase 2の分類結果 |
| `outputs/notion_markdown_YYYY-MM-DD.md` | Notion貼り付け用Markdown |
| `outputs/ticktick_todo_candidates_YYYY-MM-DD.json` | `ticktick-task` 側へ渡すTODO候補JSON |

Phase 2の分類結果は、NotionルートとTODO候補ルートの共通入力として扱います。

Notion向け出力と `ticktick-task` 向けTODO候補JSONは、別の出口として扱います。

## 14. 実装状況と確認状況の区別

コードや文書が存在するだけでは、実環境で確認済みとは扱いません。

報告や仕様書では、以下を分けて記録します。

- 実装済み
- 実データで確認済み
- テストデータで確認済み
- 未確認
- 未実装

後続Phaseは、未確認の機能を動作済みの前提にしません。

`ticktick-task` 側で行う処理は、`memo-workflow` 側の確認済み機能として扱いません。

## 15. Git運用ルール

作業前に現在の差分を確認します。

1つの作業単位が完了したら、差分を確認し、必要に応じてセルフチェックを行います。

文書修正では、対象ファイル以外に不要な差分が出ていないか確認します。

コード修正では、可能な範囲で構文チェック、DryRun、テスト実行を行います。

作業単位ごとにコミットします。

未コミットの変更を残したまま、次の大きな作業へ進みません。

コミットメッセージは、何を変更したか分かる短い英語にします。

例:

```text
Update memo workflow roadmap
Clarify TickTick handoff policy
Add phase 5 TODO candidate spec
```

## 16. 作業後の報告

作業後は、以下を分けて報告します。

- 作成・変更したファイル
- 各ファイルの役割
- 今回作成した範囲
- 今回作成していない範囲
- 確認できたこと
- 未確認のこと
- 次に実装する場合の最初の作業

特に、外部API、AI利用、Notion転記、`ticktick-task` 向けTODO候補JSON生成に関係する変更では、今回の作業範囲と対象外を明確に報告します。
