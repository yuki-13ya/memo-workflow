# 文書インデックス

この文書は、`memo-workflow` プロジェクト内の文書の役割と参照ルールを管理します。

## 文書一覧

| ファイル | 役割 | 更新タイミング |
|---|---|---|
| `README.md` | プロジェクトの目的、全体構成、主要文書、実行手順の入口 | 入口情報や参照先が変わったとき |
| `AGENTS.md` | Codexが守る作業ルール | 作業ルールや安全方針が変わったとき |
| `docs/document-index.md` | 文書の役割、配置、参照ルール | 文書を追加、削除、役割変更したとき |
| `docs/app_policy.md` | 設計、AI利用、外部連携、認証情報管理の上位方針 | 上位方針を変更したとき |
| `docs/system_design.md` | プロジェクト全体の処理の流れ、処理主体、データ受け渡し、Phase間の関係を示す設計図 | 全体構成、処理主体、データフローが変わったとき |
| `docs/development_roadmap.md` | Phase構成、対象範囲、Notionルート / TODO候補ルートの境界 | Phase構成や順序が変わったとき |
| `docs/issues.md` | 未解決事項、確認事項、判断待ちの一覧 | 未解決事項が増えたとき、確認が進んだとき、判断が確定したとき |
| `docs/change-log.md` | 仕様変更、判断変更、読み替えの記録 | 仕様や判断を変更したとき |
| `docs/context_alias_registration_interface_note.md` | 文脈ラベル辞書を将来どのインターフェースで登録、更新するかの設計メモ | 辞書登録UIや候補生成フローの方針を変えるとき |
| `docs/phase1_discord_ingest.md` | Phase 1: Discord投稿取得の詳細仕様 | Phase 1の仕様や確認条件が変わったとき |
| `docs/discord_unprocessed_queue_spec.md` | Discord投稿を `message_id` 単位で未処理キュー管理する追加仕様 | 日次処理ではなく未処理回収方式へ拡張するとき |
| `docs/phase2_topic_classification.md` | Phase 2: 原文維持のトピック分類と後続ルートへ渡す文脈情報の詳細仕様 | Phase 2の仕様や確認条件が変わったとき |
| `docs/phase5_ticktick_todo_candidates.md` | Phase 5: `ticktick-task` 向けTODO候補JSON生成の設計仕様 | Phase 5の目的、責務、判断境界、受け渡し方針が変わったとき |
| `docs/phase5_todo_candidate_json_spec.md` | Phase 5: `ticktick-task` 向けTODO候補JSONの出力仕様 | Phase 5の出力JSON項目、必須項目、値、サンプル、バリデーション方針が変わったとき |
| `docs/phase5_ticktick_task_handoff.md` | Phase 5出力を `ticktick-task` 側へ渡すときの申し送り | Phase 5と `ticktick-task` 側レビュー、分解、差し戻しの境界が変わったとき |
| `config/context_aliases.csv` | Phase 2以降で使う文脈ラベル、別名、関連名、TickTickリスト名候補の辞書 | 案件名、呼び方、人名、リスト名候補が増減したとき |
| `context-alias-editor/` | `config/context_aliases.csv` を追加、編集、削除するローカルUI | 辞書編集方法やCSV項目が変わったとき |
| `run_context_alias_editor.cmd` / `run_context_alias_editor.ps1` | 文脈ラベル辞書編集UIのWindows用起動ファイル。既定URLは `http://127.0.0.1:8788/` | 起動方法やポートを変えたとき |
| `discord-ingest/queue_batch.py` | Discord未処理キューから後続Phase向けバッチJSONを出力し、TODO候補化済み状態を明示更新するCLI | 未処理キューの受け渡し方法を変えたとき |
| `.env.example` | 必要な環境変数名の一覧 | 必要な設定項目が変わったとき |

## 今後作成する文書

以下は作成予定の候補です。まだ存在しないため、既存文書一覧には含めません。

| ファイル | 想定する役割 |
|---|---|
| `docs/phase3_notion_markdown.md` | Phase 3: Notion貼り付け用Markdown生成の詳細仕様 |
| `docs/phase4_notion_api_export.md` | Phase 4: Notion API転記の詳細仕様 |

## 参照ルール

README.mdは入口案内です。詳細仕様、例外処理、出力形式、ログ方針はPhase仕様書に分けます。

作業開始時は、まずこの文書を見出し索引として確認します。
毎回すべての文書を全文で深掘りするのではなく、この文書で関連しそうな文書を選び、作業の影響範囲に応じて読む深さを決めます。

Phase単位の作業では、対象Phaseの仕様書を最初に確認します。

実装を追加する前に、`docs/system_design.md` で現在の作業位置を確認します。
確認の深さは作業の影響範囲に応じて調整し、軽微な作業で毎回全文を深掘りしません。

