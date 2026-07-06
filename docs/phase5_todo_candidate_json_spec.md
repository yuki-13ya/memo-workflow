# Phase 5 TODO候補JSON仕様

この文書は、Phase 5で `ticktick-task` 側へ渡すTODO候補JSONの出力仕様を定義します。

Phase 5全体の目的、責務、判断境界は `docs/phase5_ticktick_todo_candidates.md` に従います。
この文書では、出力JSONの構造、項目、値、サンプル、バリデーション方針だけを扱います。

## 1. この文書の目的

Phase 5の出力を、`ticktick-task` 側の外部TODO候補入力スキーマへ合わせます。

`ticktick-task` 側の受け入れ仕様の正本は以下です。

```text
../ticktick-task/docs/todo_candidate_intake_schema.md
../ticktick-task/docs/review_item_schema.md
```

親フォルダ側の申し送りは以下です。

```text
../handoff/memo_workflow_phase5_to_ticktick_intake.md
```

この仕様で決めることは以下です。

* JSON全体の形
* TODO候補1件ごとの項目
* 必須項目と任意項目
* `initialStatus` の値
* 人間確認が必要な候補の表し方
* 元投稿と根拠情報の保持方法
* `ticktick-task` 側へ渡してよい情報、渡さない情報

## 2. 前提となるPhase 5仕様書への参照

Phase 5の基本方針は、以下の文書を正とします。

```text
docs/phase5_ticktick_todo_candidates.md
```

Phase 5では、TickTick APIへの登録、更新、削除を行いません。
既存TickTickタスクとの統合判定、人間確認CSV、OK済み候補のTickTick反映、作業ブロック分類、作業ブロック用タスク出力は `ticktick-task` 側で扱います。

## 3. 入力ファイル

Phase 5の入力は、Phase 2の分類結果JSONです。

```text
outputs/topic_classification_YYYY-MM-DD.json
```

入力から主に引き継ぐ情報は以下です。

* トピックID
* トピックタイトル
* 文脈ラベル
* 文脈ラベルの確定状態
* category
* flags
* confidence
* 元投稿ID
* 元投稿本文
* 投稿時刻
* 添付メタデータの有無

Phase 5では、入力JSON内の元投稿本文を書き換えません。

## 4. 出力ファイル

Phase 5の正本出力は、以下のJSONです。

```text
outputs/ticktick_todo_candidates_YYYY-MM-DD.json
```

必要に応じて、人間確認用Markdownを派生表示として出力できます。

```text
outputs/ticktick_todo_candidates_YYYY-MM-DD.md
```

Markdownは確認用であり、後続処理へ渡す正本はJSONです。

## 5. JSON全体構造

JSON全体は、メタ情報、集計、候補一覧を持ちます。

```json
{
  "schemaVersion": "1.0",
  "intakeSource": "memo_workflow_todo_candidate",
  "sourceFile": "outputs/topic_classification_YYYY-MM-DD.json",
  "sourceDate": "YYYY-MM-DD",
  "createdAt": "YYYY-MM-DDTHH:mm:ss+09:00",
  "createdBy": "memo-workflow",
  "summary": {
    "totalItems": 0,
    "candidateCount": 0,
    "holdCount": 0,
    "excludedCount": 0,
    "needsReviewCount": 0
  },
  "items": []
}
```

### トップレベル項目

| 項目 | 型 | 必須 | 内容 |
|---|---|---|---|
| `schemaVersion` | string | 必須 | このJSON仕様のバージョン |
| `intakeSource` | string | 必須 | 入力元。固定値は `memo_workflow_todo_candidate` |
| `sourceFile` | string | 必須 | 入力に使ったPhase 2 JSONのパス |
| `sourceDate` | string | 必須 | 対象日。形式は `YYYY-MM-DD` |
| `createdAt` | string | 必須 | JSONを生成した日時。ISO 8601形式 |
| `createdBy` | string | 必須 | 生成主体。通常は `memo-workflow` |
| `summary` | object | 必須 | 候補件数の集計 |
| `items` | array | 必須 | TODO候補の配列 |

## 6. item 1件ごとの項目

`items` 配列の各要素は、TODO候補、保留候補、非TODO判定のいずれか1件を表します。

