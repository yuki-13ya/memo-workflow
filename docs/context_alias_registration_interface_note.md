# 文脈ラベル辞書登録インターフェース設計メモ

この文書は、`config/context_aliases.csv` を将来的にどう登録、更新していくかの設計メモです。

現時点では、CSVを直接追加、編集、削除するための最小ローカルUIを `context-alias-editor/` として用意しています。
分類結果を見ながら辞書候補を昇格する本格レビューUIは、将来方針としてこの文書に残します。

## 背景

`context_aliases.csv` は、投稿本文に含まれる案件名、店舗名、人名、呼び方を、正式な `context_label` に寄せるための辞書です。

開発中はCSVを直接編集しても問題ありません。
ただし、運用が進むと辞書項目は増え、以下の判断が繰り返し発生します。

- この呼び方を既存ラベルに追加するか
- 新しい文脈ラベルとして作るか
- 一回限りの話題として辞書に入れないか
- TickTickリスト名候補まで持たせてよいか

そのため、最終的にはCSVを直接編集するのではなく、分類結果レビューから辞書へ昇格するインターフェースを用意するのが望ましいです。

## 基本方針

辞書登録は、設定画面でゼロから書くのではなく、実際に出てきた未確定メモから行います。

辞書登録の対象は、カテゴリー分類、文脈保持、タスク候補、外部連携先の判断に影響するものに限定します。
単に本文に登場する名前や普通名詞は、原則として辞書に登録しません。

Phase 2分類後に、以下のような投稿を辞書候補として提示します。

- `context_label` が空
- `context_match_status` が `ai_inferred`
- `task_hint` があるが辞書確定の `context_label` がない
- `needs_review` が付いている
- 複数候補に一致して `ambiguous` になっている

AIは辞書候補を出すだけに留めます。
正式に辞書へ登録するかどうかは人間が判断します。

生活タスクっぽい投稿は、基本的には `personal` category で扱います。
庭掃除、家の片付け、買い物、家族との約束などは、後続連携で文脈が迷子になる場合だけ辞書候補にします。
毎回の分類に不要な生活単語を辞書化しすぎないようにします。

## 想定する操作

辞書候補ごとに、人間が以下を選べる形にします。

| 操作 | 意味 |
|---|---|
| 既存ラベルに追加 | 既存の `canonical_name` に alias や related_name を追加する |
| 新規ラベルを作成 | 新しい `canonical_name` を作り、alias、category_hint、flags_hint を設定する |
| 辞書に入れない | 一回限り、または文脈ラベル化しない話題として扱う |
| 今回だけ保留 | 判断を後回しにし、次回以降も候補として確認できるようにする |

最低限、画面または確認ファイルには以下を表示します。

- 元投稿本文
- `topic_title`
- `category`
- `flags`
- AIが推測した `raw_context_label`
- 現在の `context_match_status`
- 既存辞書の近い候補
- 登録先候補

## 登録フォームの項目

辞書登録時に扱う項目は、現在の `config/context_aliases.csv` に合わせます。

| 項目 | 扱い |
|---|---|
| `canonical_name` | 正式な文脈ラベル。後続Phaseに引き継ぐ名前 |
| `aliases` | 投稿本文に出やすい呼び方。複数値はセミコロン区切り |
| `related_names` | 人名など、単独では正式名ではないが文脈推定に使う名前 |
| `ticktick_list_name` | TickTick側リスト名と完全一致できる場合だけ設定する |
| `category_hint` | Phase 2のcategory候補 |
| `flags_hint` | Phase 2で付けやすいflag候補。複数値はセミコロン区切り |
| `active` | 通常は `true` |
| `notes` | 人間向け補足 |

`ticktick_list_name` は慎重に扱います。
TickTick側の既存リスト名と完全一致できる場合だけ設定し、曖昧なものは空欄または保留にします。

## 段階的な実装案

最初から本格的なUIやDBを作りません。
Phase 2の補助機能として、以下の順に育てます。

1. `outputs/topic_classification_YYYY-MM-DD.json` から辞書候補Markdownを生成する
2. 人間がMarkdownを見て、必要なものだけ `context_aliases.csv` に手で反映する
3. 候補Markdownの形式が安定したら、分類結果レビューから辞書登録できるUIへ拡張する
4. UIからCSVへ追記できるようにする
5. 辞書が大きくなり、履歴や無視リストが必要になったらSQLiteなどへの移行を検討する

最初の補助スクリプト候補:

```text
topic-classifier/extract_context_alias_candidates.py
```

想定出力:

```text
outputs/context_alias_candidates_YYYY-MM-DD.md
```

## 将来のレビューUIイメージ

```text
[辞書候補]

投稿:
コミュニティAの営業どうするか、何ができるかをもう一度確認して...

分類結果:
topic_title: コミュニティAの営業と集客方法の検討
category: work
flags: task_hint
context_label: 未確定
context_match_status: ai_inferred

操作:
( ) 既存ラベルに追加: [選択]
( ) 新規ラベルを作成: [コミュニティA]
( ) 辞書に入れない
( ) 今回だけ保留

alias: [コミュニティAの営業;コミュニティA]
category_hint: [work]
flags_hint: [task_hint]
ticktick_list_name: []

[登録する]
```

## 決めておきたいこと

実装前に、以下は改めて確認します。

- 「辞書に入れない」と「今回だけ保留」をどこに保存するか
- CSVのまま運用する期間
- ローカルUIをPhase 2に含めるか、別Phaseの補助機能として扱うか
- 既存ラベルの検索方法
- 類似候補をAIに出させるか、Python側の文字列照合に留めるか
- 辞書更新後にPhase 2を自動再実行するか、手動にするか

## 現時点の判断

現時点では、辞書の正本は `config/context_aliases.csv` のままにします。

`context-alias-editor/` は、正本CSVを直接読み書きする最小UIです。
既定URLは `http://127.0.0.1:8788/` です。`ticktick-task` 側のTODO候補レビューUIと衝突しないよう、辞書編集UIでは `8787` を使いません。
保存時には `outputs/context_alias_backups/` にバックアップを作ります。

将来のインターフェースは、分類結果レビューから辞書へ昇格する流れを基本にします。
AIは候補生成まで、人間が正式登録を決め、PythonがCSVまたは将来の辞書ストアへ保存します。
