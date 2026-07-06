# Phase 2: AIによる原文維持のトピック分類

この文書は、Phase 2で実装するトピック分類の仕様を定義します。

## 目的

Phase 1で取得したDiscord投稿を、原文を維持したままトピック単位に分類します。

Phase 2では、後続のNotion貼り付け用Markdown生成と `ticktick-task` 向けTODO候補JSON生成に渡せる中間データを作ることを目的とします。
投稿本文を書き換えたり、Notionへ転記したり、TickTick APIへの登録、更新、削除を行ったりしません。

## 入力

Phase 2の入力は、Phase 1が出力したJSONです。

想定入力:

- `outputs/discord_messages_YYYY-MM-DD.json`
- `config/context_aliases.csv`

主に参照する項目:

| 項目 | 扱い |
|---|---|
| `target_date` | 分類対象日 |
| `timezone` | 表示・記録用のタイムゾーン |
| `messages[].message_id` | 元投稿との対応付け |
| `messages[].created_at_local` | 投稿順と時刻表示 |
| `messages[].author_name` | 投稿者表示 |
| `messages[].content` | 分類対象の本文。原文を維持する |
| `messages[].attachments` | 添付メタデータとローカル保存先 |

`attachment_urls` は長期参照の前提にしません。
添付ファイルの中身はPhase 2では解析しません。

`config/context_aliases.csv` は、AIに渡す前にPython側で行う文脈ラベル補正に使います。
辞書で確定できた `context_label` は、AI判断より優先します。

## 対象範囲

Phase 2で行うこと:

- Phase 1 JSONを読み込む
- 投稿本文と添付メタデータを維持する
- 投稿をトピック単位に分類する
- 分類結果と元投稿の対応関係を残す
- 分類できない投稿を未分類として残す
- 後続Phase向けの中間JSONを保存する
- 人間が確認しやすい分類確認用Markdownを保存する

Phase 2で行わないこと:

- 投稿本文の書き換え
- 投稿本文の要約を原文の代わりにすること
- 添付ファイルのOCR、PDF読解、動画解析
- Google Driveなど外部コミュニティA先の取得
- Notion貼り付け用Markdownの最終整形
- Notion API転記
- `ticktick-task` 向けTODO候補JSON生成
- TickTick APIへの登録、更新、削除
- Discordへの投稿、編集、削除

## 原文維持ルール

Phase 2では、元投稿の `content` を変更しません。

AIが生成してよいもの:

- トピック名
- 文脈ラベル
- 大分類
- フラグ
- 分類理由
- 信頼度
- 未分類理由

AIが変更してはいけないもの:

- `message_id`
- `created_at`
- `created_at_local`
- `author_name`
- `content`
- `attachments`
- `local_path`

誤字修正、言い換え、要約、補足説明は、原文の代替として保存しません。
必要になった場合も、原文とは別項目に分けます。

## 分類方針

Phase 2では、最初から固定カテゴリを増やしすぎず、トピック単位のまとまりを優先します。

分類では、主分類である `category` と、横断的な印である `flags` を分けます。
たとえば、仕事のメモで費用判断も含む場合は、`category: "work"` とし、`flags` に `money_related` や `task_hint` を付けます。

初期の `category` 候補:

| category | 意味 |
|---|---|
| `work` | 仕事、案件、制作、運用に関するメモ |
| `health_lifestyle` | 生活習慣、食事、運動、体調管理に関するメモ |
| `personal` | 個人的な記録、生活、思いつき |
| `reference` | 後で参照する情報、コミュニティA、添付中心の投稿 |
| `uncategorized` | 判断できないもの |

初期の `flags` 候補:

| flag | 意味 |
|---|---|
| `task_hint` | 後続Phaseでタスク候補になりそうなもの |
| `money_related` | 見積、費用、請求、収入、価格判断に関係するもの |
| `schedule_related` | 日程、頻度、時間ブロックに関係するもの |
| `health_or_care` | 体調、ケア、病院、生活管理に関係するもの |
| `meal_related` | 食事、食べたもの、食事記録に関係するもの |
| `exercise_related` | 散歩、運動、身体活動に関係するもの |
| `outing_related` | 外出、訪問、移動を伴う予定や記録に関係するもの |
| `travel_related` | 旅行、遠出、交通機関を使った移動に関係するもの |
| `leisure_related` | 娯楽、遊び、リフレッシュ目的の予定や記録に関係するもの |
| `attachment_only` | 本文が空で添付中心のもの |
| `needs_review` | AI判断に不安があり、人間確認が必要なもの |

