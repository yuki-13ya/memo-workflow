# 変更履歴

## 2026-09-13

### Memodumpの今すぐ同期UIを追加

- 登録済みの `Memodump Discord to Drive` タスクを任意のタイミングで起動するWindows UIを追加した
- 実行中、完了、新規投稿なし、エラー結果、新しく作成されたJSON名を表示する
- Memo-Routerのinboxをエクスプローラーで開く操作を追加した
- 認証情報と実行パスは複製せず、登録済みタスクの設定を利用する
- 登録済みタスクがない場合は、UIの「初期設定」から必要なパスを選択してタスク登録できる
- 日本語UIをWindows PowerShell 5.1で正しく読めるよう、UIスクリプトをUTF-8 BOM付きで保存する
- 起動時にUIを前面へ移し、ランチャーの黒いターミナル画面はすぐ閉じるようにする
- VBSの隠しランチャーを追加し、通常はターミナルを表示しない。UI起動前の障害だけを `logs/memodump_sync_ui_launch.log` へ記録する
- Windows PowerShell 5.1で初期設定値を確実に渡すため、登録スクリプト呼び出しを型確定済みの名前付き引数へ変更し、非登録の検証モードを追加する
- タスク登録処理をUI本体とは別のPowerShellプロセスへ隔離し、登録失敗がWinFormsのJIT例外ダイアログにならないようにする
- Windows PowerShell 5.1で失敗する `Split-Path -LiteralPath -Parent` を使わず、UIと同期本体の親フォルダ取得を.NET APIへ統一する
- 初期設定用の子PowerShellと登録済みタスクのPowerShellを非表示実行に統一し、同期中もUIだけを表示する

## 2026-09-12

### Memo-Router向け添付保存構造を追加

- Discord添付保存処理に `--attachment-root` を追加した
- 指定時は `<attachment-root>/<message_id>/<元ファイル名>` に保存し、JSONの `attachments[].local_path` に絶対保存先を残す
- `run_memodump_sync.ps1` は `Memo-Router/inbox` の兄弟 `attachments` を明示的に渡す
- オプション未指定時の従来保存構造は互換性のため維持した
- 添付保存の単体テストを追加し、同一投稿の複数画像が同じ `message_id` フォルダへ入ることを確認した

この文書は、`memo-workflow` プロジェクトの仕様変更、判断変更、読み替えルールを記録します。

## 記録方針

仕様や判断を変更した場合は、以下を記録します。

- 日付
- 対象ファイル
- 変更内容
- 変更理由
- 影響範囲
- 未確認事項

単なる誤字修正や表記整理は、必要に応じて記録します。

## 2026-09-11

### Google Drive受け渡し先をMemo-Routerへ変更

- 変更内容:
  - Google Drive側の作業フォルダ名変更に合わせ、受け渡し先を `Memo-Router/inbox` に変更した
  - `Memodump` をDiscord取得、ローカル保存、JSON生成、`MemoRouter` をGoogle Drive上のJSONから始まるブラウザ版ChatGPTの後続処理として責務を分けた
  - Google Drive側のREADMEとリポジトリ文書の表記を更新した
- 変更理由:
  - ローカル収集処理とブラウザチャットによる後続処理の所有範囲を名称でも区別するため
- 影響範囲:
  - WindowsタスクのDrive出力先
  - Google Drive側README
  - Discord取得、JSON形式、重複除外の挙動は変更しない

### Google Drive側のChatGPT向けREADMEを追加

- 対象ファイル:
  - `docs/drive_chatgpt_handoff.md`
  - `README.md`
  - `docs/document-index.md`
  - Google Drive同期フォルダの `Memo-Router/README.md`
- 変更内容:
  - Drive受け渡しフォルダの目的、フォルダの役割、JSON構造、生成タイミングを整理した
  - Discord原文をChatGPT自身への指示として実行しないことを明記した
  - 外部サービスへの書き込み、後続処理の完了判定、フォルダ移動の運用はMemodumpで定義しないことを明記した
- 変更理由:
  - Driveフォルダを開くブラウザ版ChatGPTが、ローカル実装を参照できなくても安全に判断できるようにするため
- 未確認事項:
  - ブラウザ版ChatGPTからのREADME参照
  - ブラウザチャット側の後続処理

## 2026-09-10

### 定期実行を未取得投稿の遡及取得へ修正

- 対象ファイル:
  - `discord-ingest/ingest_discord.py`
  - `discord-ingest/catch_up_discord.py`
  - `run_memodump_sync.ps1`
  - `tests/test_catch_up_discord.py`
  - `README.md`
  - `docs/document-index.md`
- 変更内容:
  - キュー内の最新 `createdAt` の前日から当日までを一度に取得する処理を追加した
  - 境界付近は再取得し、既存キューの `message_id` と照合して新規投稿だけを受け渡しバッチへ出力するようにした
  - 期間内の日付別JSONは従来どおり更新し、新規投稿が0件ならDriveへ何も渡さないようにした
  - Windows定期実行の入口を当日取得から遡及取得へ切り替えた
- 変更理由:
  - 数日または長期間実行できなかった場合も、Discord投稿を取りこぼさないという既存仕様に実装を合わせるため
- 未確認事項:
  - 実Discord APIによる長期間の初回遡及取得
  - Windowsタスクスケジューラによる次回の自動実行

### Google Drive同期フォルダへのJSON受け渡しを追加

- 対象ファイル:
  - `discord-ingest/publish_drive_handoff.py`
  - `run_memodump_sync.ps1`
  - `register_memodump_tasks.ps1`
  - `tests/test_publish_drive_handoff.py`
  - `README.md`
  - `docs/document-index.md`
  - `docs/change-log.md`
- 変更内容:
  - Discord取得とキュー更新が成功した後、完成済みの日付別JSONだけをGoogle Drive同期フォルダの指定先へコピーする入口を追加した
  - 投稿内容の安定ハッシュを `state/drive_handoff_state.json` に記録し、同じ内容を再実行した場合はコピーしないようにした
  - 対象日の投稿が0件の場合は `inbox` へコピーしないようにした
  - 同日中に投稿が増えた場合は、既存ファイルを上書きせず、新しい時刻付きファイルとしてコピーするようにした
  - コピー途中のファイルをChatGPTが読まないよう、一時ファイルへのコピー後に確定名へ置き換えるようにした
  - ログオン時と毎日20時に、ログオン中のユーザーとして一連処理を起動するタスク登録スクリプトを追加した
- 変更理由:
  - Notion API転記をローカル実装せず、Google Drive上のJSONをChatGPTへ安全に受け渡すため
  - ローカル出力を正本として残し、Drive同期停止時にもDiscord取得結果を失わないため
- 影響範囲:
  - Discord取得後のGoogle Drive受け渡しのみ
  - Notion書き込み、ChatGPT側の処理済み移動、既存のPhase 2 / Phase 5処理は変更しない
- 未確認事項:
  - 実際のDiscord API取得を含む一連実行
  - Google Drive for desktopでの同期完了
  - Windowsタスクスケジューラによる次回の自動実行

## 2026-08-02

### 未決定事項と仕様の扱いを作業ルールへ明記

- 対象ファイル:
  - `AGENTS.md`
  - `docs/change-log.md`
- 変更内容: 未決定事項を推測で補完しないこと、正本仕様書にない要件を実装時に追加しないこと、必要仕様が未決定なら実装を止めて確認事項として提示すること、提案と決定済み仕様を区別することを明記した。
- 変更理由: 既存ルールに同趣旨の規定はあったが、対象が個別ケースに寄っており、実装全般へ適用する共通原則としては解釈の余地があったため。
- 影響範囲: Codexの作業判断と仕様管理のみ。コード、外部API、実行時処理は変更しない。
- 未確認事項: なし。

## 2026-07-12

### Phase 5 TODO候補抽出をAI主経路へ整理

- 対象ファイル:
  - `README.md`
  - `docs/app_policy.md`
  - `docs/phase5_ticktick_todo_candidates.md`
  - `docs/phase5_todo_candidate_json_spec.md`
  - `docs/change-log.md`
  - `phase5-todo-candidates/export_todo_candidates.py`
  - `tests/test_phase5_action_extraction.py`