| 項目 | 型 | 必須 | 内容 |
|---|---|---|---|
| `sourceId` | string | 必須 | Phase 5内で一意な候補ID |
| `intakeSource` | string | 必須 | 候補単位の入力元。固定値は `memo_workflow_todo_candidate` |
| `sourceDate` | string | 必須 | 対象日。形式は `YYYY-MM-DD` |
| `sourceTitle` | string | 必須 | Phase 2のトピックタイトル |
| `sourceText` | string | 必須 | 候補化の根拠となる元投稿本文または抜粋 |
| `sourceRefs` | array[object] | 必須 | 元投稿ID、投稿時刻などの参照情報 |
| `sourceContext` | object | 必須 | Phase 2由来の文脈情報 |
| `initialStatus` | string | 必須 | Phase 5での初期候補状態 |
| `proposedTitle` | string | 必須 | `ticktick-task` 側へ渡す候補タイトル |
| `proposedDescription` | string | 必須 | 候補の補足説明 |
| `proposedItems` | array[object] | 必須 | 分解済み項目または別タスク候補。Phase 5で分解しない場合は空配列 |
| `estimatedMinutesCandidate` | number or null | 必須 | 所要時間候補。正式な見積もりではなく、後続レビューの初期値 |
| `needsReview` | boolean | 必須 | 人間確認が必要か |
| `reviewReason` | string or null | 必須 | 人間確認が必要な理由 |
| `blockingHint` | array[string] | 必須 | `ticktick-task` 側の作業ブロック分類に使える参考ヒント |
| `humanDecision` | string | 必須 | 人間判断欄。外部入力時点では空文字 |
| `humanMemo` | string | 必須 | 人間メモ欄。外部入力時点では空文字 |

## 7. sourceRefs

`sourceRefs` は、元情報へ戻るための参照情報です。

Discord投稿由来の場合は以下の形を基本にします。

```json
[
  {
    "type": "discord_post",
    "id": "discord-post-001",
    "time": "2026-07-01T09:15:00+09:00"
  }
]
```

認証情報、秘密値、一時URL、ローカル環境固有の秘密パスは含めません。

## 8. sourceContext

`sourceContext` は、候補を理解するための補助情報です。

`memo-workflow` 由来の場合は以下を基本にします。

```json
{
  "originalSource": "phase2_topic_classification",
  "topicId": "topic-001",
  "topicTitle": "店舗Bのホームページ修正",
  "contextLabel": "店舗B",
  "contextLabelStatus": "confirmed",
  "category": "work",
  "flags": ["task_hint"],
  "confidence": 0.92
}
```

添付メタデータを保持する場合は、`sourceContext.attachments` に参照情報として入れます。
秘密値を含むローカルパスや一時URLは入れません。

## 9. 必須項目

トップレベルでは、以下を必須とします。

```text
schemaVersion
intakeSource
sourceFile
sourceDate
createdAt
createdBy
summary
items
```

item 1件では、以下を必須とします。

```text
sourceId
intakeSource
sourceDate
sourceTitle
sourceText
sourceRefs
sourceContext
initialStatus
proposedTitle
proposedDescription
proposedItems
estimatedMinutesCandidate
needsReview
reviewReason
blockingHint
humanDecision
humanMemo
```

値が未確定の場合でも、項目自体は省略しません。
未確定値は `null`、空文字、空配列のいずれかを仕様に合わせて入れます。

## 10. 任意項目

任意項目は、後続処理や人間確認に役立つ場合だけ付けます。

| 項目 | 型 | 内容 |
|---|---|---|
| `sourceContext.notes` | string or null | Phase 5側の補足 |
| `sourceContext.attachments` | array[object] | 添付ファイル名、種類、保存状態などの参照情報 |
| `sourceContext.dueDateHint` | string or null | 本文から読み取れる日付候補。正式な期限ではない |
| `sourceContext.durationHintMinutes` | number or null | 所要時間の参考値。正式な見積もりではない |
| `sourceContext.extractionMode` | string or null | `topic`、`message_line` など、候補抽出単位の参考情報 |