AIは必要に応じて `topic_title` を生成します。
ただし、`topic_title` や `classification_reason` でも、本文にない場所、関係、所属、理由を推測で足しません。
たとえば、「お母さん」「庭」という本文だけから「実家」と決めつけず、本文にある表現に留めます。
ただし、分類に迷う場合は無理に決めず、`uncategorized` にします。
読み込み確認などの一時的なテスト投稿も、通常は `uncategorized` として扱います。
フラグに迷う場合は、過剰に付けず `needs_review` を使います。

生活習慣、食事、運動、体調管理の投稿は、通常 `health_lifestyle` として扱います。
家族や日常の記録でも、健康・食事・運動の管理に関係しないものは `personal` にします。
庭掃除、家の片付け、買い物、家族との約束などの生活タスクは、健康管理や仕事案件でない限り `personal` にします。
生活タスクが予定化、時間確保、作業候補になりそうな場合は、categoryを増やさず `task_hint` や `schedule_related` を付けます。
外出を伴う投稿は、目的に応じて `work`、`personal`、`health_lifestyle` などのcategoryを選び、`outing_related`、`travel_related`、`leisure_related` を必要に応じて付けます。

## 文脈保持ルール

`task_hint` が付くトピックでは、後続Phaseで短いタスク名だけが独り歩きしないように、必ず `context_label` または十分に具体的な `topic_title` を持たせます。

例:

| topic_title | context_label | 後続で避けたい状態 |
|---|---|---|
| 株式会社Aの整理とマルウェア対応 | 株式会社A | `残すサイトを決めてもらう` だけが残る |
| 店舗Bのホームページ修正と納品 | 店舗B | `ホームページを修正する` だけが残る |

後続Phaseでタスク候補を抽出する場合は、`context_label`、`topic_title`、`source_message_id` を引き継ぎます。
Phase 2ではタスク候補そのものは作りませんが、タスク候補を文脈つきで拾える状態を作ります。

## 文脈ラベルと別名辞書

案件名、会社名、店舗名、人名、呼び方には表記ゆれがあります。
Phase 2では、AIの推測だけで文脈を確定せず、人間が管理する別名辞書に基づいて `context_label` を補正します。

別名辞書は、スプレッドシートで編集しやすく、実装からも読みやすいCSVとして管理します。

- 管理ファイル: `config/context_aliases.csv`
- 文字コード: UTF-8
- 区切り: カンマ
- `aliases`、`related_names`、`flags_hint` の複数値はセミコロン区切り

辞書の列:

| 列 | 内容 |
|---|---|
| `canonical_name` | 正式な文脈ラベル。`context_label` に入る値 |
| `aliases` | 案件名、略称、呼び方。複数ある場合はセミコロン区切り |
| `related_names` | 人名など、単独では正式名ではないが文脈推定に使う名前 |
| `ticktick_list_name` | TickTickリスト名と完全一致した場合だけ後続Phaseで自動分類候補にする値 |
| `category_hint` | Phase 2分類時のcategory候補 |
| `flags_hint` | Phase 2分類時に付けやすいflag候補。複数ある場合はセミコロン区切り |
| `active` | `true` の行だけ有効として扱う |
| `notes` | 人間向けの補足。判定ロジックには使わない |

辞書で扱う内容の例:

```json
{
  "canonical_name": "株式会社A",
  "aliases": ["A社"],
  "related_names": ["担当者A"],
  "ticktick_list_name": "株式会社A"
}
```

```json
{
  "canonical_name": "店舗B",
  "aliases": ["B先生", "B先生の所"],
  "related_names": [],
  "ticktick_list_name": "店舗B"
}
```

```json
{
  "canonical_name": "講座C",
  "aliases": ["C先生", "C先生の所", "講座C"],
  "related_names": [],
  "ticktick_list_name": ""
}
```

文脈判定の方針:

- 投稿本文が `aliases` または `related_names` に一致し、候補が1件だけの場合は `context_label` を `canonical_name` に寄せる
- 複数候補に一致する場合は、自動確定せず `needs_review` を付ける
- 別名辞書にないがAIが推測しただけの場合は、自動確定せず `needs_review` を付ける
- TickTickリスト名へ自動連携する場合は、`ticktick_list_name` が既存リスト名と完全一致する場合だけ自動分類候補にする
- 辞書の編集は、まず `config/context_aliases.csv` を更新し、分類ロジック側はその内容を読む