- 変更内容:
  - AIプロンプトを作るときは、禁止命令を中心にせず、望ましい作業方法、出力単位、判断基準、根拠の扱いを肯定文で指示する上位方針を追加した
  - 例文はAIの出力を例文の語彙や構造へ引っ張ることがあるため、抽象的な型、判断基準、出力項目の説明を優先し、例文は必要最小限にする方針を追加した
  - Phase 5では、自由文からTODO候補を抽出、分解する主経路としてAIを使う方針を明記した
  - Phase 2のGemini分類は、NotionルートとTODO候補ルートの共通入力を作るトピック分類であり、TODO候補1件ごとの分解や候補タイトル確定ではないことを整理した
  - `やること` 見出し、空行、箇条書き、改行などを機械的な固定ルールだけで解釈しようとせず、自由文の候補抽出はAIに寄せる方針にした
  - Python側の役割を、対象トピックの絞り込み、AI出力のJSONスキーマ検証、元投稿ID照合、辞書ラベル補正、安全側補正、`ticktick-task` 入力スキーマ保存に限定する方針を追加した
  - `--use-ai` 指定時にPhase 5でGeminiを呼び、AI抽出結果を既存のTODO候補JSONへ変換する実装を追加した
  - AI抽出結果をレビュー用候補へ変換する回帰テストを追加した
- 変更理由:
  - 禁止事項の列挙中心のプロンプトは、AIの出力を狭めすぎたり、意図しない萎縮を招いたりしやすいため
  - 具体例をむやみに入れると、モデルが例文の語彙、場面、分割粒度に寄りやすくなるため
  - Discord投稿は自由文であり、空行や箇条書き形式などの入力規則を前提にすると、運用側に不自然な制約が増えるため
  - Phase 2の分類結果は `task_hint` や文脈を付けるには有効だが、TODO候補単位の分解には粒度が粗く、Phase 5で再度文章判断が必要になるため
  - 機械的な抽出ルールを増やし続けるより、AI抽出とローカル検証に責務を分けた方が保守しやすいため
- 影響範囲:
  - Phase 5のTODO候補JSON / Markdown出力
  - `ticktick-task` 側へ渡す外部TODO候補レビュー入力
  - `--use-ai` を指定しない場合のローカルフォールバック経路
  - TickTick API、Notion API、Discord APIへの書き込み挙動は変更なし
- 未確認事項:
  - 2026-07-12実データではAI抽出を確認済みだが、複数成果物を含む短文の分割精度は継続確認する
  - AIなしフォールバック時の抽出精度と警告文言

## 2026-07-10

### TickTickリスト名の辞書反映方針を未解決事項へ追加

- 対象ファイル:
  - `docs/issues.md`
  - `docs/context_alias_registration_interface_note.md`
  - `docs/change-log.md`
- 変更内容:
  - TickTickから取得した既存リスト名を、`config/context_aliases.csv` の `ticktick_list_name` へどう反映するかを未解決事項として追加した
  - TickTickリスト名の読み取りは `ticktick-task` 側、文脈ラベル辞書への反映は `memo-workflow` 側、レビューUIへ渡す共有候補は親 `handoff/ticktick_list_names.json` とする方針を明記した
- 変更理由:
  - `ticktick-task` のレビューUIは `handoff/ticktick_list_names.json` を候補として読むが、その元になる辞書へTickTick既存リスト名を取り込む運用が未定義だったため
- 影響範囲:
  - 文書のみ。辞書編集UI、Phase 2分類、Phase 5 TODO候補生成、TickTick API連携のコード挙動は変更なし
- 未確認事項:
  - TickTick取得リストと `context_aliases.csv` の差分確認方法
  - `handoff/ticktick_list_names.json` の生成または更新手順

## 2026-07-05

### Phase 5の長文TODO抽出重複を修正

- 対象ファイル:
  - `phase5-todo-candidates/export_todo_candidates.py`
  - `tests/test_phase5_action_extraction.py`
  - `docs/phase5_ticktick_todo_candidates.md`
  - `docs/change-log.md`
- 変更内容:
  - Phase 5では、拾い漏れを減らすためにTODO候補をやや広めに抽出し、不要な候補は `ticktick-task` 側レビューで却下する方針を明記した
  - 1つのDiscord投稿が複数トピックに分かれた場合、同じ `message_id` と同じ行動文を複数回TODO候補化しないようにした
  - 各トピックのタイトルや分類理由と関係がある行動文だけを候補化するようにした
  - `伝えないと`、`買いたい`、`作らないと`、`方が先` をTODO候補として拾えるようにした
  - `買いたい` の直後に具体物の補足行がある場合、候補タイトルへ括弧付きで反映するようにした
  - `health_or_care` だけではTODO候補化せず、具体的な行動や必要性が読み取れる場合だけ候補化する方針にした
  - 2026-07-04の実データで、同じ相談タスクが重複して出る問題を、別TODO候補へ分かれる形に修正した
- 変更理由:
  - Phase 2で1投稿が複数トピックへ分かれたとき、Phase 5が各トピックから元投稿全文を再走査し、最初に見つかった同じTODO行を重複して出していたため
  - 日記部分とTODO部分が混在する長文メモでは、行動文単位で抽出し、日記だけの部分は候補化しない方がレビュー負担が少ないため
- 影響範囲:
  - Phase 5のTODO候補JSON / Markdown出力
  - `ticktick-task` へ渡す外部TODO候補レビュー入力
  - Discord取得、Phase 2分類、TickTick API書き込みは変更なし

## 2026-07-04

### Discord未処理キューのバッチ出力とTODO候補化済みマークを追加

- 対象ファイル:
  - `discord-ingest/queue_batch.py`
  - `tests/test_discord_queue_batch.py`
  - `README.md`
  - `docs/document-index.md`
  - `docs/discord_unprocessed_queue_spec.md`
  - `docs/change-log.md`
- 変更内容:
  - `python discord-ingest/queue_batch.py export-pending` で、キュー内の未TODO候補化メッセージだけをPhase 1互換のバッチJSON / Markdownへ出力できるようにした
  - `ignored` または `held` のメッセージ、すでに `todoCandidateGenerated = true` のメッセージはバッチ出力から除外するようにした
  - `python discord-ingest/queue_batch.py mark-todo-generated --source-file ...` で、Phase 5のTODO候補JSONまたは元バッチJSONを根拠に、対象メッセージを `todoCandidateGenerated = true` へ更新できるようにした
  - バッチJSON生成だけでは `todoCandidateGenerated` を進めない方針に修正
  - READMEと文書インデックスにキュー用CLIの入口を追加
- 変更理由:
  - バッチJSONを作っただけでTODO候補化済みにすると、Phase 2 / Phase 5が失敗した場合に未処理メッセージを取りこぼすため
  - 取得、バッチ抽出、TODO候補生成完了マークを分けることで、長期間未処理後の回収でも状態を安全に追えるようにするため
- 影響範囲:
  - Discord未処理キューのローカル状態管理
  - Phase 2 / Phase 5へ渡す入力JSON
  - Discord API、Notion API、TickTick APIへの書き込みは変更なし

### Discord未処理キューの初期実装を追加

- 対象ファイル:
  - `discord-ingest/ingest_discord.py`
  - `.gitignore`
  - `state/.gitkeep`
  - `tests/test_discord_message_queue.py`
  - `docs/discord_unprocessed_queue_spec.md`
  - `docs/phase1_discord_ingest.md`
  - `docs/change-log.md`
- 変更内容:
  - Discord取得スクリプトに `--merge-existing`、`--update-queue`、`--queue-path` を追加
  - 同じ日を再取得した場合、既存の日付別JSONと新規取得結果を `message_id` でマージするようにした
  - `state/discord_message_queue.json` に取得済みメッセージを登録または更新できるようにした
  - 既存キューの `todoCandidateGenerated`、`reviewed` などの状態を再取得で消さないようにした
  - キュー実データをGit管理対象外にし、空ディレクトリ維持用に `state/.gitkeep` を追加
  - マージとキュー更新のユニットテストを追加
- 変更理由:
  - 昼と夜の追記処理、翌朝処理、長期間未処理後の回収で、取得済みと後続処理済みを安全に分けるため
- 影響範囲:
  - Discord取得のローカル出力とローカル状態管理
  - Phase 2 / Phase 5の入力JSON構造は維持
  - Discord APIへの書き込み、Notion転記、TickTick書き込みは変更なし
- 未確認事項:
  - 未TODO候補化メッセージだけをバッチJSONへ出す処理
  - バッチJSON生成後に `todoCandidateGenerated = true` へ更新する処理

### Discord未処理キュー追加仕様を作成

- 対象ファイル:
  - `docs/discord_unprocessed_queue_spec.md`
  - `docs/phase1_discord_ingest.md`
  - `docs/document-index.md`
  - `docs/system_design.md`
  - `docs/development_roadmap.md`
  - `docs/change-log.md`