任意項目を追加する場合も、TickTick登録済みID、TickTickリスト名確定値、作業ブロック正式分類など、`ticktick-task` 側で確定する値は入れません。

1投稿内の箇条書きから複数候補を作る場合、候補ごとの `sourceText` は根拠となる行を入れます。
投稿全体の `contextLabel`、`flags`、`reviewReason` を全候補へ無条件に継承せず、各行の本文と辞書照合結果から候補単位で再評価します。

分解済み項目がある場合、`proposedItems` は文字列ではなく以下の形にします。

```json
[
  {
    "title": "カット編集する",
    "estimatedMinutesCandidate": 120,
    "order": 1
  },
  {
    "title": "YouTubeにアップする",
    "estimatedMinutesCandidate": 15,
    "order": 2
  }
]
```

`proposedItems[].estimatedMinutesCandidate` は、分解後に別タスクとして扱う場合の初期時間候補です。
親候補の `estimatedMinutesCandidate` と一致する必要はありません。
親候補を1件として登録する場合は親の時間候補を使い、分解して別タスク化する場合は各 `proposedItems` の時間候補を使います。

## 11. initialStatus の値

`initialStatus` は以下の3種類だけを使います。

```text
todo_candidate
hold_candidate
non_todo
```

| 値 | 意味 |
|---|---|
| `todo_candidate` | 行動が読み取れ、`ticktick-task` 側へTODO候補として渡せるもの |
| `hold_candidate` | 行動がありそうだが、人間判断なしで渡すと誤登録や混乱が起きそうなもの |
| `non_todo` | TODO候補として扱わないもの |

`initialStatus` はPhase 5での初期候補状態です。
TickTickへの登録可否、既存タスクとの統合可否、作業ブロック分類を確定する値ではありません。

`todo_candidate` は、粒度が粗いことだけを理由に `hold_candidate` へ寄せません。
「考える」「決める」「確認する」などの検討系表現も、対象や目的が読み取れる場合は行動として扱います。

不要な候補、修正が必要な候補、分解が必要な候補は、後続の `ticktick-task` 側レビューで却下、編集、分解される前提です。

## 12. needsReview / reviewReason の扱い

`needsReview` は、人間確認が必要な候補かどうかを表します。

以下に該当する場合は、原則として `true` にします。

* `initialStatus` が `hold_candidate`
* 費用、請求、見積、収入に関係する判断がある
* 条件付きで実行する
* 日程、頻度、期限が曖昧
* 登録前に分解方針を決めないと混乱する
* 文脈ラベルが未確定
* AI分類または候補化の確信度が低い
* 本文から判断しきれない
* タスク化するか記録に留めるか迷う

候補の粒度が粗いこと自体は、`needsReview` を `true` にする十分条件ではありません。

`reviewReason` には、人間確認が必要な理由を短く書きます。

`needsReview` が `true` の場合、`reviewReason` は空にしません。
`needsReview` が `false` の場合、`reviewReason` は `null` にできます。

## 13. blockingHint の扱い

`blockingHint` は、`ticktick-task` 側の作業ブロック分類に使える参考情報です。

`blockingHint` は正式な `classification` ではありません。
正式な作業ブロック分類は `ticktick-task` 側で行います。

`blockingHint` は配列として持ち、必要がなければ空配列にします。

想定値:

```text
needs_review
needs_breakdown
needs_duration_estimate
condition_waiting
schedule_related
money_related
context_unclear
not_task_like
reference_only
```

これらは参考ヒントであり、`ticktick-task` 側で別の分類へ変換、無視、再判定される可能性があります。

## 14. estimatedMinutesCandidate の扱い

`estimatedMinutesCandidate` は、レビュー画面で最初に表示する所要時間候補です。

これは正式な見積もりではありません。
`ticktick-task` 側のレビューで、登録しない、時間なしで登録する、別の時間に直す、分解する、既存タスクを更新する、などの判断で上書きできます。

値は以下のいずれかにします。

```text
null
15
30
45
60
90
120
150
180
```

本文中に `30分`、`1時間`、`1.5h` のような明示時間がある場合は、それを優先して候補にします。
明示時間がない場合は、本文や候補タイトルの語から控えめな初期候補を入れることがあります。

