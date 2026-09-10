"""Read Discord messages for one local date and save Markdown/JSON outputs.

Phase 1 is read-only. This script uses Discord REST read endpoints only and
never logs Bot Token or other secret values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_EPOCH_MS = 1420070400000
DEFAULT_MAX_PAGES = 50
SUPPORTED_ATTACHMENT_TYPES = ("image/", "video/")
SUPPORTED_ATTACHMENT_EXACT_TYPES = {"application/pdf"}


class IngestError(Exception):
    """Error with a phase-specific stage label for safe logging."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


@dataclass(frozen=True)
class Config:
    bot_token: str
    channel_id: str
    timezone_name: str
    target_date: date
    target_date_source: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read Discord messages for one local date and save Markdown/JSON."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Optional .env file to load before reading environment variables.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory for Markdown and JSON output files.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("logs"),
        help="Directory for log files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read Discord and print a summary without saving Markdown/JSON files.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="Maximum Discord message pages to read while paging backward.",
    )
    parser.add_argument(
        "--merge-existing",
        action="store_true",
        help="Merge fetched messages into an existing date output by message_id.",
    )
    parser.add_argument(
        "--update-queue",
        action="store_true",
        help="Update state/discord_message_queue.json with fetched messages.",
    )
    parser.add_argument(
        "--queue-path",
        type=Path,
        default=Path("state/discord_message_queue.json"),
        help="Path to the Discord message queue state file.",
    )
    return parser.parse_args()