- 変更内容:
  - Discord投稿を日付だけではなく `message_id` 単位で管理する未処理キュー仕様を追加
  - `state/discord_message_queue.json` をローカル状態管理の正本とし、取得済み、TODO候補化済み、レビュー済み、Confirm済み、Execute済みを段階的に持てる方針を定義
  - 同日再取得、昼と夜の追記処理、1週間または1か月放置後の回収に対応する方針を文書化
- 変更理由:
  - 毎日定期的に処理できるとは限らず、日付単位の処理だけでは取得済み、未TODO候補化、レビュー済み、反映済みを安全に区別できないため
- 影響範囲:
  - 現時点では仕様追加のみ
  - Discord取得、TODO候補生成、TickTick API書き込みの実装は変更なし
  - 初期実装では、既存の日付別出力を維持したまま未処理キューを補助基盤として追加する

## 2026-07-03

### TickTick連携先の辞書項目名をリスト名へ変更

- 対象ファイル:
  - `config/context_aliases.csv`
  - `topic-classifier/context_aliases.py`
  - `topic-classifier/test_context_aliases.py`
  - `context-alias-editor/server.py`
  - `context-alias-editor/static/index.html`
  - `context-alias-editor/static/app.js`
  - `docs/phase2_topic_classification.md`
  - `docs/context_alias_registration_interface_note.md`
  - `docs/system_design.md`
  - `docs/document-index.md`
  - `docs/phase5_todo_candidate_json_spec.md`
  - `docs/change-log.md`
- 変更内容:
  - `context_aliases.csv` の列名を `ticktick_category` から `ticktick_list_name` へ変更
  - 辞書編集UIとPhase 2辞書照合出力のキーも `ticktick_list_name` に統一
  - 辞書編集UIの一覧で `category_hint` ではなく `ticktick_list_name` を表示
  - TickTick側の反映先を「カテゴリ」ではなく「リスト名」として文書化
- 変更理由:
  - TickTick側で実際に指定している単位はカテゴリではなくリストであり、未完成段階で用語と保存キーを正した方が後続のレビューUI、DryRun、Executeで混乱が少ないため
- 影響範囲:
  - 文脈ラベル辞書CSV、辞書編集UI、Phase 2辞書照合出力
  - Phase 2の `category` / `category_hint` は別概念のため変更なし
  - TickTick API書き込みは変更なし

### 文脈ラベル辞書UIの既定ポートを変更

- 対象ファイル:
  - `context-alias-editor/server.py`
  - `run_context_alias_editor.cmd`
  - `run_context_alias_editor.ps1`
  - `README.md`
  - `docs/document-index.md`
  - `docs/context_alias_registration_interface_note.md`
  - `docs/change-log.md`
- 変更内容:
  - 文脈ラベル辞書編集UIの既定ポートを `8787` から `8788` へ変更
  - 起動手順と関連文書のURL表記を `http://127.0.0.1:8788/` に更新
- 変更理由:
  - `ticktick-task` 側のTODO候補レビューUIも `8787` を使うため、辞書編集UIを開こうとしてTODO候補レビュー画面に当たる混乱を避けるため
- 影響範囲:
  - 文脈ラベル辞書編集UIのローカル起動URLのみ
  - Discord取得、分類、TODO候補JSON生成、TickTick API書き込みは変更なし

### Phase 5の所要時間候補を180分まで拡張

- 対象ファイル:
  - `docs/phase5_todo_candidate_json_spec.md`
  - `docs/phase5_ticktick_task_handoff.md`
  - `phase5-todo-candidates/export_todo_candidates.py`
  - `docs/change-log.md`
- 変更内容:
  - `estimatedMinutesCandidate` と `proposedItems[].estimatedMinutesCandidate` の許容値に `150`、`180` を追加
- 変更理由:
  - レビューUIで、2時間を少し超える親タスクを2.5hまたは3hの単発タスクとして扱いたいケースがあるため
- 影響範囲:
  - Phase 5のTODO候補JSON / Markdown出力
  - TickTick APIへの登録、更新、削除は変更なし

### Phase 5の分解案に項目ごとの所要時間候補を追加

- 対象ファイル:
  - `docs/phase5_todo_candidate_json_spec.md`
  - `phase5-todo-candidates/export_todo_candidates.py`
  - `docs/change-log.md`
- 変更内容:
  - `proposedItems` を文字列配列ではなく、`title`、`estimatedMinutesCandidate`、`order` を持つobject配列として出力するようにした
  - 分解案ごとに、本文や項目名から所要時間候補を付けるようにした
  - 親候補の `estimatedMinutesCandidate` と、分解後の各項目の時間候補は別物として扱う方針を仕様化した
- 変更理由:
  - レビュー画面で「親タスクとして登録する」場合と「分解して別タスクにする」場合の時間候補を分けて判断できるようにするため
- 影響範囲:
  - Phase 5のTODO候補JSON / Markdown出力
  - TickTick APIへの登録、更新、削除は変更なし

### Phase 5 TODO候補JSONに所要時間候補を追加

- 対象ファイル:
  - `docs/phase5_ticktick_todo_candidates.md`
  - `docs/phase5_todo_candidate_json_spec.md`
  - `docs/phase5_ticktick_task_handoff.md`
  - `phase5-todo-candidates/export_todo_candidates.py`
  - `docs/change-log.md`
- 変更内容:
  - Phase 5出力itemに `estimatedMinutesCandidate` を追加
  - 値は `null`、`15`、`30`、`45`、`60`、`90`、`120`、`150`、`180` のいずれかに限定
  - 本文中の明示時間を優先し、明示時間がない場合はローカルルールで控えめな時間候補を付けるようにした
  - 候補時間が作れない場合は `needs_duration_estimate` を `blockingHint` に追加するようにした
- 変更理由:
  - `ticktick-task` 側レビュー画面で、AI/ルール由来の作業時間候補を初期表示できるようにするため
- 影響範囲:
  - Phase 5のTODO候補JSON / Markdown出力
  - TickTick APIへの登録、更新、削除は変更なし

## 2026-07-02

### 文脈ラベル辞書のローカル編集UIを追加

- 対象ファイル:
  - `context-alias-editor/server.py`
  - `context-alias-editor/static/index.html`
  - `context-alias-editor/static/style.css`
  - `context-alias-editor/static/app.js`
  - `run_context_alias_editor.cmd`
  - `run_context_alias_editor.ps1`
  - `README.md`
  - `docs/document-index.md`
  - `docs/context_alias_registration_interface_note.md`
  - `docs/change-log.md`
- 変更内容:
  - `config/context_aliases.csv` を追加、編集、削除できるローカルUIを追加
  - 保存前にCSVを `outputs/context_alias_backups/` へバックアップするようにした
  - `canonical_name` の重複、`category_hint`、`flags_hint` の最低限の検証を追加
- 変更理由:
  - 文脈ラベル辞書を今後頻繁に育てるため、CSVを直接編集する負担と削除ミスのリスクを減らすため
- 影響範囲:
  - ローカル辞書編集のみ
  - Discord取得、Gemini分類、Notion転記、TickTick API書き込みは変更なし

### Phase 5で箇条書きTODOを行動単位に分割

- 対象ファイル:
  - `config/context_aliases.csv`
  - `docs/phase5_ticktick_todo_candidates.md`
  - `docs/phase5_todo_candidate_json_spec.md`
  - `docs/phase5_ticktick_task_handoff.md`
  - `phase5-todo-candidates/export_todo_candidates.py`
  - `docs/change-log.md`
- 変更内容:
  - 1投稿内に複数の箇条書きTODOがある場合、投稿全体を1候補に丸めず、行動単位に分けて出力するようにした
  - 分割候補では、トピック全体の `context_label` や `flags` を無条件に継承せず、行ごとに辞書照合とフラグ付けを行う方針へ変更
  - `sourceContext.extractionMode` により、トピック単位か行単位かを参照できるようにした
  - `講座A` という本文上の呼び名でも `講座A` に照合できるよう、別名辞書へ追加
- 変更理由:
  - 1投稿内に複数文脈のTODOが混ざる場合、投稿全体の文脈を全候補へかけると誤分類や過剰な保留が起きるため
  - `ticktick-task` 側レビューに渡す前に、明確な箇条書きTODOは候補単位で分けた方が確認しやすいため
- 影響範囲:
  - Phase 5のTODO候補JSON / Markdown出力
  - Phase 2分類、Discord取得、Notion転記、TickTick API書き込みは変更なし

### 仕様書内の実案件名サンプルを仮名化