Phase 2の後続は、NotionルートとTODO候補ルートに分けて確認します。
NotionルートはNotion向けMarkdown生成とNotion API転記を扱い、TODO候補ルートは `ticktick-task` 向けTODO候補JSON生成までを扱います。
TickTickへの登録、既存TickTickタスクとの統合判定、人間確認CSV、OK済み候補の反映、作業ブロック化は `ticktick-task` 側の責務として扱います。

設計方針、AI利用、外部連携、認証情報管理で迷った場合は、`docs/app_policy.md` を優先します。

仕様変更や判断変更が発生した場合は、文書を直接書き換えるだけでなく、`docs/change-log.md` に理由と影響範囲を残します。

未解決事項、確認事項、判断待ちは `docs/issues.md` に集約します。
固定の仕様、全体設計、Phase境界、作業フローの本文には、未確定の詳細を混ぜすぎず、必要な場合は `docs/issues.md` への参照に留めます。

ベース文書では、作業時点に依存する表現を避けます。
範囲外の内容を書く場合は、「このPhaseで作らないもの」として書き、後続Phaseで実装済みになっても過去Phaseの境界として読める形にします。

## 作業別の読み先

| 作業内容 | 最初に確認する場所 | 必要に応じて確認する場所 |
|---|---|---|
| プロジェクト全体像、Phaseの現在位置を確認する | `docs/system_design.md` の「全体の流れ」「Phaseごとの役割」 | `docs/development_roadmap.md` の「全体の流れ」「Phase構成」「Phaseごとの非対象」 |
| Codexの作業ルールを確認する | `AGENTS.md` の「作業前に確認する文書」「ルート構造」「TickTick関連の制限」 | `docs/app_policy.md` の「設計の基本姿勢」「文書責務の基本ルール」 |
| 文書の置き場所を判断する | この文書の「文書一覧」「文書追加時の方針」 | `docs/app_policy.md` の「文書責務の基本ルール」 |
| Phase 1のDiscord取得を変更する | `docs/phase1_discord_ingest.md` の「対象範囲」「入力」「出力」「ログ」 | `docs/system_design.md` の「Phaseごとの役割」 |
| Discord取得を未処理キュー化する | `docs/discord_unprocessed_queue_spec.md` | `docs/phase1_discord_ingest.md`、`docs/system_design.md`、`docs/development_roadmap.md` |
| Phase 1の添付保存を変更する | `docs/phase1_discord_ingest.md` の「添付ファイルの扱い」「Phase 1出力JSON仕様」 | `docs/issues.md` のPhase 1関連イシュー |
| Phase 2の分類や出力を変更する | `docs/phase2_topic_classification.md` の「分類方針」「出力」「Phase 2出力JSON仕様」 | `docs/system_design.md` の「辞書とAIの順番」 |
| 文脈ラベル辞書を手で追加、編集、削除する | `run_context_alias_editor.cmd` でローカルUIを起動 | `docs/context_alias_registration_interface_note.md`, `config/context_aliases.csv` |
| AI利用、外部AI API呼び出し条件を確認する | `docs/app_policy.md` の「AI利用の方針」「認証情報管理」 | `docs/phase2_topic_classification.md` の「AI利用の方針」「AI失敗時のフォールバック」 |
| Notionルートを検討する | `docs/system_design.md` の「全体の流れ」「Phaseごとの役割」 | `docs/development_roadmap.md` の「Notionルート」「Notionルートの安全ルール」 |
| TODO候補ルートを検討する | `docs/system_design.md` の「全体の流れ」「Phaseごとの役割」 | `docs/development_roadmap.md` の「TODO候補ルート」「TODO候補ルートの安全ルール」 |
| Phase 5のTODO候補JSON生成方針を確認する | `docs/phase5_ticktick_todo_candidates.md` の「目的」「このPhaseの位置づけ」「ticktick-task との境界」 | `docs/system_design.md` の「全体の流れ」「Phaseごとの役割」、`docs/development_roadmap.md` の「Phase 5の完了条件」 |
| Phase 5の出力JSON項目を確認する | `docs/phase5_todo_candidate_json_spec.md` の「JSON全体構造」「item 1件ごとの項目」「サンプルJSON」 | `docs/phase5_ticktick_todo_candidates.md` の「出力」「ticktick-task との境界」 |
| `ticktick-task` 側との責務分担を確認する | `docs/system_design.md` の「全体の流れ」「Phaseごとの役割」 | `docs/phase5_ticktick_task_handoff.md`, `docs/app_policy.md` の「外部連携の方針」、`AGENTS.md` の「TickTick関連の制限」 |
| 未解決事項、確認事項、判断待ちを扱う | `docs/issues.md` | 判断が確定した後に、対象Phase仕様書、`docs/system_design.md`、`docs/change-log.md` |
| 仕様変更や判断変更の経緯を確認する | `docs/change-log.md` の該当日付 | 対象Phase仕様書、`docs/app_policy.md` |
| 環境変数や秘密情報の扱いを確認する | `docs/app_policy.md` の「認証情報管理」 | `.env.example`、対象Phase仕様書 |

