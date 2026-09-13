# Discordメモ取得ワークフロー

Discordに雑に投げ込んだメモを取得し、原文を維持したまま整理して、Notion向けの記録データと `ticktick-task` 向けのTODO候補データへ分岐させるための小規模自動化プロジェクトです。

## 基本方針

このプロジェクトでは、実装をPhase単位で区切り、確認できたこと、未確認のこと、未実装のことを分けて管理します。

Phase 1では、Discord投稿を読み取り専用で取得し、Markdown / JSONとして保存します。

Phase 2では、Phase 1のJSONを入力にし、原文を維持したままトピック分類します。

Phase 2の分類結果は、後続で2つのルートに分岐します。

- Notionルート
- TODO候補ルート

Notionルートでは、雑文、記録、考えたこと、日報的な内容、添付メモなどを、Notionで見返しやすい形に整えます。

TODO候補ルートでは、Discord雑文からタスク候補になりそうな内容だけを抽出し、`ticktick-task` 側が受け取れるTODO候補JSONとして出力します。

`memo-workflow` 側では、TickTick APIへの登録、更新、削除を行いません。
TickTickへの登録、既存TickTickタスクとの統合判定、人間確認CSV、OK済み候補の反映、作業ブロック化、作業ブロック用タスク出力は `ticktick-task` 側の責務として扱います。

認証情報やトークンはプロジェクトフォルダ内に保存しません。必要な環境変数名だけを `.env.example` に記載します。

## 主要文書

| ファイル | 役割 |
|---|---|
| `AGENTS.md` | Codexがこのプロジェクト内で作業するときのルール |
| `docs/document-index.md` | 文書の役割、配置、参照ルール |
| `docs/app_policy.md` | 設計、AI利用、外部連携、認証情報管理の上位方針 |
| `docs/system_design.md` | プロジェクト全体の設計図 |
| `docs/development_roadmap.md` | Phase構成と各Phaseの境界 |
| `docs/issues.md` | 未解決事項、確認事項、判断待ち |
| `docs/phase1_discord_ingest.md` | Phase 1: Discord投稿取得の詳細仕様 |
| `docs/discord_unprocessed_queue_spec.md` | Discord投稿を未処理キューで管理する追加仕様 |
| `docs/phase2_topic_classification.md` | Phase 2: 原文維持のトピック分類仕様 |
| `docs/phase5_ticktick_todo_candidates.md` | Phase 5: `ticktick-task` 向けTODO候補JSON生成の設計仕様 |
| `docs/phase5_todo_candidate_json_spec.md` | Phase 5: TODO候補JSONの出力仕様 |
| `docs/phase5_ticktick_task_handoff.md` | Phase 5出力を `ticktick-task` 側へ渡すときの申し送り |
| `context-alias-editor/` | `config/context_aliases.csv` を編集するローカルUI |
| `docs/change-log.md` | 仕様変更や判断変更の記録 |
| `.env.example` | 必要な環境変数名の一覧 |

## フォルダ構成

```text
memo-workflow/
├─ README.md
├─ AGENTS.md
├─ .env.example
├─ .gitignore
├─ docs/
│  ├─ document-index.md
│  ├─ app_policy.md
│  ├─ system_design.md
│  ├─ development_roadmap.md
│  ├─ issues.md
│  ├─ change-log.md
│  ├─ phase1_discord_ingest.md
│  └─ phase2_topic_classification.md
├─ discord-ingest/
├─ phase5-todo-candidates/
├─ outputs/
└─ logs/
```

## 実行手順の入口

Phase構成、Phaseごとの対象範囲、各Phaseの完了条件は `docs/development_roadmap.md` を参照します。

Phase固有の仕様、環境変数、出力形式、ログ方針、例外時の扱いは、対象Phaseの仕様書を参照します。

Phase 5のTODO候補JSON生成は `python phase5-todo-candidates/export_todo_candidates.py --date YYYY-MM-DD --use-ai` から実行します。
`--use-ai` は自由文からTODO候補を抽出、分解する主経路です。
`--use-ai` を付けない場合はローカル抽出の退避経路として動きますが、抽出品質確認の正規経路としては扱いません。

Discord未処理キューから後続Phase向けのバッチJSONを作る場合は `python discord-ingest/queue_batch.py export-pending` を使います。
詳細は `docs/discord_unprocessed_queue_spec.md` を参照します。

未処理キューの最終取得位置からDiscord投稿を遡及取得し、新しく見つかった投稿だけを
Google Drive同期フォルダへ受け渡す場合は `run_memodump_sync.ps1` を使います。
境界の1日分を重ねて再取得し、`message_id` で重複を除外します。ローカルの日付別
`outputs/` を正本として維持し、新規投稿バッチだけをGoogle Drive上の
`Memo-Router/inbox/` へコピーします。
Drive上のJSONを扱う人間またはブラウザ版ChatGPT向けの説明は
`docs/drive_chatgpt_handoff.md` を参照します。同文書はDrive側では `README.md` として配置します。

```powershell
.\run_memodump_sync.ps1 -EnvFile path\to\.env -PythonExecutable path\to\python.exe
```

タスクスケジューラでは、認証情報を引数へ直接書かず、外部 `.env` のパスと
Python実行ファイルをこのスクリプトへ渡します。

現在のPCへログオン時と毎日20時のトリガーを登録する場合は、
`register_memodump_tasks.ps1` を実行します。Drive for desktopを利用できるよう、
タスクはログオン中のユーザーとして動作します。

```powershell
.\register_memodump_tasks.ps1 `
  -EnvFile path\to\.env `
  -PythonExecutable path\to\python.exe `
  -DriveInbox path\to\Memo-Router\inbox
```

登録済みタスクを任意のタイミングで実行する場合は、`run_memodump_sync_ui.cmd` を
ダブルクリックします。「今すぐ同期」から定期実行と同じタスクを起動でき、完了後に
新しいJSON名または「新しい投稿なし」を表示します。認証情報や実行パスはUI側に
複製せず、登録済みタスクの設定を使用します。タスクが未登録の場合は「初期設定」から
`.env`、Python、`Memo-Router/inbox` を選択すると、ログオン時・毎日20時・今すぐ同期で
共通利用するタスクを登録できます。

デスクトップショートカットと `.cmd` は `run_memodump_sync_ui.vbs` を経由してUIだけを
表示します。通常のエラーはUI内へ表示し、UIが開く前に発生した起動エラーだけを
`logs/memodump_sync_ui_launch.log` へ記録します。

文脈ラベル辞書の編集UIは `run_context_alias_editor.cmd` から起動します。
起動後、ブラウザで `http://127.0.0.1:8788/` を開きます。

プロジェクト全体の流れ、NotionルートとTODO候補ルートの分岐、`memo-workflow` と `ticktick-task` の責務分担は `docs/system_design.md` を参照します。

Codexで作業する場合のルールは `AGENTS.md` を参照します。

未解決事項、確認事項、判断待ちは `docs/issues.md` を参照します。

仕様変更や判断変更の経緯は `docs/change-log.md` を参照します。