- 対象ファイル:
  - `docs/phase2_topic_classification.md`
  - `docs/phase5_ticktick_todo_candidates.md`
  - `docs/phase5_todo_candidate_json_spec.md`
  - `docs/phase5_ticktick_task_handoff.md`
  - `docs/change-log.md`
- 変更内容:
  - 仕様やサンプルに出ていた実案件名を、`株式会社A`、`店舗B`、`講座C`、`コミュニティD` などの仮名例へ置換
  - 実運用に必要な文脈辞書 `config/context_aliases.csv` は実データとして維持
- 変更理由:
  - 仕様例が特定案件中心に読まれ、今後の設計や実装判断に偏りが出ることを避けるため
- 影響範囲:
  - 仕様書とサンプル表現のみ
  - 実運用の辞書、過去の変更履歴、既存出力ファイル内の実データは対象外

### Phase 5 TODO候補JSONをticktick-task入力スキーマへ整合

- 対象ファイル:
  - `docs/phase5_todo_candidate_json_spec.md`
  - `docs/phase5_ticktick_task_handoff.md`
  - `docs/document-index.md`
  - `phase5-todo-candidates/export_todo_candidates.py`
  - `docs/change-log.md`
- 変更内容:
  - Phase 5出力JSONを `ticktick-task/docs/todo_candidate_intake_schema.md` の外部TODO候補入力スキーマへ合わせた
  - トップレベルの `candidates` を `items` に変更
  - `candidateId`、`status`、`title`、`description`、`evidenceText`、`sourcePostIds` / `sourcePostTimes`、`humanReviewRequired` を、`sourceId`、`initialStatus`、`proposedTitle`、`proposedDescription`、`sourceText`、`sourceRefs`、`needsReview` へ整理
  - Phase 2由来の文脈情報を `sourceContext` にまとめる方針へ変更
  - `humanDecision` と `humanMemo` を外部入力時点の空欄として付与する方針を追加
  - `matchType`、`classification`、`taskId`、`projectId` など `ticktick-task` 側で確定する項目をPhase 5出力に含めない方針を明記
- 変更理由:
  - `ticktick-task` 側で、外部TODO候補レビュー、統合判定レビュー、作業ブロック分類レビューを共通レビュー構造へ流せるようにするため
  - `memo-workflow` 側の内部項目名ではなく、下流の受け入れ契約に沿ったJSONをPhase 5の正本出力にするため
- 影響範囲:
  - Phase 5のローカルJSON / Markdown / ログ出力
  - Phase 5の出力JSON仕様と `ticktick-task` 側申し送り
  - TickTick API書き込み、既存TickTickタスクとの統合判定、人間確認CSV、Notion処理、Discord書き込みは変更なし

### memo-automation-suite の作業分担ルールを追加

- 対象ファイル:
  - `AGENTS.md`
  - `docs/change-log.md`
  - `D:\Automation-Projects\memo-automation-suite\handoff\README.md`
- 変更内容:
  - `memo-automation-suite` 全体の開発方針、Phase構成、上流ワークフロー整理は原則として `memo-workflow` 側で扱う方針を追加
  - TickTickタスクの登録、統合、レビュー、分解、差し戻し、作業ブロック分類など、タスク関連に特化した設計と実装は `ticktick-task` 側で扱う方針を追加
  - `memo-workflow` と `ticktick-task` の間の申し送り、受け渡しメモ、移行メモは親フォルダ直下の `handoff` に格納する方針を追加
- 変更理由:
  - `memo-workflow` と `ticktick-task` を共通親フォルダ配下へ整理したため、今後の作業場所と申し送り置き場を明確にするため
- 影響範囲:
  - 作業ルールと申し送り置き場の整理のみ
  - 実装、Phase 5出力JSON、TickTick API処理、Notion処理、Discord処理の変更はなし

## 2026-07-01

### Phase 5のTODO候補判定方針とticktick-task申し送りを追加

- 対象ファイル:
  - `docs/phase5_ticktick_todo_candidates.md`
  - `docs/phase5_todo_candidate_json_spec.md`
  - `docs/phase5_ticktick_task_handoff.md`
  - `docs/document-index.md`
  - `docs/issues.md`
  - `README.md`
  - `docs/change-log.md`
- 変更内容:
  - Phase 5では、行動が読み取れる投稿をTODO候補として広めに拾う方針を追加
  - 「考える」「決める」「確認する」も、対象や目的が読み取れる場合は行動として扱う方針を追加
  - 粒度が粗いことだけを理由に `hold_candidate` へ寄せず、後続の `ticktick-task` 側レビューで却下、編集、分解できる前提を追加
  - `hold_candidate` は、文脈、対象、担当、登録可否などに人間判断が必要で、誤登録や混乱が起きそうな候補に限定する方針へ整理
  - Phase 5出力を `ticktick-task` 側へ渡すときの申し送り文書を追加
  - ISS-008を判断済みに更新
- 変更理由:
  - Phase 5で過度に保守的な分類へ寄せすぎず、候補出し係として広めに拾い、承認、却下、編集、分解、差し戻しは `ticktick-task` 側レビューで扱う境界を明確にするため
- 影響範囲:
  - Phase 5の候補判定方針と文書上の責務境界
  - Phase 5実装、TickTick API書き込み、`ticktick-task` 側ファイル、Notion処理、Discord書き込みの変更はなし

### Phase 5 TODO候補JSON生成の最小実装を追加

- 対象ファイル:
  - `phase5-todo-candidates/export_todo_candidates.py`
  - `README.md`
  - `docs/change-log.md`
- 変更内容:
  - Phase 2分類JSONを読み、`docs/phase5_todo_candidate_json_spec.md` に沿った `ticktick-task` 向けTODO候補JSONを出力するPhase 5 CLIを追加
  - `task_hint` が付いたトピックを中心に、ルールベースで `todo_candidate` または `hold_candidate` を生成
  - `--include-non-todo` 指定時に、候補外トピックを `non_todo` として残せるようにした
  - JSON必須項目、`status`、`sourcePostIds`、`humanReviewRequired`、`candidateId` の最低限バリデーションを追加
  - 人間確認用Markdownと処理ログをローカル出力できるようにした
- 変更理由:
  - Phase 5の最小実装として、外部サービスへ書き込まずにTODO候補JSONを安定して生成できる入口を用意するため
- 影響範囲:
  - Phase 5のローカルJSON / Markdown / ログ出力
  - AI API呼び出し、TickTick API書き込み、既存TickTickタスクとの統合判定、人間確認CSV、Notion処理、Discord書き込み、`ticktick-task` 側ファイルの変更はなし

### Phase 5 TODO候補JSON仕様を追加

- 対象ファイル:
  - `docs/phase5_todo_candidate_json_spec.md`
  - `docs/document-index.md`
  - `README.md`
  - `docs/change-log.md`
- 変更内容:
  - Phase 5で `ticktick-task` 側へ渡すTODO候補JSONの全体構造、候補1件ごとの項目、必須項目、任意項目、`status`、人間確認、`blockingHint`、根拠情報、サンプルJSON、バリデーション方針を別文書として定義
  - `blockingHint` は `ticktick-task` 側の正式な `classification` ではなく、Phase 5から渡す参考情報として定義
  - `docs/document-index.md` と READMEの主要文書一覧に、出力JSON仕様書への参照を追加
- 変更理由:
  - Phase 5本体仕様で未確定としていた出力JSONの詳細項目とサンプルを、実装前に参照できる形へ分離するため
- 影響範囲:
  - Phase 5の出力JSON仕様
  - 実装、Pythonスクリプト、AIプロンプト、AI API呼び出し、TickTick API書き込み処理、Notion処理、`ticktick-task` 側ファイルの変更はなし

### Phase 5仕様書を文書一覧に反映

- 対象ファイル:
  - `docs/phase5_ticktick_todo_candidates.md`
  - `docs/document-index.md`
  - `README.md`
  - `docs/change-log.md`
- 変更内容:
  - 追加済みの `docs/phase5_ticktick_todo_candidates.md` を、Phase 5: `ticktick-task` 向けTODO候補JSON生成の設計仕様として文書一覧に追加
  - `docs/document-index.md` の「今後作成する文書」からPhase 5仕様書を外し、未作成扱いを解消
  - READMEの主要文書一覧にPhase 5仕様書を追加
- 変更理由:
  - Phase 5仕様書が作成済みになったため、入口文書と索引から正しく参照できるようにするため
- 影響範囲:
  - 文書参照先と変更履歴のみ
  - Phase 5仕様書本文、実装、出力JSON詳細仕様、AIプロンプト、バリデーション仕様、TickTick API書き込み処理の変更はなし

### 2ルート構造とticktick-task責務分担へ整理