def load_env_file(path: Path) -> None:
    if not path.exists():
        raise IngestError("env_load", "env file was not found")
    if not path.is_file():
        raise IngestError("env_load", "env file path is not a file")

    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_config() -> Config:
    required = ["DISCORD_BOT_TOKEN", "DISCORD_CHANNEL_ID", "MEMO_WORKFLOW_TIMEZONE"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise IngestError("env_load", f"missing environment variables: {', '.join(missing)}")

    timezone_name = os.environ["MEMO_WORKFLOW_TIMEZONE"].strip()
    try:
        local_tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise IngestError("date_extract", "timezone is not available") from exc

    raw_target_date = os.environ.get("MEMO_WORKFLOW_TARGET_DATE", "").strip()
    if raw_target_date:
        try:
            target_date = date.fromisoformat(raw_target_date)
        except ValueError as exc:
            raise IngestError("date_extract", "target date must use YYYY-MM-DD") from exc
        target_date_source = "env"
    else:
        target_date = datetime.now(local_tz).date()
        target_date_source = "default_today"

    return Config(
        bot_token=os.environ["DISCORD_BOT_TOKEN"],
        channel_id=os.environ["DISCORD_CHANNEL_ID"].strip(),
        timezone_name=timezone_name,
        target_date=target_date,
        target_date_source=target_date_source,
    )


def setup_logger(log_dir: Path, target_date: date) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("discord_ingest")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s stage=%(stage)s %(message)s")
    log_path = log_dir / f"discord_ingest_{target_date.isoformat()}.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


def log_info(logger: logging.Logger, stage: str, message: str) -> None:
    logger.info(message, extra={"stage": stage})


def log_error(logger: logging.Logger, stage: str, message: str) -> None:
    logger.error(message, extra={"stage": stage})


def discord_request(token: str, path: str, params: dict[str, str] | None = None) -> Any:
    url = f"{DISCORD_API_BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "memo-workflow-discord-ingest/0.1",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise IngestError("discord_api", f"discord api returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise IngestError("discord_api", "discord api connection failed") from exc
    except json.JSONDecodeError as exc:
        raise IngestError("discord_api", "discord api returned invalid JSON") from exc


def snowflake_for_datetime(value: datetime) -> str:
    utc_value = value.astimezone(timezone.utc)
    timestamp_ms = int(utc_value.timestamp() * 1000)
    return str((timestamp_ms - DISCORD_EPOCH_MS) << 22)


def parse_discord_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def is_supported_attachment(content_type: str) -> bool:
    normalized = content_type.lower()
    return normalized.startswith(SUPPORTED_ATTACHMENT_TYPES) or normalized in SUPPORTED_ATTACHMENT_EXACT_TYPES


def attachment_metadata(attachment: dict[str, Any]) -> dict[str, Any]:
    content_type = attachment.get("content_type") or ""
    supported = is_supported_attachment(content_type)
    metadata = {
        "attachment_id": attachment.get("id", ""),
        "filename": attachment.get("filename", ""),
        "content_type": content_type,
        "size": attachment.get("size", 0),
        "download_status": "pending" if supported else "skipped",
    }
    if supported:
        metadata["url"] = attachment.get("url", "")
        metadata["local_path"] = None
    else:
        metadata["skip_reason"] = "unsupported_content_type"
    return metadata


def message_to_record(message: dict[str, Any], local_tz: ZoneInfo) -> dict[str, Any]:
    created_at = parse_discord_datetime(message["timestamp"])
    created_at_local = created_at.astimezone(local_tz)
    author = message.get("author", {})
    attachments = [attachment_metadata(item) for item in message.get("attachments", [])]
    return {
        "message_id": message.get("id", ""),
        "created_at": created_at.isoformat(),
        "created_at_local": created_at_local.isoformat(),
        "author_name": author.get("global_name") or author.get("username") or "",
        "content": message.get("content", ""),
        "attachment_urls": [
            item["url"]
            for item in attachments
            if item.get("download_status") == "pending" and item.get("url")
        ],
        "attachments": attachments,
    }


def fetch_channel(token: str, channel_id: str) -> dict[str, Any]:
    try:
        return discord_request(token, f"/channels/{channel_id}")
    except IngestError as exc:
        raise IngestError("channel_get", str(exc)) from exc


def check_auth(token: str) -> None:
    try:
        discord_request(token, "/users/@me")
    except IngestError as exc:
        raise IngestError("auth", str(exc)) from exc


def fetch_messages_for_date(
    config: Config, local_tz: ZoneInfo, max_pages: int, logger: logging.Logger
) -> list[dict[str, Any]]:
    return fetch_messages_for_range(
        config, local_tz, config.target_date, config.target_date, max_pages, logger
    )


def fetch_messages_for_range(
    config: Config,
    local_tz: ZoneInfo,
    start_date: date,
    end_date: date,
    max_pages: int,
    logger: logging.Logger,
) -> list[dict[str, Any]]:
    if start_date > end_date:
        raise IngestError("date_extract", "start date must not be after end date")
    start_local = datetime.combine(start_date, time.min, tzinfo=local_tz)
    end_exclusive_local = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=local_tz)
    start_utc = start_local.astimezone(timezone.utc)
    end_utc = end_exclusive_local.astimezone(timezone.utc)

    before = snowflake_for_datetime(end_utc)
    records: list[dict[str, Any]] = []

    for page_index in range(max_pages):
        params = {"limit": "100", "before": before}
        try:
            messages = discord_request(
                config.bot_token, f"/channels/{config.channel_id}/messages", params
            )
        except IngestError as exc:
            raise IngestError("message_get", str(exc)) from exc

        if not messages:
            log_info(logger, "message_get", f"page={page_index + 1} count=0")
            break

        page_datetimes = [parse_discord_datetime(item["timestamp"]) for item in messages]
        for message, created_at in zip(messages, page_datetimes):
            if start_utc <= created_at < end_utc:
                records.append(message_to_record(message, local_tz))

        oldest_message = min(messages, key=lambda item: int(item["id"]))
        oldest_dt = min(page_datetimes)
        before = oldest_message["id"]
        log_info(
            logger,
            "message_get",
            f"page={page_index + 1} count={len(messages)} matched_total={len(records)}",
        )

        if oldest_dt < start_utc:
            break

    records.sort(key=lambda item: item["created_at"])
    return records