合計が180分を超える、または単体タスクとして扱うには大きすぎる場合は、`estimatedMinutesCandidate` を `null` にし、必要に応じて `blockingHint` に `needs_duration_estimate` や `needs_breakdown` を付けます。

Phase 5の通常実装では外部AIを呼ばず、ローカルルールで候補を作ります。
AIを使う場合も、実行時に明示オプションが指定された場合だけとし、出力値はこの許容値に丸めて検証します。

## 15. 元投稿・根拠情報の保持方法

候補ごとに、元投稿へ戻れる情報を保持します。

必ず保持する情報:

* `sourceId`
* `sourceTitle`
* `sourceText`
* `sourceRefs`
* `sourceContext.topicId`
* `sourceContext.topicTitle`

可能な範囲で保持する情報:

* `sourceContext.contextLabel`
* `sourceContext.contextLabelStatus`
* `sourceContext.category`
* `sourceContext.flags`
* `sourceContext.attachments`

`sourceText` には、候補化の根拠になる本文または抜粋を入れます。
AIやPhase 5処理が本文にない事情を補ってはいけません。

## 16. ticktick-task 側へ渡してよい情報

`ticktick-task` 側へ渡してよい情報は以下です。

* TODO候補タイトル
* TODO候補の補足説明
* 初期候補状態
* 人間確認要否
* 人間確認理由
* 元投稿ID
* 元投稿時刻
* 根拠本文または根拠抜粋
* Phase 2由来の `contextLabel`
* Phase 2由来の `topicTitle`
* Phase 2由来の `category`
* Phase 2由来の `flags`
* 添付メタデータの参照情報
* `blockingHint`
* `estimatedMinutesCandidate`
* 空文字の `humanDecision`
* 空文字の `humanMemo`

これらは、`ticktick-task` 側の統合判定、人間確認、作業ブロック分類の材料として渡します。

## 17. ticktick-task 側へ渡さない情報

以下は、このJSONに入れません。

* Discord Bot Token
* Notion API Token
* TickTick API Token
* その他の認証情報や秘密値
* `.env` の実値
* TickTickへの登録済みタスクID
* TickTickへの登録、更新、削除を指示する値
* 既存TickTickタスクとの統合結果
* 人間確認CSVの確定結果
* OK済み候補の反映結果
* `ticktick-task` 側の正式な作業ブロック `classification`
* `matchType`
* `proposedAction`
* `matchedExistingTasks`
* `existingTitleToRename`
* `schedulingStatus`
* `blockingStatus`
* `estimateConfidence`
* `taskId`
* `projectId`
* Googleカレンダー空き時間参照結果

添付ファイルを扱う場合は、Phase 2またはPhase 1の出力で管理している参照情報に留めます。
秘密値を含むローカルパスや一時URLは入れません。

## 18. サンプルJSON

以下は、1ファイル全体の形を示すサンプルです。