- 対象ファイル:
  - `README.md`
  - `AGENTS.md`
  - `docs/app_policy.md`
  - `docs/system_design.md`
  - `docs/development_roadmap.md`
  - `docs/document-index.md`
  - `docs/change-log.md`
- 変更内容:
  - `memo-workflow` の責務を、Discord取得、原文維持の分類、Notion向け出力、`ticktick-task` 向けTODO候補JSON生成を担当する上流プロジェクトとして整理
  - Phase 2後に Notionルート / TODO候補ルート へ分岐する構造へ変更
  - Notionルートでは、Notion貼り付け用Markdown生成とNotion API転記を扱う方針に整理
  - TODO候補ルートでは、TickTick本体への直接書き込みを行わず、`ticktick-task` 向けTODO候補JSONを出力する方針に変更
  - TickTickへの登録、既存TickTickタスクとの統合判定、人間確認CSV、OK済み候補の反映、作業ブロック化、作業ブロック用タスク出力は `ticktick-task` 側の責務として分離
  - Phase 6は独立Phaseにせず、`ticktick-task` 受け渡し確認をPhase 5の完了条件に含める方針に変更
- 判断理由:
  - `ticktick-task` 側の設計が先に具体化し、TickTick登録、統合判定、人間確認、作業ブロック化を安全に扱う中核プロジェクトとして整理されたため
  - `memo-workflow` 側ではTickTick本体へ直接書き込まず、後続処理へ渡せるTODO候補JSON生成までを担当する形にすると、責務境界が明確になるため
- 影響範囲:
  - プロジェクト全体のPhase構成と文書上の責務分担
  - NotionルートとTODO候補ルートの読み分け
  - Phase 5の位置づけ
  - 実装変更、既存出力JSON形式変更、TickTick API書き込み処理追加はなし
- 今後の対応:
  - Phase 3、Phase 4、Phase 5に着手する直前に、それぞれのPhase仕様書を作成する
  - `ticktick-task` 側との受け渡し確認は、Phase 5の完了条件として扱う

## 2026-06-30

### 生活タスクの分類と辞書登録基準を追記

- 対象ファイル:
  - `docs/phase2_topic_classification.md`
  - `docs/context_alias_registration_interface_note.md`
  - `docs/change-log.md`
- 内容:
  - 庭掃除、家の片付け、買い物、家族との約束などの生活タスクは、健康管理や仕事案件でない限り `personal` に分類する方針を追加
  - 生活タスクが予定化、時間確保、作業候補になりそうな場合は、categoryを増やさず `task_hint` や `schedule_related` を付ける方針を追加
  - 辞書登録の対象を、カテゴリー分類、文脈保持、タスク候補、外部連携先の判断に影響するものへ限定する方針を追加
- 理由:
  - 辞書が生活に出てくる単語帳として膨らみすぎることを避けるため
  - 生活タスクを `personal` category に収め、必要な性質だけ flags で表すため
- 影響範囲:
  - Phase 2分類方針
  - 将来の辞書登録インターフェース方針
  - 実装変更はなし

### 文脈ラベル辞書の表記ゆれとAI補足抑制を反映

- 対象ファイル:
  - `config/context_aliases.csv`
  - `topic-classifier/classify_topics.py`
  - `docs/phase2_topic_classification.md`
  - `docs/change-log.md`
- 内容:
  - `コミュニティA` を追加し、`コミュニティA`、`コミュニティA`、`コミュニティA` を同じ文脈として扱うようにした
  - `講師A`、`講師A`、`講師A`、`講師A` を `講座A` の文脈として追加
  - 新規追加した `コミュニティA` と `講座A` のTickTickリスト名候補は、既存リスト名未確認のため空欄にした
  - `講師A` 系の表記を `教室B` から外した
  - `講師B`、`講師B`、`講師B` を `教室B` の文脈として整理した
  - Phase 2仕様書内の辞書例から、古い `教室B` と `講師A` の組み合わせを削除し、`講座A` の例を追加
  - Phase 2のAIプロンプトと仕様に、本文にない場所、関係、所属、理由を `topic_title` や `classification_reason` に推測で足さない方針を追加
- 理由:
  - `講師A` と `講師B` が別文脈であり、辞書で誤って同一扱いされていたため
  - `庭` の投稿に対してAIが本文にない `実家` を補足したため
- 影響範囲:
  - Phase 2の辞書照合
  - Phase 2のAI分類プロンプト
  - Notion転記、TickTick連携、Discord書き込みは変更なし

### 文脈ラベル辞書登録インターフェースの設計メモを追加

- 対象ファイル:
  - `docs/context_alias_registration_interface_note.md`
  - `docs/document-index.md`
  - `docs/change-log.md`
- 内容:
  - 将来的に `context_aliases.csv` をどう登録、更新していくかの設計メモを追加
  - 分類結果レビューから辞書へ昇格する流れを基本方針として記録
  - 既存ラベルに追加、新規ラベル作成、辞書に入れない、今回だけ保留の操作案を整理
  - 最初は辞書候補Markdown、次に簡易レビューUI、必要になればSQLiteなどへ移行する段階案を記録
- 理由:
  - 開発中はCSV直接編集でよいが、運用時に辞書が増えても人間が無理なく登録できるインターフェース方針を残すため
  - 後続実装時に、AIが辞書を直接更新せず、人間確認を挟む設計意図を見失わないようにするため
- 影響範囲:
  - 将来設計メモと文書インデックスのみ
  - 実装変更はなし

### 未解決事項をイシュー一覧へ分離

- 対象ファイル:
  - `docs/issues.md`
  - `docs/document-index.md`
  - `docs/app_policy.md`
  - `docs/system_design.md`
  - `README.md`
  - `AGENTS.md`
  - `docs/change-log.md`
- 内容:
  - 未解決事項、確認事項、判断待ちを集約する `docs/issues.md` を追加
  - 固定仕様、全体設計、Phase境界、作業フローに未確定の詳細を混ぜすぎない方針を追加
  - `docs/system_design.md` の未決事項一覧を、`docs/issues.md` 参照へ変更
  - Phase 1仕様書に残っていた未確認事項を `docs/issues.md` へ移し、仕様書側は参照に変更
  - 作業開始時は `docs/document-index.md` を見出し索引として使い、関連文書だけを影響範囲に応じて確認する方針を明記
  - AGENTS.mdに、全体設計と現在位置を確認してから実装し、設計が粗い場合は先に整理するルールを明記
- 理由:
  - 基本情報、全体フロー、実装状況、未解決事項が混ざり、Phase進行後に意味の壊れる修正が発生することを避けるため
  - AIが目の前の実装だけを進めて全体整合性を崩すことを防ぎ、人間が後から追える手順で開発するため
- 影響範囲:
  - 文書運用ルール
  - 実装変更はなし

### 文書インデックスの索引粒度を追加

- 対象ファイル:
  - `docs/document-index.md`
  - `docs/change-log.md`
- 内容:
  - `docs/document-index.md` に作業別の読み先を追加
  - 各文書の主な見出しを集めた文書内見出し索引を追加
- 理由:
  - 作業開始時に毎回すべての文書を深掘りせず、関連する文書と見出しだけを選べるようにするため
  - 全体設計の確認と、過剰な読み込みを両立するため
- 影響範囲:
  - 文書運用ルール
  - 実装変更はなし

### Phase 2確認用Markdownをレビューしやすい形に整理

- 対象ファイル:
  - `topic-classifier/classify_topics.py`
  - `docs/phase2_topic_classification.md`
  - `docs/change-log.md`
- 内容:
  - Phase 2の確認用Markdownに、トピック数、投稿数、未分類数、要確認候補数を追加
  - category と flags の件数を確認できるサマリを追加
  - `needs_review`、`low` confidence、`uncategorized`、AI推定文脈、`task_hint` だが `context_label` が空のトピックを「Review Needed」として先に確認できる形にした
  - 各トピックに `raw_context_label`、review points、辞書照合候補、添付メタデータを表示するようにした
- 理由:
  - Phase 2のJSON構造は後続Phase向けに維持しつつ、人間が分類結果の怪しい箇所から確認できるようにするため
  - 文脈ラベル辞書の不足やAI推定だけの分類を、分類結果の本文を読まずに見つけやすくするため
- 影響範囲:
  - Phase 2の確認用Markdown生成のみ
  - 分類ロジック、Gemini呼び出し条件、JSON仕様、Notion転記、TickTick連携、Discord書き込みは変更なし
- 未確認事項:
  - 実運用でどの review point を必ず手動確認にするかは、今後の実データ確認で調整する

