"""Publish a completed Discord ingest JSON to a synced Drive inbox.

The source output remains the local canonical copy.  A stable content digest
prevents unchanged daily output from being handed to ChatGPT more than once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


class PublishError(Exception):
    """A validation or file publication error."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy a completed Discord ingest JSON to a Drive-synced inbox."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--inbox", type=Path, required=True)
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path("state/drive_handoff_state.json"),
    )
    return parser.parse_args()


def load_payload(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise PublishError(f"source JSON was not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PublishError("source file is not valid JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
        raise PublishError("source JSON must contain messages[]")
    target_date = data.get("target_date")
    if not isinstance(target_date, str) or not target_date:
        raise PublishError("source JSON must contain target_date")
    return data


def content_digest(payload: dict[str, Any]) -> str:
    stable_payload = {
        "channel_id": payload.get("channel_id"),
        "target_date": payload.get("target_date"),
        "timezone": payload.get("timezone"),
        "messages": payload.get("messages", []),
    }
    encoded = json.dumps(
        stable_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schemaVersion": "memo-workflow.drive-handoff.v1", "deliveries": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PublishError("handoff state file is not valid JSON") from exc
    if not isinstance(state, dict) or not isinstance(state.get("deliveries"), dict):
        raise PublishError("handoff state file has an invalid structure")
    return state


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def publish(source: Path, inbox: Path, state_file: Path) -> Path | None:
    payload = load_payload(source)
    if not payload["messages"]:
        return None
    digest = content_digest(payload)
    state = load_state(state_file)
    target_date = payload["target_date"]
    delivery_key = f"{payload.get('channel_id', '')}:{target_date}"
    previous = state["deliveries"].get(delivery_key)
    if isinstance(previous, dict) and previous.get("contentHash") == digest:
        return None

    inbox.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    destination = inbox / (
        f"memodump_batch_{target_date.replace('-', '')}_{timestamp}_{digest[:10]}.json"
    )
    temporary = inbox / f".{destination.name}.{os.getpid()}.tmp"
    shutil.copyfile(source, temporary)
    os.replace(temporary, destination)

    state["deliveries"][delivery_key] = {
        "contentHash": digest,
        "publishedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "fileName": destination.name,
    }
    atomic_write_json(state_file, state)
    return destination


def main() -> int:
    args = parse_args()
    try:
        destination = publish(args.source, args.inbox, args.state_file)
    except (OSError, PublishError) as exc:
        print(f"ERROR stage=drive_handoff {exc}", file=sys.stderr)
        return 1
    if destination is None:
        print("drive_handoff=skipped reason=empty_or_unchanged")
    else:
        print(f"drive_handoff=published file={destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
