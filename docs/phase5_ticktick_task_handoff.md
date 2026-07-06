# Phase 5 ticktick-task申し送り

この文書は、`memo-workflow` のPhase 5が出力するTODO候補JSONを、後続の `ticktick-task` 側で受け取るときの申し送りをまとめます。

Phase 5の正本仕様は以下に従います。

```text
docs/phase5_ticktick_todo_candidates.md
docs/phase5_todo_candidate_json_spec.md
```

`ticktick-task` 側の受け入れ仕様の正本は以下です。

```text
../ticktick-task/docs/todo_candidate_intake_schema.md
../ticktick-task/docs/review_item_schema.md
```

この文書は、`ticktick-task` 側の実装仕様ではありません。
確認画面、CSV、スプレッドシート、TickTick反映、差し戻し、分解処理の詳細は `ticktick-task` 側で定義します。

## 1. Phase 5の役割

Phase 5は、Phase 2分類JSONからTODO候補を抽出し、`ticktick-task` 側へ渡せるJSONを出力します。

Phase 5は、TickTickへ登録、更新、削除を行いません。
既存TickTickタスクとの統合判定、人間確認、候補の承認、却下、編集、分解、差し戻し、TickTick反映も行いません。

## 2. 受け渡すファイル

正本は以下のJSONです。

```text
outputs/ticktick_todo_candidates_YYYY-MM-DD.json
```

必要に応じて、人間確認用Markdownも生成されます。

```text
outputs/ticktick_todo_candidates_YYYY-MM-DD.md
```

Markdownは確認用の派生表示であり、後続処理の正本はJSONです。

## 3. 受け渡しJSONの位置づけ

Phase 5出力JSONは、`ticktick-task` の外部TODO候補入力です。

トップレベルの入力元は、以下の固定値にします。

```text
intakeSource: memo_workflow_todo_candidate
```

候補一覧は `items` 配列で渡します。
各itemは、`sourceId`、`sourceText`、`sourceRefs`、`sourceContext` を持ち、元投稿とPhase 2の文脈へ戻れる形にします。

## 4. initialStatus の受け取り方

Phase 5の `initialStatus` は、TickTick登録可否の最終判断ではありません。
`ticktick-task` 側のレビュー、統合判定、反映処理のための初期候補状態です。

| initialStatus | Phase 5での意味 | ticktick-task側で期待する扱い |
|---|---|---|
| `todo_candidate` | 行動が読み取れ、TODO候補として渡せるもの | レビュー、既存タスク照合、承認、編集、分解、却下の対象 |
| `hold_candidate` | 行動がありそうだが、人間判断なしでは誤登録や混乱が起きそうなもの | まず人間確認へ回す対象 |
| `non_todo` | TODO候補として扱わないもの | 通常は登録対象外。必要なら参照、監査、却下済み相当として扱う |

## 5. todo_candidate の考え方

Phase 5では、行動が読み取れる投稿をTODO候補として広めに拾います。

以下のような表現も、対象や目的が読み取れる場合は `todo_candidate` になり得ます。

* 考える
* 決める
* 確認する
* 時間を取る
* 業者に出す
* 請求する

候補の粒度が粗いこと自体は、`hold_candidate` にする十分条件ではありません。

不要な候補、修正が必要な候補、分解が必要な候補は、`ticktick-task` 側のレビューで却下、編集、分解される前提です。

## 6. hold_candidate の考え方

`hold_candidate` は、Phase 5が自信を持てないものをすべて逃がす場所ではありません。

以下のように、人間判断なしで登録すると誤登録や混乱が起きそうな候補を想定します。

* 文脈、対象、担当、登録可否が分からない
* 行動ではなく、迷い、感情、方針メモに近い
* 登録前に分解方針を決めないと混乱する
* 費用、請求、見積などの判断が曖昧
* 条件付きで、実行可能な状態か分からない

## 7. needsReview / reviewReason

`needsReview` は、Phase 5時点で人間確認が必要そうな候補を示す初期フラグです。

`needsReview` が `true` の場合、`reviewReason` を空にしません。
`needsReview` が `false` の場合、`reviewReason` は `null` にできます。