## 2026-06-28

### ロードマップの時点依存表現を整理

- 対象ファイル:
  - `docs/development_roadmap.md`
  - `docs/app_policy.md`
  - `docs/document-index.md`
  - `docs/change-log.md`
- 内容:
  - `docs/development_roadmap.md` の「今回作らないもの」を「Phaseごとの非対象」に変更
  - 「今回作らない」という初期作成時の文脈を削除し、各Phaseで混ぜないものを表で整理
  - ベース文書では「今回」「現時点」など時点依存の表現を避ける方針を追加
  - 範囲外の記述は「このPhaseで作らないもの」として書き、後続Phaseで実装済みになっても過去Phaseの境界として読める形にする方針を追加
- 理由:
  - Phaseが進んだ後に、ロードマップや上位文書が古い作業時点の記述で矛盾しないようにするため
  - 後続Phaseで実装済みになった内容を、過去Phaseの境界説明として安定して残せるようにするため
- 影響範囲:
  - 文書運用ルール
  - ロードマップの表現整理
  - 実装変更はなし

### 設計確認の深さを調整

- 対象ファイル:
  - `docs/app_policy.md`
  - `docs/document-index.md`
  - `docs/system_design.md`
  - `docs/change-log.md`
- 内容:
  - 実装前に全体設計を確認する方針は維持しつつ、毎回全文を深掘りしないルールに変更
  - 軽い確認、通常確認、深い確認の3段階を追加
  - 未決事項が今回の作業に直接関係しない場合は、存在するだけで作業を止めない方針を追加
- 理由:
  - 全体設計を見失わないことと、小さな作業で過剰確認にならないことを両立するため
  - AIが「全部確認」と解釈して過剰に読み込みすぎることを避けるため
- 影響範囲:
  - 作業前確認ルール
  - 実装変更はなし

### 外部AI APIの明示実行ルールを追加

- 対象ファイル:
  - `docs/app_policy.md`
  - `docs/phase2_topic_classification.md`
  - `topic-classifier/classify_topics.py`
  - `docs/change-log.md`
- 内容:
  - 環境変数に認証情報が存在していても、それだけでは外部AI APIを呼ばない方針を追加
  - Phase 2のGemini呼び出しには `--use-ai` を必須にした
  - `--dry-run` は常にGeminiを呼ばない方針を明記
  - Phase 2出力に `ai_called` を追加し、外部AI APIを呼んだかどうかを記録するようにした
- 理由:
  - 実行環境に既存の `GEMINI_API_KEY` が見えている場合でも、人間の明示許可なしに外部AI APIへ送信しないようにするため
  - 認証情報の存在と、外部API実行の許可を分離するため
- 影響範囲:
  - Phase 2実行時のAI呼び出し条件
  - 認証情報管理方針
  - Notion転記、TickTick連携、Discord書き込みは未実装

### Phase 2のGemini実データ分類を確認

- 対象ファイル:
  - `topic-classifier/classify_topics.py`
  - `outputs/topic_classification_2026-06-28.json`
  - `outputs/topic_classification_2026-06-28.md`
  - `docs/development_roadmap.md`
  - `docs/system_design.md`
  - `docs/change-log.md`
- 内容:
  - `outputs/discord_messages_2026-06-28.json` を入力にして、GeminiによるPhase 2分類を実行
  - 9件の投稿から9件のトピックを作成
  - 未分類0件、警告0件を確認
  - 株式会社A、店舗B、教室Bの `context_label` が辞書照合結果として維持されることを確認
  - Phase 2の状態をロードマップ上で「初期実装・実データ分類確認済み」に更新
- 理由:
  - Phase 2の設計どおり、Pythonによる辞書照合、Geminiによる分類案、Pythonによる出力保存がつながるか確認するため
- 影響範囲:
  - Phase 2初期実装
  - Notion転記、TickTick連携、Discord書き込みは未実装

### Phase 2の実行時AIをGemini第一候補に確定

- 対象ファイル:
  - `.env.example`
  - `docs/app_policy.md`
  - `docs/system_design.md`
  - `docs/phase2_topic_classification.md`
  - `topic-classifier/classify_topics.py`
  - `docs/change-log.md`
- 内容:
  - Phase 2の実行時AIをGemini第一候補として確定
  - `GEMINI_API_KEY` と `MEMO_WORKFLOW_GEMINI_MODEL` を `.env.example` に追加
  - Gemini Interactions APIをRESTで呼び、`response_format` とJSON Schemaで構造化出力を受け取る方針に整理
  - Gemini呼び出しをPythonスクリプト内の `call_gemini()` に閉じ込め、将来の差し替え余地を残す形にした
- 理由:
  - 既存の別プロジェクトでGemini利用経験があり、新しい契約や認証管理を増やさずに済むため
  - 今回のPhase 2では、雑メモを定義済みカテゴリへ分類しJSONで返す構造化出力が重要なため
  - Gemini公式ドキュメントでも、構造化出力は分類やツール/API向けデータ生成に向くとされているため
- 影響範囲:
  - Phase 2仕様
  - Phase 2本体候補スクリプト
  - Notion転記、TickTick連携、Discord書き込みは未実装

### Phase 2のAIプロバイダ確定を保留に戻す

- 対象ファイル:
  - `.env.example`
  - `docs/app_policy.md`
  - `docs/system_design.md`
  - `docs/phase2_topic_classification.md`
  - `topic-classifier/classify_topics.py`
  - `docs/change-log.md`
- 内容:
  - GeminiをPhase 2の確定プロバイダとして扱う記述を取り下げ
  - AIプロバイダ、モデル、呼び出し方式、認証情報名は未決事項として扱う方針に修正
  - `.env.example` から未確定の `GEMINI_API_KEY` を削除
  - Phase 2本体候補スクリプトは、現時点ではAI APIを呼ばず辞書照合とフォールバック出力だけを行う形に修正
- 理由:
  - 既存TickTick側でGemini呼び出し実装を確認できず、既存実装流用を前提にできないため
  - 未確認のAI API仕様を土台にしないため
- 影響範囲:
  - Phase 2仕様
  - Phase 2本体候補スクリプト
  - 外部AI API呼び出しは未実装

### Phase 2のGemini利用契約を追記

注記: この判断は、後続の「Phase 2のAIプロバイダ確定を保留に戻す」で見直し済みです。
Geminiを確定プロバイダとして扱わず、AIプロバイダ、モデル、呼び出し方式、認証情報名は未決事項に戻しています。

- 対象ファイル:
  - `.env.example`
  - `docs/phase2_topic_classification.md`
  - `docs/system_design.md`
  - `docs/change-log.md`
- 内容:
  - Phase 2の入力に `config/context_aliases.csv` を明記
  - Phase 2実装の処理順序を追加
  - Gemini APIの認証情報名を `GEMINI_API_KEY` として追加
  - Geminiに渡すもの、渡さないもの、期待するJSON出力を整理
  - AI失敗時は元投稿を失わず `unclassified_messages` に残すフォールバック方針を追加
- 理由:
  - Phase 2実装前に、Python、辞書照合、Geminiの責務境界を明確にするため
  - ノンプログラマーでも、どの処理が何を担当するか追えるようにするため
- 影響範囲:
  - Phase 2仕様
  - 環境変数名の追加
  - 実装変更は未実施

### 全体設計図を追加

- 対象ファイル:
  - `docs/system_design.md`
  - `docs/document-index.md`
  - `docs/app_policy.md`
  - `docs/change-log.md`
- 内容:
  - プロジェクト全体の流れ、処理主体、データ受け渡し、Phaseごとの役割をまとめる設計図を追加
  - Phase実装前に `docs/system_design.md` を確認するルールを追加
  - `topic-classifier/test_context_aliases.py` はPhase 2本体ではなく、辞書照合の検証用スクリプトとして扱うことを明記
  - 未決事項を設計図にまとめ、推測で実装を広げない方針を補強
- 理由:
  - Phaseごとに部品を足す進め方ではなく、先に全体設計を確認してから実装する進め方へ戻すため
  - ノンプログラマーでも、どの処理がどこで何をするのか追える状態にするため
- 影響範囲:
  - 文書構成と作業ルール
  - 実装変更はなし

### 処理主体の統一方針を追加

- 対象ファイル:
  - `docs/app_policy.md`
  - `docs/phase2_topic_classification.md`
  - `docs/change-log.md`
