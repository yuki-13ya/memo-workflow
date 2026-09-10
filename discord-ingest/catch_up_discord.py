"""Fetch Discord messages since the last queued message and create one new-message batch."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import ingest_discord as ingest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Catch up Discord messages since the last fetch.")
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--log-dir", type=Path, default=Path("logs"))
    parser.add_argument("--queue-path", type=Path, default=Path("state/discord_message_queue.json"))
    parser.add_argument("--initial-from", type=date.fromisoformat)
    parser.add_argument("--overlap-days", type=int, default=1)
    parser.add_argument("--max-pages", type=int, default=ingest.DEFAULT_MAX_PAGES)
    return parser.parse_args()


def range_start(queue: dict, local_tz: ZoneInfo, today: date, initial_from: date | None, overlap_days: int) -> date:
    created_values = []
    for item in queue.get("messages", {}).values():
        if isinstance(item, dict) and item.get("createdAt"):
            created_values.append(ingest.parse_discord_datetime(str(item["createdAt"])))
    if created_values:
        latest_local_date = max(created_values).astimezone(local_tz).date()
        return latest_local_date - timedelta(days=max(overlap_days, 0))
    return initial_from or today


def payload_for_date(config, channel, records, target_date: date) -> dict:
    payload = ingest.build_payload(config, channel, records)
    payload["target_date"] = target_date.isoformat()
    payload["target_date_source"] = "since_last_fetch"
    return payload


def main() -> int:
    args = parse_args()
    try:
        ingest.load_env_file(args.env_file)
        config = ingest.load_config()
        local_tz = ZoneInfo(config.timezone_name)
        today = datetime.now(local_tz).date()
        queue = ingest.load_queue(args.queue_path)
        known_ids = set(queue.get("messages", {}).keys())
        start_date = range_start(queue, local_tz, today, args.initial_from, args.overlap_days)
        logger = ingest.setup_logger(args.log_dir, today)

        ingest.log_info(logger, "date_extract", f"mode=since_last_fetch from={start_date} to={today}")
        ingest.check_auth(config.bot_token)
        channel = ingest.fetch_channel(config.bot_token, config.channel_id)
        records = ingest.fetch_messages_for_range(
            config, local_tz, start_date, today, args.max_pages, logger
        )

        by_date: dict[str, list[dict]] = {}
        for record in records:
            local_date = ingest.local_date_for_message(record)
            by_date.setdefault(local_date, []).append(record)

        for local_date, date_records in sorted(by_date.items()):
            target_date = date.fromisoformat(local_date)
            ingest.download_supported_attachments(date_records, args.output_dir, local_date, logger)
            payload = payload_for_date(config, channel, date_records, target_date)
            json_path = args.output_dir / f"discord_messages_{local_date}.json"
            existing = ingest.load_json_if_exists(json_path)
            payload, _ = ingest.merge_payload_by_message_id(existing, payload)
            _, json_path = ingest.save_outputs(args.output_dir, payload)
            ingest.update_queue(args.queue_path, payload, json_path)

        new_records = [item for item in records if str(item.get("message_id", "")) not in known_ids]
        batch_path = None
        if new_records:
            timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
            batch_payload = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "channel_id": config.channel_id,
                "channel_name": channel.get("name", ""),
                "target_date": today.isoformat(),
                "target_date_source": "since_last_fetch_batch",
                "range_start": start_date.isoformat(),
                "range_end": today.isoformat(),
                "timezone": config.timezone_name,
                "message_count": len(new_records),
                "messages": new_records,
            }
            batch_path = args.output_dir / f"discord_messages_catchup_batch_{timestamp}.json"
            batch_path.write_text(json.dumps(batch_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print(json.dumps({
            "range_start": start_date.isoformat(),
            "range_end": today.isoformat(),
            "fetched_count": len(records),
            "new_message_count": len(new_records),
            "batch_path": str(batch_path) if batch_path else None,
        }, ensure_ascii=False))
        return 0
    except (OSError, ValueError, ingest.IngestError) as exc:
        logger = logging.getLogger("discord_ingest")
        if logger.handlers:
            ingest.log_error(logger, getattr(exc, "stage", "catch_up"), str(exc))
        else:
            print(f"ERROR stage=catch_up {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