Phase 2出力では、必要に応じて以下を保持します。

| 項目 | 内容 |
|---|---|
| `raw_context_label` | 投稿本文からAIが読み取った文脈候補 |
| `context_label` | 別名辞書で補正した正式な文脈ラベル |
| `context_match_status` | `alias_matched`、`related_name_matched`、`ambiguous`、`ai_inferred`、`unmatched` など |

## 添付の扱い

添付がある投稿は、添付メタデータと `local_path` を維持します。

Phase 2では、画像、動画、PDFの中身を読みません。
添付のみの投稿は、本文が空であることを維持し、添付メタデータをもとに `reference` または `uncategorized` として分類します。

Office系などPhase 1で `skipped` になった添付は、その状態を維持します。

## 出力

出力先は `outputs/` とします。

想定ファイル名:

- `outputs/topic_classification_YYYY-MM-DD.json`
- `outputs/topic_classification_YYYY-MM-DD.md`

JSONは後続Phase用、Markdownは人間の確認用として扱います。

確認用Markdownには、分類結果を人間が見直しやすいように以下を含めます。

- トピック数、投稿数、未分類数、要確認候補数
- category と flags の件数
- Geminiを呼び出したかどうか
- `needs_review`、`low` confidence、`uncategorized`、文脈ラベル未確定、`task_hint` だが `context_label` が空のトピック
- 元投稿本文、添付メタデータ、辞書照合候補

Markdownは確認用の派生表示であり、後続Phaseが読む正本はJSONとします。

## 実装単位

Phase 2の実装は、以下の順番で処理します。

1. PythonがPhase 1 JSONを読む
2. Pythonが `config/context_aliases.csv` を読む
3. Pythonが辞書照合で `context_label` 候補を付ける
4. PythonがAI分類用の入力データを作る
5. 実行時AIが分類案を返す
6. PythonがAI出力を検証し、原文を維持したままPhase 2 JSONへ保存する
7. Pythonが人間確認用Markdownを保存する

実行時AIは分類案を返すだけです。
ファイル保存、Discord、Notion、TickTickへの操作は行いません。

Phase 2本体のPythonスクリプト名は、実装時点で以下を候補にします。

- `topic-classifier/classify_topics.py`

`topic-classifier/test_context_aliases.py` は、辞書照合の検証用スクリプトであり、Phase 2本体ではありません。

Gemini APIは、実行時に `--use-ai` が指定された場合だけ呼び出します。
`GEMINI_API_KEY` が環境変数に存在していても、`--use-ai` がなければGeminiへ送信しません。
`--dry-run` は常にGeminiを呼ばず、辞書照合とフォールバック出力だけを確認します。

## Phase 2出力JSON仕様

トップレベルの主な項目:

| 項目 | 内容 |
|---|---|
| `generated_at` | Phase 2出力を生成したUTC時刻 |
| `source_file` | 入力に使ったPhase 1 JSON |
| `target_date` | 分類対象日 |
| `timezone` | Phase 1から引き継いだタイムゾーン |
| `classification_policy_version` | 分類ルールの版 |
| `topics` | トピック分類結果 |
| `unclassified_messages` | 分類できなかった投稿 |
| `warnings` | 注意事項 |
| `ai_called` | 実行時AI APIを呼び出したか |

`topics[]` の主な項目:

| 項目 | 内容 |
|---|---|
| `topic_id` | Phase 2内のトピックID |
| `topic_title` | AIが生成した短いトピック名 |
| `context_label` | 案件名、対象名、生活領域など、後続Phaseで文脈を失わないためのラベル |
| `raw_context_label` | 投稿本文からAIが読み取った補正前の文脈候補 |
| `context_match_status` | 文脈ラベルの確定状態 |
| `category` | 大分類 |
| `flags` | `task_hint` や `money_related` などの横断的な印 |
| `confidence` | `high`、`medium`、`low` のいずれか |
| `classification_reason` | 分類理由 |
| `messages` | このトピックに含まれる元投稿 |

`topics[].messages[]` には、Phase 1の投稿データを原文維持で入れます。
少なくとも `message_id`、`created_at_local`、`author_name`、`content`、`attachments` を保持します。

## AI利用の方針

AIには、Phase 1 JSONのうち分類に必要な投稿本文と添付メタデータを渡します。

実行時AI判断には、Geminiを第一候補として使います。
Codexは開発支援として扱い、Phase 2の実行時分類エンジンにはしません。