- 内容:
  - Codex、Pythonスクリプト、Gemini、人間の役割分担を上位方針に追加
  - Codexは開発支援、Pythonは実行と外部API操作、Geminiは実行時AI判断の第一候補として整理
  - 外部サービスへの読み書きはAIに直接任せず、Pythonスクリプト側で制御する方針を追加
  - Phase 2の実行時AI判断は、原則Geminiを第一候補にする方針を追加
  - 辞書照合などルールで確定できる処理はAIより先にPython側で行う方針を追加
- 理由:
  - Phaseごとに処理主体やAIプロバイダがばらばらになることを避けるため
  - 既存のTickTick関連運用との整合性を取りやすくするため
  - AI判断と外部サービスの状態変更を分離し、誤登録や誤更新を避けるため
- 影響範囲:
  - プロジェクト全体の設計方針
  - Phase 2仕様
  - 実装変更は未実施

### 文脈ラベル辞書の検証スクリプトを追加

- 対象ファイル:
  - `topic-classifier/test_context_aliases.py`
  - `docs/change-log.md`
- 内容:
  - `config/context_aliases.csv` を読み、Phase 1 JSONの本文に対して文脈ラベル候補を照合する検証スクリプトを追加
  - 照合結果を `outputs/context_alias_test_YYYY-MM-DD.json` と `outputs/context_alias_test_YYYY-MM-DD.md` に保存する形にした
  - Phase 2のAI分類本体ではなく、辞書の読み取りと文脈補正だけを確認する位置づけにした
- 理由:
  - AI分類を作り込む前に、別名辞書の形式と照合ルールが実データに対して機能するか確認するため
- 影響範囲:
  - 検証用スクリプトのみ
  - Discord取得、AI分類、Notion転記、TickTick連携は未実装

### 文脈ラベル辞書CSVを追加

- 対象ファイル:
  - `config/context_aliases.csv`
  - `docs/phase2_topic_classification.md`
  - `docs/document-index.md`
  - `docs/change-log.md`
- 内容:
  - 文脈ラベル、別名、関連名、TickTickリスト名候補を管理するCSVを追加
  - CSVはExcelやGoogle Sheetsで開ける管理ファイルとして扱う方針を追加
  - `aliases`、`related_names`、`flags_hint` の複数値はセミコロン区切りにする方針を追加
  - 初期行として、株式会社A、教室B、店舗Bを追加
- 理由:
  - 会社名、案件名、人名、呼び方の表記ゆれをコードに埋め込まず、人間が編集できる形で管理するため
  - TickTickリスト名への自動分類を、辞書と完全一致に基づく保守しやすい形にするため
- 影響範囲:
  - Phase 2仕様と設定ファイルのみ
  - Phase 2実装、TickTick連携実装は未実施

### 文脈ラベル用の別名辞書方針を追加

注記: `講師A` を `教室B` に寄せる例は、後続の「文脈ラベル辞書の表記ゆれとAI補足抑制を反映」で見直し済みです。
現在は、`講師A` 系は `講座A`、`講師B` 系は `教室B` として扱います。

- 対象ファイル:
  - `docs/phase2_topic_classification.md`
  - `docs/change-log.md`
- 内容:
  - 会社名、案件名、人名、呼び方の表記ゆれを扱う別名辞書方針を追加
  - `aliases` と `related_names` に基づいて `context_label` を補正する方針を追加
  - 担当者Aから株式会社A、講師Bや講師Aから教室Bへ寄せる例を追加
  - AI推測だけでは文脈を自動確定せず、辞書未登録や複数候補は `needs_review` にする方針を追加
  - `raw_context_label` と `context_match_status` をPhase 2出力項目に追加
- 理由:
  - `担当者Aに連絡` のような短い投稿から、後続タスクが元案件の文脈を失わないようにするため
  - TickTickリスト名への誤分類を避けるため
- 影響範囲:
  - Phase 2仕様のみ
  - 別名辞書ファイル作成と実装は未実施

### 文脈保持とTickTickリスト名照合ルールを追加

- 対象ファイル:
  - `docs/phase2_topic_classification.md`
  - `docs/development_roadmap.md`
  - `docs/change-log.md`
- 内容:
  - Phase 2出力に `context_label` を追加
  - `task_hint` が付くトピックでは、後続Phaseで文脈を失わないよう `context_label` または具体的な `topic_title` を持たせる方針を追加
  - Phase 5では `context_label`、`topic_title`、元投稿IDをタスク候補に引き継ぐ方針を追加
  - Phase 6ではTickTick側カテゴリと完全一致できるものだけ自動分類し、曖昧なものは要確認にする方針を追加
- 理由:
  - `残すサイトを決めてもらう` のような短いタスク候補が、株式会社Aや店舗Bなどの元文脈を失わないようにするため
  - TickTickリスト名への誤登録を避けるため
- 影響範囲:
  - Phase 2仕様と後続Phase方針のみ
  - TickTick連携実装は未実施

### 外出・旅行・娯楽フラグを追加

- 対象ファイル:
  - `docs/phase2_topic_classification.md`
  - `docs/change-log.md`
- 内容:
  - `outing_related`、`travel_related`、`leisure_related` flagを追加
  - 外出を伴う投稿は目的に応じてcategoryを選び、外出系flagを付ける方針を追加
- 理由:
  - 仕事での外出、娯楽、旅行、スーパー銭湯など、外出を伴う雑メモが増える可能性があるため
- 影響範囲:
  - Phase 2仕様のみ
  - 実装変更はなし

### 生活習慣カテゴリと食事・運動フラグを追加

- 対象ファイル:
  - `docs/phase2_topic_classification.md`
  - `docs/change-log.md`
- 内容:
  - `health_lifestyle` categoryを追加
  - `meal_related` と `exercise_related` flagを追加
  - 生活習慣、食事、運動、体調管理の投稿は通常 `health_lifestyle` として扱う方針を追加
- 理由:
  - 実運用では生活習慣、食事、運動に関する雑メモが増える見込みがあり、`personal` に埋もれないようにするため
- 影響範囲:
  - Phase 2仕様のみ
  - 実装変更はなし

### Phase 2の分類をcategoryとflagsに分離

- 対象ファイル:
  - `docs/phase2_topic_classification.md`
  - `docs/change-log.md`
- 内容:
  - `task_hint` をcategoryから外し、`flags` として扱う方針に変更
  - 費用、請求、収入などは `money_related` flag として扱う方針に変更
  - 読み込み確認などの一時的な投稿は専用categoryを作らず、通常は `uncategorized` として扱う方針に変更
  - `schedule_related`、`health_or_care`、`attachment_only`、`needs_review` の初期flagを追加
- 理由:
  - 実データでは、仕事、個人、参照などの主分類と、タスク化・費用・予定などの横断的な性質が重なるため
  - テスト投稿は通常運用では少ないため、専用categoryを増やさず分類軸を簡潔に保つため
- 影響範囲:
  - Phase 2仕様のみ
  - 実装変更はなし

### Phase 2仕様書を作成

- 対象ファイル:
  - `docs/phase2_topic_classification.md`
  - `docs/document-index.md`
  - `docs/development_roadmap.md`
  - `docs/change-log.md`
- 内容:
  - Phase 2の目的、入力、対象範囲、原文維持ルール、分類方針、出力JSON仕様、AI利用方針、例外時の扱い、完了条件を定義
  - Phase 2の入力をPhase 1 JSONに限定
  - Notion転記、TickTick連携、タスク候補抽出、添付内容解析はPhase 2対象外として整理
  - 文書インデックスにPhase 2仕様書を追加
  - ロードマップ上のPhase 2を仕様作成済みに更新
- 理由:
  - Phase 2実装前に、AIが担当する分類範囲と原文維持の境界を明確にするため
- 影響範囲:
  - 文書作成のみ
  - Phase 2実装、AIプロンプト作成、外部連携は未実施

## 2026-06-27

### Phase 1出力JSON仕様を追加

- 対象ファイル:
  - `docs/phase1_discord_ingest.md`
  - `docs/development_roadmap.md`
  - `docs/change-log.md`
- 内容:
  - Phase 1の出力JSONについて、トップレベル、投稿、添付の主要項目を仕様化
  - 後続Phaseでは `content` と `attachments[].local_path` を主な入力にする方針を追加
  - Discord CDNの `attachment_urls` は長期参照前提にしない方針を明記
  - ロードマップでPhase 2の入力をPhase 1 JSONと明記
- 理由:
  - Phase 1を後続Phaseへ渡せる成果物として確定しやすくするため
- 影響範囲:
  - 文書整理のみ
  - 実装変更はなし

### Phase 1確認状況チェック表を追加

- 対象ファイル:
  - `docs/phase1_discord_ingest.md`
  - `docs/change-log.md`