この値は、`ticktick-task` 側の最終判断ではありません。
`ticktick-task` 側では、レビューCSVまたは専用レビュー画面で人間判断を入力します。

## 8. humanDecision / humanMemo

Phase 5出力では、`humanDecision` と `humanMemo` を空文字で付与します。

```json
{
  "humanDecision": "",
  "humanMemo": ""
}
```

この2項目は、`ticktick-task` 側でレビュー構造を揃えるための空欄です。
Phase 5側では、人間レビュー後の確定判断を事前に入れません。

## 9. 分解と差し戻し

Phase 5は、1投稿内の箇条書きTODOを検出できる場合、候補を行動単位に分けて渡します。
この場合、投稿全体の文脈ラベルを全候補に無条件継承せず、各行の本文から候補単位で文脈を付け直します。

1候補の中に `カット編集する`、`YouTubeにアップする` のような分解案がある場合、`proposedItems` は `title` と `estimatedMinutesCandidate` を持つobject配列として渡せます。
この時間候補は、分解後の各項目を別タスク候補として扱う場合の初期値です。
親候補の `estimatedMinutesCandidate` とは一致しなくてよく、`ticktick-task` 側レビューで採用、編集、削除できます。

粒度が粗い `todo_candidate` は、`ticktick-task` 側で分解できる前提です。

たとえば、Phase 5が以下のような粗い候補を渡す場合があります。

```text
株式会社A: 作業タスク
```

レビュー後には、`ticktick-task` 側で以下のように分解する可能性があります。

```text
株式会社A: 残すサイトを決めてもらう
株式会社A: 決まったサイト分を業者に出す
株式会社A: 業者対応分の費用を請求に含める
株式会社A: メインサイトの古いファイルを掃除する
```

分解、差し戻し、再処理の管理方式は `ticktick-task` 側で定義します。
`memo-workflow` 側では、差し戻しキュー、レビュー画面、分解結果の保存仕様を確定しません。

## 10. レビューで想定する判断

Phase 5出力を受け取った後、`ticktick-task` 側では少なくとも以下のような判断が必要になる可能性があります。

```text
approve
split_required
reject
hold
merge_existing
revise
mark_reference
keep_waiting
needs_more_info
```

これらの値名や保存形式は、`ticktick-task` 側の `docs/review_item_schema.md` を正とします。
初期運用ではスプレッドシートやCSVで判断し、必要に応じて確認画面へ移行する想定です。

## 11. blockingHint の扱い

`blockingHint` は、Phase 5から渡す参考情報です。

`blockingHint` は `ticktick-task` 側の正式な作業ブロック分類ではありません。
正式な分類、無視、変換、再判定は `ticktick-task` 側で行います。

## 12. estimatedMinutesCandidate の扱い

`estimatedMinutesCandidate` は、Phase 5から渡す所要時間候補です。

この値は正式な見積もりではありません。
`ticktick-task` 側では、レビュー画面の初期値として扱い、登録しない、時間なしで登録する、別の時間に直す、分解する、既存タスクを更新する、などの判断で上書きできます。

値は `null`、`15`、`30`、`45`、`60`、`90`、`120`、`150`、`180` のいずれかだけを受け渡します。

## 13. memo-workflow側で出さない項目

以下は、Phase 5出力JSONに含めません。

```text
matchType
proposedAction
matchedExistingTasks
existingTitleToRename
schedulingStatus
classification
blockingStatus
estimateConfidence
taskId
projectId
```

これらは、既存TickTickタスクや作業ブロック分類と照合してから `ticktick-task` 側で決めます。

## 14. ticktick-task 側で確定してほしいこと

以下は `memo-workflow` 側では確定しません。

* レビュー画面の有無
* スプレッドシート、CSV、画面のどれを正本にするか
* 承認、却下、編集、分解、差し戻しの値名
* 既存TickTickタスクとの統合判定
* 承認済み候補のTickTick登録、更新、削除
* 作業ブロック正式分類
* Googleカレンダー参照や配置候補作成

## 15. 運用上の前提

Phase 5は、最初から完璧な抽出精度を目指しません。

行動が読み取れるものは広めに拾い、不要な候補は `ticktick-task` 側のレビューで却下します。
精度が運用上問題になる場合は、実例をもとにPhase 5の抽出ルールを見直します。