```json
{
  "schemaVersion": "1.0",
  "intakeSource": "memo_workflow_todo_candidate",
  "sourceFile": "outputs/topic_classification_2026-07-01.json",
  "sourceDate": "2026-07-01",
  "createdAt": "2026-07-01T18:30:00+09:00",
  "createdBy": "memo-workflow",
  "summary": {
    "totalItems": 2,
    "candidateCount": 1,
    "holdCount": 1,
    "excludedCount": 0,
    "needsReviewCount": 1
  },
  "items": [
    {
      "sourceId": "todo-2026-07-01-001",
      "intakeSource": "memo_workflow_todo_candidate",
      "sourceDate": "2026-07-01",
      "sourceTitle": "店舗Bのホームページ修正",
      "sourceText": "店舗Bのホームページを修正して納品する",
      "sourceRefs": [
        {
          "type": "discord_post",
          "id": "discord-post-001",
          "time": "2026-07-01T09:15:00+09:00"
        }
      ],
      "sourceContext": {
        "originalSource": "phase2_topic_classification",
        "topicId": "topic-001",
        "topicTitle": "店舗Bのホームページ修正",
        "contextLabel": "店舗B",
        "contextLabelStatus": "confirmed",
        "category": "work",
        "flags": ["task_hint"],
        "confidence": 0.92
      },
      "initialStatus": "todo_candidate",
      "proposedTitle": "店舗B: 店舗Bのホームページ修正",
      "proposedDescription": "Phase 2でtask_hintが付いたトピックから抽出したTODO候補。",
      "proposedItems": [],
      "estimatedMinutesCandidate": 60,
      "needsReview": false,
      "reviewReason": null,
      "blockingHint": [],
      "humanDecision": "",
      "humanMemo": ""
    },
    {
      "sourceId": "todo-2026-07-01-002",
      "intakeSource": "memo_workflow_todo_candidate",
      "sourceDate": "2026-07-01",
      "sourceTitle": "生活リズムの困りごと",
      "sourceText": "どうしても朝が起きられない。これは本当に良くない。",
      "sourceRefs": [
        {
          "type": "discord_post",
          "id": "discord-post-002",
          "time": "2026-07-01T12:30:00+09:00"
        }
      ],
      "sourceContext": {
        "originalSource": "phase2_topic_classification",
        "topicId": "topic-002",
        "topicTitle": "生活リズムの困りごと",
        "contextLabel": null,
        "contextLabelStatus": "none",
        "category": "health_lifestyle",
        "flags": ["health_or_care"],
        "confidence": 0.65
      },
      "initialStatus": "hold_candidate",
      "proposedTitle": "生活リズムの困りごと",
      "proposedDescription": "task_hintはないが、仕様上確認対象にできる内容として保留候補にしたもの。",
      "proposedItems": [],
      "estimatedMinutesCandidate": null,
      "needsReview": true,
      "reviewReason": "候補として重要そうだが、登録前に確認や分解が必要。",
      "blockingHint": ["needs_review", "needs_breakdown", "context_unclear"],
      "humanDecision": "",
      "humanMemo": ""
    }
  ]
}
```

## 19. バリデーション方針

Phase 5の実装では、保存前に以下を確認します。

* JSONとしてパースできる
* トップレベル必須項目が存在する
* `intakeSource` が `memo_workflow_todo_candidate` である
* `items` が配列である
* item 1件ごとの必須項目が存在する
* item 1件ごとの `intakeSource` が `memo_workflow_todo_candidate` である
* `initialStatus` が `todo_candidate`、`hold_candidate`、`non_todo` のいずれかである
* `needsReview` がbooleanである
* `needsReview` が `true` の候補では `reviewReason` が空でない
* `blockingHint` が配列である
* `sourceRefs` が配列である
* `sourceContext` がobjectである
* `proposedItems` が配列である
* `proposedItems` の各要素がobjectであり、`title` を持つ
* `proposedItems[].estimatedMinutesCandidate` が `null`、`15`、`30`、`45`、`60`、`90`、`120`、`150`、`180` のいずれかである
* `estimatedMinutesCandidate` が `null`、`15`、`30`、`45`、`60`、`90`、`120`、`150`、`180` のいずれかである
* `humanDecision` と `humanMemo` が存在し、stringである
* 認証情報らしき値が含まれていない

バリデーションに失敗したJSONは、成功出力として扱いません。

## 20. エラー時の扱い

Phase 5の出力JSON生成でエラーが起きた場合は、どの段階で失敗したか分かるようにします。

区別する段階:

* 入力JSON読み込み
* 入力JSONの形式確認
* 候補抽出
* 候補項目の組み立て
* 出力JSONバリデーション
* 出力保存

AIを使う場合、AI出力がこの仕様に合わないときは成功扱いしません。
その場合も、AIに外部サービスへの書き込みを行わせません。

ログファイル名や実行オプションの詳細は、この文書では確定しません。

## 21. この仕様で確定しないこと

この文書では、以下を確定しません。

* AIプロンプト
* AI出力スキーマの詳細
* AIプロバイダやモデル
* ログファイル名
* 人間確認用Markdownの詳細レイアウト
* `ticktick-task` 側の取り込み実装
* 既存TickTickタスクとの統合判定仕様
* 人間確認CSVの仕様
* OK済み候補のTickTick反映仕様
* 作業ブロック正式分類
* Googleカレンダー空き時間参照

これらは、Phase 5実装直前または `ticktick-task` 側の仕様として別途定義します。