def build_payload(
    config: Config, channel: dict[str, Any], records: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel_id": config.channel_id,
        "channel_name": channel.get("name", ""),
        "target_date": config.target_date.isoformat(),
        "target_date_source": config.target_date_source,
        "timezone": config.timezone_name,
        "message_count": len(records),
        "messages": records,
    }


def safe_filename(value: str) -> str:
    name = Path(value).name.strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name or "attachment"


def download_attachment(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "memo-workflow-discord-ingest/0.1"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        destination.write_bytes(response.read())


def download_supported_attachments(
    records: list[dict[str, Any]], output_dir: Path, target_date: str, logger: logging.Logger
) -> None:
    attachment_dir = output_dir / "attachments" / target_date
    for message in records:
        for attachment in message.get("attachments", []):
            if attachment.get("download_status") != "pending":
                continue

            filename = safe_filename(attachment.get("filename", "attachment"))
            attachment_id = attachment.get("attachment_id") or "attachment"
            local_path = attachment_dir / f"{message['message_id']}_{attachment_id}_{filename}"
            if local_path.exists():
                attachment["download_status"] = "already_exists"
                attachment["local_path"] = str(local_path)
                log_info(
                    logger,
                    "attachment_download",
                    f"message_id={message['message_id']} attachment_id={attachment_id} already exists",
                )
                continue

            try:
                attachment_dir.mkdir(parents=True, exist_ok=True)
                download_attachment(attachment["url"], local_path)
            except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
                attachment["download_status"] = "failed"
                attachment["download_error"] = exc.__class__.__name__
                log_error(
                    logger,
                    "attachment_download",
                    f"message_id={message['message_id']} attachment_id={attachment_id} download failed",
                )
                continue

            attachment["download_status"] = "downloaded"
            attachment["local_path"] = str(local_path)
            log_info(
                logger,
                "attachment_download",
                f"message_id={message['message_id']} attachment_id={attachment_id} downloaded",
            )


def markdown_for_payload(payload: dict[str, Any]) -> str:
    lines = [
        f"# Discord messages: {payload['target_date']}",
        "",
        f"- Timezone: {payload['timezone']}",
        f"- Target date source: {payload['target_date_source']}",
        f"- Channel: {payload.get('channel_name') or '(unknown)'}",
        f"- Message count: {payload['message_count']}",
        "",
    ]

    for message in payload["messages"]:
        lines.extend(
            [
                f"## {message['created_at_local']} / {message['author_name']}",
                "",
                message["content"] or "(no text)",
                "",
            ]
        )
        if message.get("attachments"):
            lines.append("Attachments:")
            for attachment in message["attachments"]:
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


def save_outputs(output_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    target_date = payload["target_date"]
    json_path = output_dir / f"discord_messages_{target_date}.json"
    markdown_path = output_dir / f"discord_messages_{target_date}.md"

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(markdown_for_payload(payload), encoding="utf-8")
    return markdown_path, json_path


def text_value(value: Any) -> str:
    return "" if value is None else str(value)


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise IngestError("output_save", f"existing JSON is invalid: {path}") from exc
    if not isinstance(data, dict):
        raise IngestError("output_save", f"existing JSON root must be an object: {path}")
    return data


def merge_payload_by_message_id(
    existing: dict[str, Any] | None, incoming: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, int]]:
    incoming_messages = [
        item for item in incoming.get("messages", []) if isinstance(item, dict)
    ]
    if not existing:
        merge_summary = {
            "existing_message_count": 0,
            "incoming_message_count": len(incoming_messages),
            "new_message_count": len(incoming_messages),
            "merged_message_count": len(incoming_messages),
            "changed_existing_count": 0,
        }
        merged = dict(incoming)
        merged["merge_summary"] = merge_summary
        return merged, merge_summary

    existing_messages = [
        item for item in existing.get("messages", []) if isinstance(item, dict)
    ]
    merged_by_id: dict[str, dict[str, Any]] = {}
    changed_existing_count = 0

    for message in existing_messages:
        message_id = text_value(message.get("message_id"))
        if message_id:
            merged_by_id[message_id] = message

    for message in incoming_messages:
        message_id = text_value(message.get("message_id"))
        if not message_id:
            continue
        if message_id in merged_by_id:
            existing_message = merged_by_id[message_id]
            if (
                text_value(existing_message.get("content")) != text_value(message.get("content"))
                or existing_message.get("attachments", []) != message.get("attachments", [])
            ):
                changed_existing_count += 1
            continue
        merged_by_id[message_id] = message

    merged_messages = sorted(
        merged_by_id.values(),
        key=lambda item: text_value(item.get("created_at")),
    )
    merged = dict(incoming)
    merged["messages"] = merged_messages
    merged["message_count"] = len(merged_messages)
    merge_summary = {
        "existing_message_count": len(existing_messages),
        "incoming_message_count": len(incoming_messages),
        "new_message_count": max(len(merged_messages) - len(existing_messages), 0),
        "merged_message_count": len(merged_messages),
        "changed_existing_count": changed_existing_count,
    }
    merged["merge_summary"] = merge_summary
    return merged, merge_summary


def content_hash(message: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    digest.update(text_value(message.get("content")).encode("utf-8"))
    return digest.hexdigest()


def local_date_for_message(message: dict[str, Any]) -> str:
    created_at_local = text_value(message.get("created_at_local"))
    return created_at_local[:10] if len(created_at_local) >= 10 else ""


def empty_queue() -> dict[str, Any]:
    return {
        "schemaVersion": "1.0",
        "updatedAt": "",
        "messages": {},
    }


def load_queue(path: Path) -> dict[str, Any]:
    data = load_json_if_exists(path)
    if data is None:
        return empty_queue()
    if not isinstance(data.get("messages"), dict):
        raise IngestError("queue_update", "queue messages must be an object")
    return data


def queue_entry_for_message(
    message: dict[str, Any],
    discord_messages_file: Path,
    now_iso: str,
) -> dict[str, Any]:
    return {
        "messageId": text_value(message.get("message_id")),
        "createdAt": text_value(message.get("created_at")),
        "createdAtLocal": text_value(message.get("created_at_local")),
        "localDate": local_date_for_message(message),
        "authorName": text_value(message.get("author_name")),
        "contentHash": content_hash(message),
        "attachmentCount": len(message.get("attachments", []) or []),
        "statuses": {
            "fetched": True,
            "todoCandidateGenerated": False,
            "reviewed": False,
            "confirmed": False,
            "executed": False,
            "ignored": False,
            "held": False,
        },
        "files": {
            "discordMessagesFile": str(discord_messages_file),
            "todoCandidatesFile": "",
            "reviewedFile": "",
            "executedFile": "",
        },
        "lastError": "",
        "updatedAt": now_iso,
    }


def merge_queue_entry(existing: dict[str, Any] | None, incoming: dict[str, Any]) -> dict[str, Any]:
    if not existing:
        return incoming

    merged = dict(existing)
    merged.update(
        {
            "createdAt": incoming["createdAt"],
            "createdAtLocal": incoming["createdAtLocal"],
            "localDate": incoming["localDate"],
            "authorName": incoming["authorName"],
            "attachmentCount": incoming["attachmentCount"],
            "updatedAt": incoming["updatedAt"],
        }
    )
    if merged.get("contentHash") and merged.get("contentHash") != incoming["contentHash"]:
        merged["lastError"] = "content_hash_changed_after_initial_fetch"
    else:
        merged["contentHash"] = incoming["contentHash"]

    statuses = dict(incoming["statuses"])
    statuses.update(existing.get("statuses", {}))
    statuses["fetched"] = True
    merged["statuses"] = statuses

    files = dict(incoming["files"])
    files.update(existing.get("files", {}))
    files["discordMessagesFile"] = incoming["files"]["discordMessagesFile"]
    merged["files"] = files
    return merged


def update_queue(
    queue_path: Path,
    payload: dict[str, Any],
    discord_messages_file: Path,
) -> dict[str, int]:
    queue = load_queue(queue_path)
    messages = queue["messages"]
    now_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    added = 0
    updated = 0

    for message in payload.get("messages", []):
        if not isinstance(message, dict):
            continue
        message_id = text_value(message.get("message_id"))
        if not message_id:
            continue
        incoming = queue_entry_for_message(message, discord_messages_file, now_iso)
        existing = messages.get(message_id)
        if existing:
            updated += 1
        else:
            added += 1
        messages[message_id] = merge_queue_entry(existing, incoming)

    queue["updatedAt"] = now_iso
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"queue_added": added, "queue_updated": updated, "queue_total": len(messages)}


def main() -> int:
    args = parse_args()
    try:
        if args.env_file:
            load_env_file(args.env_file)
        config = load_config()
        logger = setup_logger(args.log_dir, config.target_date)
        local_tz = ZoneInfo(config.timezone_name)

        log_info(
            logger,
            "date_extract",
            f"target_date_source={config.target_date_source} target_date={config.target_date.isoformat()}",
        )
        log_info(logger, "auth", "checking Discord bot authentication")
        check_auth(config.bot_token)
        log_info(logger, "auth", "authentication succeeded")

        log_info(logger, "channel_get", "checking target channel access")
        channel = fetch_channel(config.bot_token, config.channel_id)
        log_info(logger, "channel_get", "channel access succeeded")

        records = fetch_messages_for_date(config, local_tz, args.max_pages, logger)

        if args.dry_run:
            log_info(logger, "output_save", "dry run enabled; outputs were not saved")
        else:
            download_supported_attachments(
                records, args.output_dir, config.target_date.isoformat(), logger
            )
        payload = build_payload(config, channel, records)
        merge_summary = {
            "existing_message_count": 0,
            "incoming_message_count": len(payload.get("messages", [])),
            "new_message_count": len(payload.get("messages", [])),
            "merged_message_count": len(payload.get("messages", [])),
            "changed_existing_count": 0,
        }
        queue_summary: dict[str, int] | None = None

        if not args.dry_run:
            target_date = payload["target_date"]
            json_path = args.output_dir / f"discord_messages_{target_date}.json"
            if args.merge_existing:
                existing_payload = load_json_if_exists(json_path)
                payload, merge_summary = merge_payload_by_message_id(
                    existing_payload, payload
                )
                log_info(
                    logger,
                    "output_save",
                    (
                        "merge_existing "
                        f"existing={merge_summary['existing_message_count']} "
                        f"incoming={merge_summary['incoming_message_count']} "
                        f"new={merge_summary['new_message_count']} "
                        f"changed_existing={merge_summary['changed_existing_count']}"
                    ),
                )
            markdown_path, json_path = save_outputs(args.output_dir, payload)
            log_info(
                logger,
                "output_save",
                f"saved markdown={markdown_path} json={json_path}",
            )
            if args.update_queue:
                queue_summary = update_queue(args.queue_path, payload, json_path)
                log_info(
                    logger,
                    "queue_update",
                    (
                        f"updated queue={args.queue_path} "
                        f"added={queue_summary['queue_added']} "
                        f"updated={queue_summary['queue_updated']} "
                        f"total={queue_summary['queue_total']}"
                    ),
                )

        print(
            json.dumps(
                {
                    "target_date": config.target_date.isoformat(),
                    "target_date_source": config.target_date_source,
                    "message_count": len(records),
                    "dry_run": args.dry_run,
                    "merge_existing": args.merge_existing and not args.dry_run,
                    "merge_summary": merge_summary,
                    "update_queue": args.update_queue and not args.dry_run,
                    "queue_summary": queue_summary,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except IngestError as exc:
        logger = logging.getLogger("discord_ingest")
        if logger.handlers:
            log_error(logger, exc.stage, str(exc))
        else:
            print(f"ERROR stage={exc.stage} {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
