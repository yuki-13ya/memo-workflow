# イシュー一覧

この文書は、`memo-workflow` の未解決事項、確認事項、判断待ちを集める場所です。

固定の仕様、Phase境界、全体設計、判断履歴とは役割を分けます。

## 記録方針

未解決事項や確認事項は、可能な限りこの文書に集約します。

Phase仕様書や `docs/system_design.md` には、確定した仕様、Phase境界、設計上の前提を記載します。
未確定の内容を仕様本文に混ぜる必要がある場合は、詳細をこの文書へ寄せ、仕様側には参照だけを置きます。

`docs/change-log.md` は、判断が変わった理由と影響範囲を残す履歴です。
未解決事項の管理表としては使いません。

## 書き方

各イシューは、以下を分けて書きます。

- 状態
- 関連Phase
- 確認したいこと
- 判断が必要な理由
- 判断後に更新する文書または実装

状態は、原則として以下から選びます。

- open
- checking
- decided
- deferred

`decided` になった内容は、必要に応じて該当するPhase仕様書、`docs/system_design.md`、`docs/development_roadmap.md`、`docs/change-log.md` に反映します。

## 未解決事項

| ID | 状態 | 関連Phase | 確認したいこと | 判断が必要な理由 | 判断後に更新する場所 |
|---|---|---|---|---|---|
| ISS-001 | open | Phase 4 | Notionの転記先構造 | Notion API転記の入力、変換、保存結果ログを確定するため | `docs/system_design.md`, Phase 4仕様書 |
| ISS-002 | open | Phase 6 | TickTickの既存カテゴリ取得方法 | 自動分類できる範囲と要確認に回す条件を確定するため | `docs/system_design.md`, Phase 6仕様書 |
| ISS-003 | open | Phase 2以降 | 要確認項目を人間が見る画面またはファイル形式 | AI分類、タスク候補、外部連携前の確認方法を決めるため | `docs/system_design.md`, 対象Phase仕様書 |
| ISS-004 | open | 全体 | 完成後の実行方法 | 日次実行、手動実行、ログ確認、失敗時復旧の運用を確定するため | `docs/system_design.md`, `docs/development_roadmap.md`, 運用仕様書 |
| ISS-005 | open | Phase 1 | zip / exe / 不明形式の添付スキップを実データで確認するか | 方針は定義済みだが、実データでのスキップ記録は未確認のため | `docs/phase1_discord_ingest.md`, `docs/change-log.md` |
| ISS-006 | open | Phase 1 | 大きな動画ファイルの保存を確認するか | 小さな動画では確認済みだが、大きな動画の保存挙動は未確認のため | `docs/phase1_discord_ingest.md`, `docs/change-log.md` |
| ISS-007 | open | Phase 1 | 100件超の複数ページ取得を確認するか | Discord APIのページングを実データで確認していないため | `docs/phase1_discord_ingest.md`, `docs/change-log.md` |
| ISS-008 | decided | Phase 5 | 行動が読み取れる候補は粒度が粗くても `todo_candidate` にできる。迷い、感情、文脈不明など人間判断なしで混乱しそうなものを `hold_candidate` にする | `ticktick-task` 側レビューで却下、編集、分解できる前提にし、Phase 5で過度に保守的な分類へ寄せすぎないため | `docs/phase5_ticktick_todo_candidates.md`, `docs/phase5_todo_candidate_json_spec.md`, `docs/phase5_ticktick_task_handoff.md`, `docs/change-log.md` |
| ISS-009 | open | Phase 5 | `reviewReason` と `non_todo` 理由の文言をどこまで人間向けに具体化するか | 現状でも機械判定の根拠は残るが、確認作業では理由がテンプレート的で判断の助けが弱い候補があるため | Phase 5実装, `docs/phase5_todo_candidate_json_spec.md` |
| ISS-010 | open | Phase 2以降 / 辞書運用 | TickTickから取得した既存リスト名を `config/context_aliases.csv` の `ticktick_list_name` へどう反映するか | `ticktick-task` のレビューUIは `handoff/ticktick_list_names.json` を登録先候補として読むが、その元になる辞書へTickTick既存リスト名を取り込む運用が未定義のため。実リスト名を全自動で辞書へ入れると、文脈ラベルと関係ないリストまで候補化する危険がある | `docs/context_alias_registration_interface_note.md`, `docs/change-log.md`, 親 `handoff/README.md` |