- 内容:
  - Phase 1で作る予定だった項目について、確認済み、未確認、対象外を一覧化
  - 実データで確認済みのDiscord投稿取得、添付保存、既存スキップ、秘密情報混入チェックを整理
- 理由:
  - Phase 1の残作業と完了候補の状態を一目で確認できるようにするため
- 影響範囲:
  - 文書整理のみ
  - 実装変更はなし

### 添付再実行時の既存スキップを追加

- 対象ファイル:
  - `discord-ingest/ingest_discord.py`
  - `docs/phase1_discord_ingest.md`
  - `docs/change-log.md`
- 内容:
  - 同じ日の再実行時、同じ保存名の添付ファイルが既にある場合は再ダウンロードしない方針を追加
  - 保存名を `message_id_attachment_id_元ファイル名` とし、既存ファイルは取得済みとして扱う
  - `Content-Length` やDiscord API上のサイズによる差分判定は行わない方針に変更
  - 添付の `download_status` に `already_exists` を追加
- 確認したこと:
  - `2026-06-27` を明示指定した同じ日の再実行で、既存の画像、動画、PDFが `already_exists` として記録された
  - 日付未指定では、Asia/Tokyoの日付が変わった後に `2026-06-28` が対象日になることを確認した
  - Office系添付は引き続き `skipped` として記録された
  - Markdown / JSONに `already_exists` とローカル保存先が反映された
  - Token、外部 `.env` パス、認証情報の混入チェックで該当なし
- 理由:
  - 日次運用や再実行時に、同じ添付ファイルを毎回ダウンロードしないようにするため
  - Discord CDNやAPIのサイズ情報に依存せず、Phase 1の挙動をシンプルに保つため
- 未確認事項:
  - 添付ファイル本体を意図的に壊した場合の自動修復はPhase 1では扱わない
- 影響範囲:
  - Phase 1の添付保存処理のみ

### 添付ファイル保存方針を追加

- 対象ファイル:
  - `discord-ingest/ingest_discord.py`
  - `docs/phase1_discord_ingest.md`
  - `docs/change-log.md`
  - `outputs/attachments/2026-06-27/`
  - `outputs/discord_messages_2026-06-27.md`
  - `outputs/discord_messages_2026-06-27.json`
- 内容:
  - Discord直添付のうち、画像、動画、PDFだけをローカル保存対象にした
  - Office、zip、exe、不明な形式は保存対象外としてスキップする方針を追加
  - JSONに `attachments` としてファイル名、content type、サイズ、保存状態、保存先を残すようにした
  - 添付保存先を `outputs/attachments/YYYY-MM-DD/` にした
- 確認したこと:
  - 画像1件を保存できた
  - 動画1件を保存できた
  - PDF2件を保存できた
  - docx1件とxlsx1件を `skipped` として記録できた
  - Markdownに添付ファイルの保存状態とローカル保存先を表示できた
  - Token、外部 `.env` パス、認証情報の混入チェックで該当なし
- 理由:
  - Discord CDNの添付URLに表示期限がある可能性があり、雑メモとして重要になりやすい画像、動画、PDFだけを手元に残すため
  - がっつり確認する資料やOfficeファイルはGoogle DriveコミュニティAとして扱う運用に合わせるため
- 未確認事項:
  - zip、exe、不明な形式のスキップ記録
  - 大きな動画ファイルの保存
- 影響範囲:
  - Phase 1の添付保存処理
  - 添付内容の解析、OCR、PDF読解、動画解析は未実装

### Phase 1の実データ取得を確認

- 対象ファイル:
  - `outputs/discord_messages_2026-06-27.md`
  - `outputs/discord_messages_2026-06-27.json`
  - `logs/discord_ingest_2026-06-27.log`
  - `docs/change-log.md`
- 内容:
  - Bot招待後にDiscord APIの読み取り専用dry-runを再実行
  - 認証、チャンネル取得、メッセージ取得に成功
  - `MEMO_WORKFLOW_TARGET_DATE` 空欄から、`Asia/Tokyo` 基準の `2026-06-27` を対象日に決定
  - 対象日の投稿1件をMarkdown / JSONに保存
- 確認したこと:
  - Discord Bot認証成功
  - 対象チャンネル取得成功
  - メッセージ取得成功
  - 日付抽出成功
  - Markdown / JSON保存成功
  - Token、外部 `.env` パス、認証情報の混入チェックで該当なし
- 未確認事項:
  - 添付ファイルURLを含む投稿の取得
  - 複数ページにまたがる大量投稿の取得
  - 過去日を明示指定した再取得
- 影響範囲:
  - Phase 1の実データ確認
  - AI分類、Notion転記、TickTick連携は未実装

### Phase 1の最小取得スクリプトを追加

- 対象ファイル:
  - `discord-ingest/ingest_discord.py`
  - `logs/.gitkeep`
  - `outputs/.gitkeep`
  - `docs/phase1_discord_ingest.md`
  - `docs/change-log.md`
- 内容:
  - Discord REST APIを読み取り専用で使う最小取得スクリプトを追加
  - 外部 `.env` を `--env-file` で読み込めるようにした
  - `MEMO_WORKFLOW_TARGET_DATE` 空欄時は指定タイムゾーン基準の今日を使う処理を実装
  - `--dry-run` ではDiscord読み取り確認だけを行い、Markdown / JSON出力は保存しない
  - `logs/` と `outputs/` の空ディレクトリ維持用ファイルを追加
- 確認したこと:
  - 構文チェック成功
  - `--help` 表示成功
  - 外部 `.env` 読み込みと対象日自動決定に成功
  - Discord Bot認証に成功
  - チャンネル取得で HTTP 403 を確認
- 未確認事項:
  - 対象チャンネルからのメッセージ取得
  - Markdown / JSONの実データ保存
- 影響範囲:
  - Phase 1のDiscord投稿取得のみ
  - AI分類、Notion転記、TickTick連携は未実装

### 対象日未指定時の扱いを追加

- 対象ファイル:
  - `docs/phase1_discord_ingest.md`
  - `docs/change-log.md`
- 内容:
  - `MEMO_WORKFLOW_TARGET_DATE` が空の場合は、指定タイムゾーン基準の今日を対象日にする方針を追加
  - ログには対象日の決定元だけを残し、環境変数の実値や秘密値を出さない方針を明記
- 理由:
  - 毎日使う運用で、対象日を毎回 `.env` に手入力しなくてもよいようにするため
- 影響範囲:
  - Phase 1の日付決定仕様
  - Discord取得、出力項目、後続Phaseの仕様変更はなし

## 2026-06-25

### 文書責務の基本ルールを上位方針に追加

- 対象ファイル:
  - `docs/app_policy.md`
  - `docs/change-log.md`
- 内容:
  - README、roadmap、Phase仕様書、change-log、AGENTS、app_policyの役割分担を `docs/app_policy.md` に追加
  - README.mdは入口案内に留め、変更されやすい情報は各文書に分ける方針を明文化
- 理由:
  - 小さい開発でも、今後の開発で文書の置き場所に迷わないようにするため
- 影響範囲:
  - 文書管理方針の明確化のみ
  - Phase 1仕様や実装内容の変更はなし

### README.mdを入口案内に整理

- 対象ファイル:
  - `README.md`
  - `docs/change-log.md`
- 内容:
  - README.mdから「現時点」「現在の対象範囲」など、Phase進行で古くなりやすい記述を削除
  - Phaseの状態や詳細仕様は `docs/development_roadmap.md` と対象Phase仕様書へ分ける方針を明確化
- 理由:
  - README.mdをプロジェクトの入口案内として保ち、Phase進行後も意味が残る文書にするため
- 影響範囲:
  - 文書構成の整理のみ
  - Phase 1仕様、環境変数、出力方針の内容変更はなし

### 初期文書構成を作成

- 対象ファイル:
  - `README.md`
  - `AGENTS.md`
  - `docs/document-index.md`
  - `docs/app_policy.md`
  - `docs/development_roadmap.md`
  - `docs/phase1_discord_ingest.md`
  - `.env.example`
  - `.gitignore`
- 内容:
  - Discordメモ取得プロジェクトの初期文書構成を作成
  - Phase 1をDiscord投稿取得の最小検証として定義
  - Phase 2以降はロードマップ上の予定として整理
- 理由:
  - 実装前に、文書の役割とPhase 1の境界を明確にするため
- 影響範囲:
  - 文書構成のみ
  - 実装、認証情報作成、外部サービス接続は未実施
- 未確認事項:
  - 実際のDiscord Bot権限
  - 実際のチャンネル取得可否
  - 実データでの日付抽出可否
