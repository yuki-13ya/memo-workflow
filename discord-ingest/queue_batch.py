"""Export and update Discord message queue batches.

This script works only on local queue/output files. It does not call Discord,
Notion, TickTick, or any AI API.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class QueueBatchError(Exception):
    """Error with a stage label for safe CLI reporting."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


def load_json(path: Path, stage: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise QueueBatchError(stage, f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise QueueBatchError(stage, f"file is not valid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise QueueBatchError(stage, f"JSON root must be an object: {path}")
    return data


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def text_value(value: Any) -> str:
    return "" if value is None else str(value)


def queue_messages(queue: dict[str, Any]) -> dict[str, Any]:
    messages = queue.get("messages")
    if not isinstance(messages, dict):
        raise QueueBatchError("queue_load", "queue messages must be an object")
    return messages


def is_pending_todo_candidate(entry: dict[str, Any]) -> bool:
    statuses = entry.get("statuses", {})
    if not isinstance(statuses, dict):
        return False
    return (
        statuses.get("fetched") is True
        and statuses.get("todoCandidateGenerated") is not True
        and statuses.get("ignored") is not True
        and statuses.get("held") is not True
    )


def pending_entries(queue: dict[str, Any], limit: int | None = None) -> list[dict[str, Any]]:
    entries = [
        entry
        for entry in queue_messages(queue).values()
        if isinstance(entry, dict) and is_pending_todo_candidate(entry)
    ]
    entries.sort(
        key=lambda item: (
            text_value(item.get("createdAtLocal") or item.get("createdAt")),
            text_value(item.get("messageId")),
        )
    )
    if limit is not None:
        return entries[:limit]
    return entries


def resolve_local_path(raw_path: str, base_dir: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return base_dir / path


def message_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    messages = payload.get("messages", [])
    if not isinstance(messages, list):
        raise QueueBatchError("source_load", "source JSON does not include messages[]")
    indexed: dict[str, dict[str, Any]] = {}
    for message in messages:
        if not isinstance(message, dict):
            continue
        message_id = text_value(message.get("message_id"))
        if message_id:
            indexed[message_id] = message
    return indexed


def load_pending_messages(
    queue_path: Path,
    entries: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], dict[str, str]]:
    base_dir = Path.cwd()
    source_cache: dict[Path, dict[str, dict[str, Any]]] = {}
    messages: list[dict[str, Any]] = []
    warnings: list[str] = []
    source_meta: dict[str, str] = {
        "channel_id": "",
        "channel_name": "queue_batch",
        "timezone": "",
    }

    for entry in entries:
        message_id = text_value(entry.get("messageId"))
        files = entry.get("files", {})
        if not isinstance(files, dict):
            warnings.append(f"message_id={message_id} missing files object")
            continue
        source_file = text_value(files.get("discordMessagesFile"))
        if not source_file:
            warnings.append(f"message_id={message_id} missing discordMessagesFile")
            continue

        source_path = resolve_local_path(source_file, base_dir)
        if source_path not in source_cache:
            source_payload = load_json(source_path, "source_load")
            source_cache[source_path] = message_index(source_payload)
            if not source_meta["channel_id"]:
                source_meta["channel_id"] = text_value(source_payload.get("channel_id"))
            if source_meta["channel_name"] == "queue_batch":
                source_meta["channel_name"] = text_value(
                    source_payload.get("channel_name")
                ) or "queue_batch"
            if not source_meta["timezone"]:
                source_meta["timezone"] = text_value(source_payload.get("timezone"))

        source_message = source_cache[source_path].get(message_id)
        if not source_message:
            warnings.append(f"message_id={message_id} not found in {source_path}")
            continue
        messages.append(source_message)

    return messages, warnings, source_meta


def markdown_for_payload(payload: dict[str, Any]) -> str:
    lines = [
        f"# Discord queue batch: {payload['target_date']}",
        "",
        f"- Timezone: {payload.get('timezone') or ''}",
        f"- Message count: {payload['message_count']}",
        f"- Source queue: {payload['queue_batch']['sourceQueuePath']}",
        "",
    ]
    warnings = payload["queue_batch"].get("warnings", [])
    if warnings:
        lines.extend(["Warnings:", ""])
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")

    for message in payload["messages"]:
        lines.extend(
            [
                f"## {message.get('created_at_local') or message.get('created_at')} / {message.get('author_name') or ''}",
                "",
                message.get("content") or "(no text)",
                "",
            ]
        )
        attachments = message.get("attachments", [])
        if attachments:
            lines.append("Attachments:")
            for attachment in attachments:
                filename = attachment.get("filename") or "(unknown filename)"
                status = attachment.get("download_status", "unknown")
                local_path = attachment.get("local_path")
                if local_path:
                    lines.append(f"- {filename} ({status}): {local_path}")
                else:
                    reason = attachment.get("skip_reason") or attachment.get("download_error") or ""
                    suffix = f", {reason}" if reason else ""
                    lines.append(f"- {filename} ({status}{suffix})")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_batch_payload(queue_path: Path, entries: list[dict[str, Any]]) -> dict[str, Any]:
    messages, warnings, source_meta = load_pending_messages(queue_path, entries)
    now = datetime.now(timezone.utc)
    batch_id = now.strftime("%Y%m%d_%H%M%S")
    return {
        "generated_at": now.isoformat(),
        "channel_id": source_meta["channel_id"],
        "channel_name": source_meta["channel_name"],
        "target_date": f"queue_batch_{batch_id}",
        "target_date_source": "queue_batch",
        "timezone": source_meta["timezone"],
        "message_count": len(messages),
        "messages": messages,
        "queue_batch": {
            "batchId": batch_id,
            "sourceQueuePath": str(queue_path),
            "messageIds": [
                text_value(message.get("message_id"))
                for message in messages
                if text_value(message.get("message_id"))
            ],
            "pendingQueueEntryCount": len(entries),
            "warningCount": len(warnings),
            "warnings": warnings,
        },
    }


def export_pending(args: argparse.Namespace) -> int:
    queue = load_json(args.queue_path, "queue_load")
    entries = pending_entries(queue, args.limit)
    payload = build_batch_payload(args.queue_path, entries)
    batch_id = payload["queue_batch"]["batchId"]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"discord_messages_queue_batch_{batch_id}.json"
    md_path = args.output_dir / f"discord_messages_queue_batch_{batch_id}.md"

    if not args.dry_run:
        save_json(json_path, payload)
        md_path.write_text(markdown_for_payload(payload), encoding="utf-8")

    print(
        json.dumps(
            {
                "pending_queue_entries": len(entries),
                "exported_messages": payload["message_count"],
                "warning_count": payload["queue_batch"]["warningCount"],
                "dry_run": args.dry_run,
                "json_output": str(json_path) if not args.dry_run else "",
                "markdown_output": str(md_path) if not args.dry_run else "",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def source_message_ids(source_data: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for message in source_data.get("messages", []):
        if isinstance(message, dict):
            message_id = text_value(message.get("message_id"))
            if message_id:
                ids.add(message_id)
    for item in source_data.get("items", []):
        if not isinstance(item, dict):
            continue
        for ref in item.get("sourceRefs", []):
            if not isinstance(ref, dict):
                continue
            if ref.get("type") == "discord_post":
                message_id = text_value(ref.get("id"))
                if message_id:
                    ids.add(message_id)
    queue_batch = source_data.get("queue_batch", {})
    if isinstance(queue_batch, dict):
        for message_id in queue_batch.get("messageIds", []):
            message_id_text = text_value(message_id)
            if message_id_text:
                ids.add(message_id_text)
    return ids


def mark_todo_generated(args: argparse.Namespace) -> int:
    queue = load_json(args.queue_path, "queue_load")
    source_data = load_json(args.source_file, "source_load")
    ids = source_message_ids(source_data)
    messages = queue_messages(queue)
    now_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    marked = 0
    missing: list[str] = []

    for message_id in sorted(ids):
        entry = messages.get(message_id)
        if not isinstance(entry, dict):
            missing.append(message_id)
            continue
        statuses = entry.setdefault("statuses", {})
        if not isinstance(statuses, dict):
            statuses = {}
            entry["statuses"] = statuses
        if statuses.get("todoCandidateGenerated") is not True:
            marked += 1
        statuses["todoCandidateGenerated"] = True
        files = entry.setdefault("files", {})
        if isinstance(files, dict):
            files["todoCandidatesFile"] = str(args.todo_candidates_file or args.source_file)
        entry["updatedAt"] = now_iso

    queue["updatedAt"] = now_iso
    if not args.dry_run:
        save_json(args.queue_path, queue)

    print(
        json.dumps(
            {
                "source_message_ids": len(ids),
                "marked": marked,
                "missing": missing,
                "dry_run": args.dry_run,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export/update Discord message queue batches.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser(
        "export-pending",
        help="Export fetched messages that have not been processed into TODO candidates.",
    )
    export_parser.add_argument(
        "--queue-path",
        type=Path,
        default=Path("state/discord_message_queue.json"),
    )
    export_parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    export_parser.add_argument("--limit", type=int)
    export_parser.add_argument("--dry-run", action="store_true")
    export_parser.set_defaults(func=export_pending)

    mark_parser = subparsers.add_parser(
        "mark-todo-generated",
        help="Mark queue messages as TODO-candidate-generated from a batch or Phase 5 output.",
    )
    mark_parser.add_argument(
        "--queue-path",
        type=Path,
        default=Path("state/discord_message_queue.json"),
    )
    mark_parser.add_argument("--source-file", type=Path, required=True)
    mark_parser.add_argument("--todo-candidates-file", type=Path)
    mark_parser.add_argument("--dry-run", action="store_true")
    mark_parser.set_defaults(func=mark_todo_generated)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return args.func(args)
    except QueueBatchError as exc:
        print(f"ERROR stage={exc.stage} {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