Gemini APIの認証情報は、環境変数 `GEMINI_API_KEY` から読みます。
モデル名は、環境変数 `MEMO_WORKFLOW_GEMINI_MODEL` から任意指定できます。
未指定の場合は、実装側の既定値を使います。

ただし、環境変数に `GEMINI_API_KEY` が存在していても、それだけではGeminiを呼びません。
Geminiを呼び出すには、実行時に `--use-ai` を明示します。

Geminiは公式のInteractions APIをRESTで呼び出し、`response_format` に `mime_type: "application/json"` とJSON Schemaを指定して、構造化出力を受け取ります。
Gemini呼び出しはPythonスクリプト内の小さな関数に閉じ込め、将来別AIへ切り替える場合も他の処理へ影響が広がりにくい形にします。

AIに渡すもの:

- 投稿ID
- 投稿時刻
- 投稿者名
- 投稿本文
- 添付ファイル名
- 添付content type
- 添付保存状態
- 添付ローカルパス
- Python側で辞書照合した `context_label` 候補
- `context_match_status`

AIに渡さないもの:

- Bot Token
- 認証情報
- 外部 `.env` のパス
- Discordへの書き込み権限
- NotionやTickTickの認証情報

AI出力は分類案として扱います。
保存、ファイル移動、状態変更、外部連携はアプリ側の処理で管理します。
辞書照合で確定できる `context_label` は、AI判断よりも人間が管理する `config/context_aliases.csv` を優先します。

## 実行時AIに期待する出力

実行時AIには、投稿本文を原文のまま扱い、分類結果だけをJSONで返すことを期待します。

AI出力の基本単位:

| 項目 | 内容 |
|---|---|
| `topic_title` | 短いトピック名 |
| `raw_context_label` | AIが読み取った文脈候補 |
| `category` | `work`、`health_lifestyle`、`personal`、`reference`、`uncategorized` のいずれか |
| `flags` | 初期flag候補から必要なもの |
| `confidence` | `high`、`medium`、`low` のいずれか |
| `classification_reason` | 分類理由 |
| `message_ids` | このトピックに含める元投稿ID |

実行時AIには、元投稿の本文を書き換えさせません。
本文、投稿時刻、投稿者、添付情報は、Python側がPhase 1 JSONから再結合します。

## AI失敗時のフォールバック

AI APIを呼び出せない場合、または返却JSONを検証できない場合でも、Phase 1の原文を失いません。

フォールバック方針:

- 処理を失敗としてログに残す
- 元投稿を `unclassified_messages` に残す
- 辞書照合で確定できた `context_label` がある場合は、警告付きで保持する
- Notion転記、`ticktick-task` 向けTODO候補JSON生成、TickTick APIへの登録、更新、削除、Discord書き込みは行わない

AI失敗時に空の成功結果を作らず、`warnings` に失敗理由を残します。

## 例外時の扱い

| 失敗箇所 | 扱い |
|---|---|
| 入力JSONが存在しない | 処理を止め、入力ファイル不足としてログに残す |
| 入力JSONの形式が違う | 処理を止め、形式不一致としてログに残す |
| 投稿が0件 | 空の分類結果を出力する |
| AI分類に失敗 | 元投稿を失わず、全件を `unclassified_messages` に残す |
| 一部投稿だけ分類不能 | 該当投稿だけ `unclassified_messages` に残す |
| 出力保存失敗 | 保存失敗としてログに残す |

## 完了条件

Phase 2は、以下を満たした時点で完了候補とします。

- Phase 1 JSONを入力として読める
- 元投稿の原文を変更せずに保持できる
- 投稿をトピック単位に分類できる
- 分類結果と元投稿の対応関係を追える
- 未分類投稿を失わずに残せる
- 後続Phase向けJSONを保存できる
- 人間確認用Markdownを保存できる
- AI分類失敗時に元投稿を失わない
- Notion転記、`ticktick-task` 向けTODO候補JSON生成、TickTick APIへの登録、更新、削除、Discord書き込みを混ぜていない

## 確認予定

初期検証では、`outputs/discord_messages_2026-06-27.json` を入力にして確認します。

確認すること:

- 文字投稿が分類されること
- 添付のみ投稿が失われないこと
- 画像、動画、PDFの `local_path` が維持されること
- Office系の `skipped` が維持されること
- 未分類が必要な場合に `unclassified_messages` に残ること
- Phase 3が読めるJSON構造になっていること