## 文書内見出し索引

| ファイル | 主な見出し |
|---|---|
| `README.md` | 基本方針、主要文書、フォルダ構成、実行手順の入口 |
| `AGENTS.md` | 基本方針、プロジェクト責務、作業対象、作業前に確認する文書、文書の扱い、実装の進め方、ルート構造、Discord連携の制限、AI利用の扱い、Notion連携の制限、TickTick関連の制限、ログと認証情報、出力管理、実装状況と確認状況の区別、Git運用ルール、作業後の報告 |
| `docs/app_policy.md` | 設計の基本姿勢、文書責務の基本ルール、Phase単位の進行、AI利用の方針、処理主体の統一方針、外部連携の方針、認証情報管理、ログ方針、出力管理、実装状況と確認状況の区別、Git運用 |
| `docs/system_design.md` | このプロジェクトで作るもの、全体の流れ、処理主体、データの考え方、辞書とAIの順番、Phaseごとの役割、実装前の確認ルール、現時点のプロトタイプの扱い、未解決事項の扱い |
| `docs/development_roadmap.md` | 全体方針、全体の流れ、Phase構成、Phase 1の完了条件、Phase 2の入口と役割、Notionルート、TODO候補ルート、Phase 5の完了条件、後続Phaseの安全ルール、Phaseごとの非対象、今後作成するPhase仕様書 |
| `docs/issues.md` | 記録方針、書き方、未解決事項 |
| `docs/change-log.md` | 記録方針、日付別の変更履歴 |
| `docs/context_alias_registration_interface_note.md` | 背景、基本方針、想定する操作、登録フォームの項目、段階的な実装案、将来のレビューUIイメージ、決めておきたいこと、現時点の判断 |
| `context-alias-editor/` | CSV読み書き用ローカルサーバー、追加、編集、削除画面、保存時バックアップ |
| `docs/phase1_discord_ingest.md` | 目的、対象範囲、入力、実装ファイル、日付抽出方針、取得項目、添付ファイルの扱い、出力、Phase 1出力JSON仕様、ログ、DryRun / 読み取り専用検証、例外時の扱い、完了条件、Phase 1確認状況 |
| `docs/discord_unprocessed_queue_spec.md` | 目的、背景、基本方針、管理ファイル、キューJSON構造、状態、取得範囲、既存日付ファイルとの関係、後続Phaseへの渡し方、初期実装範囲 |
| `docs/phase2_topic_classification.md` | 目的、入力、対象範囲、原文維持ルール、分類方針、文脈保持ルール、文脈ラベルと別名辞書、添付の扱い、出力、実装単位、Phase 2出力JSON仕様、AI利用の方針、実行時AIに期待する出力、AI失敗時のフォールバック、例外時の扱い、完了条件、確認予定 |
| `docs/phase5_ticktick_todo_candidates.md` | 目的、このPhaseの位置づけ、入力、出力、抽出対象、抽出しないもの、候補ステータス、文脈保持ルール、人間確認の扱い、blockingHint の扱い、AI利用の方針、ticktick-task との境界、このPhaseでやらないこと、完了条件、後続で別途定義すること |
| `docs/phase5_todo_candidate_json_spec.md` | この文書の目的、前提となるPhase 5仕様書への参照、入力ファイル、出力ファイル、JSON全体構造、item 1件ごとの項目、sourceRefs、sourceContext、必須項目、任意項目、initialStatus の値、needsReview / reviewReason の扱い、blockingHint の扱い、元投稿・根拠情報の保持方法、ticktick-task 側へ渡してよい情報、ticktick-task 側へ渡さない情報、サンプルJSON、バリデーション方針、エラー時の扱い、この仕様で確定しないこと |
| `docs/phase5_ticktick_task_handoff.md` | Phase 5の役割、受け渡すファイル、受け渡しJSONの位置づけ、initialStatus の受け取り方、todo_candidate の考え方、hold_candidate の考え方、needsReview / reviewReason、humanDecision / humanMemo、分解と差し戻し、レビューで想定する判断、blockingHint の扱い、memo-workflow側で出さない項目、ticktick-task 側で確定してほしいこと、運用上の前提 |
| `config/context_aliases.csv` | 文脈ラベル、別名、関連名、TickTickリスト名候補を管理するCSV |
| `.env.example` | 必要な環境変数名の一覧 |

## 文書追加時の方針

新しい文書を追加する場合は、以下を確認します。

- README.mdに入れるべき入口情報か
- Phase仕様書に入れるべき詳細仕様か
- ロードマップに入れるべき予定か
- issuesに入れるべき未解決事項、確認事項、判断待ちか
- change-logに残すべき判断変更か
- 一時メモであり、正式文書にしない方がよい内容か

文書を増やす場合は、この文書にも役割を追加します。
