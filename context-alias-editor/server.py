#!/usr/bin/env python3
"""Local editor for config/context_aliases.csv.

This server is local-file only. It does not call external APIs.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_DICTIONARY = ROOT_DIR / "config" / "context_aliases.csv"
BACKUP_DIR = ROOT_DIR / "outputs" / "context_alias_backups"

FIELDS = [
    "canonical_name",
    "aliases",
    "related_names",
    "ticktick_list_name",
    "category_hint",
    "flags_hint",
    "active",
    "notes",
]

ALLOWED_CATEGORY_HINTS = {"", "work", "health_lifestyle", "personal", "reference", "uncategorized"}
ALLOWED_FLAGS = {
    "",
    "task_hint",
    "money_related",
    "schedule_related",
    "health_or_care",
    "meal_related",
    "exercise_related",
    "outing_related",
    "travel_related",
    "leisure_related",
    "attachment_only",
    "needs_review",
}

FLAG_LABELS_JA = {
    "task_hint": "タスク候補",
    "money_related": "お金・請求・見積",
    "schedule_related": "予定・頻度・時間",
    "health_or_care": "体調・ケア",
    "meal_related": "食事",
    "exercise_related": "運動",
    "outing_related": "外出",
    "travel_related": "旅行・遠出",
    "leisure_related": "娯楽・リフレッシュ",
    "attachment_only": "添付中心",
    "needs_review": "要確認",
}


def split_semicolon(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def join_semicolon(items: list[str]) -> str:
    return ";".join(item.strip() for item in items if item.strip())


def normalize_bool(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value or "").strip().lower()
    return "true" if text in {"true", "1", "yes", "y", "on"} else "false"


def normalize_row(payload: dict[str, Any]) -> dict[str, str]:
    row: dict[str, str] = {}
    for field in FIELDS:
        value = payload.get(field, "")
        if isinstance(value, list):
            value = join_semicolon([str(item) for item in value])
        row[field] = str(value or "").strip()

    row["active"] = normalize_bool(payload.get("active", row["active"] or "true"))
    row["aliases"] = join_semicolon(split_semicolon(row["aliases"]))
    row["related_names"] = join_semicolon(split_semicolon(row["related_names"]))
    row["flags_hint"] = join_semicolon(split_semicolon(row["flags_hint"]))
    return row


def validate_row(row: dict[str, str], rows: list[dict[str, str]], row_id: int | None = None) -> list[str]:
    errors: list[str] = []
    canonical_name = row["canonical_name"]
    if not canonical_name:
        errors.append("canonical_name is required")

    for index, existing in enumerate(rows):
        if row_id is not None and index == row_id:
            continue
        if canonical_name and existing.get("canonical_name") == canonical_name:
            errors.append("canonical_name already exists")
            break

    if row["category_hint"] not in ALLOWED_CATEGORY_HINTS:
        errors.append("category_hint is not allowed")

    invalid_flags = [flag for flag in split_semicolon(row["flags_hint"]) if flag not in ALLOWED_FLAGS]
    if invalid_flags:
        errors.append(f"flags_hint includes unsupported values: {', '.join(invalid_flags)}")

    return errors


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [field for field in FIELDS if field not in fieldnames]
        if missing:
            raise ValueError(f"dictionary is missing required columns: {', '.join(missing)}")
        return [
            {field: (row.get(field) or "").strip() for field in FIELDS}
            for row in reader
        ]


def write_rows(path: Path, rows: list[dict[str, str]]) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"context_aliases_{timestamp}.csv"
        shutil.copy2(path, backup_path)
    else:
        backup_path = BACKUP_DIR / "context_aliases_initial_missing.csv"

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})
    return backup_path


class AliasEditorHandler(BaseHTTPRequestHandler):
    dictionary_path: Path = DEFAULT_DICTIONARY

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/aliases":
            self.send_aliases()
            return
        if parsed.path == "/api/options":
            self.send_json(
                {
                    "fields": FIELDS,
                    "categoryHints": sorted(ALLOWED_CATEGORY_HINTS),
                    "flagHints": sorted(flag for flag in ALLOWED_FLAGS if flag),
                    "flagLabels": FLAG_LABELS_JA,
                }
            )
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/aliases":
            rows = read_rows(self.dictionary_path)
            row = normalize_row(self.read_json())
            errors = validate_row(row, rows)
            if errors:
                self.send_json({"errors": errors}, HTTPStatus.BAD_REQUEST)
                return
            rows.append(row)
            backup = write_rows(self.dictionary_path, rows)
            self.send_json({"rows": with_ids(rows), "backup": str(backup.relative_to(ROOT_DIR))})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        row_id = row_id_from_path(parsed.path)
        if row_id is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        rows = read_rows(self.dictionary_path)
        if row_id < 0 or row_id >= len(rows):
            self.send_json({"errors": ["row not found"]}, HTTPStatus.NOT_FOUND)
            return
        row = normalize_row(self.read_json())
        errors = validate_row(row, rows, row_id)
        if errors:
            self.send_json({"errors": errors}, HTTPStatus.BAD_REQUEST)
            return
        rows[row_id] = row
        backup = write_rows(self.dictionary_path, rows)
        self.send_json({"rows": with_ids(rows), "backup": str(backup.relative_to(ROOT_DIR))})

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        row_id = row_id_from_path(parsed.path)
        if row_id is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        rows = read_rows(self.dictionary_path)
        if row_id < 0 or row_id >= len(rows):
            self.send_json({"errors": ["row not found"]}, HTTPStatus.NOT_FOUND)
            return
        deleted = rows.pop(row_id)
        backup = write_rows(self.dictionary_path, rows)
        self.send_json(
            {
                "rows": with_ids(rows),
                "deleted": deleted.get("canonical_name", ""),
                "backup": str(backup.relative_to(ROOT_DIR)),
            }
        )

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("request body must be an object")
        return data

    def send_aliases(self) -> None:
        rows = read_rows(self.dictionary_path)
        self.send_json(
            {
                "dictionary": str(self.dictionary_path.relative_to(ROOT_DIR)),
                "rows": with_ids(rows),
                "updatedAt": datetime.now().isoformat(timespec="seconds"),
            }
        )

    def send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def serve_static(self, request_path: str) -> None:
        path = STATIC_DIR / ("index.html" if request_path in {"", "/"} else request_path.lstrip("/"))
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(STATIC_DIR.resolve()) or not resolved.is_file():
                raise FileNotFoundError
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content = resolved.read_bytes()
        content_type = content_type_for(resolved)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def with_ids(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [{**row, "id": index} for index, row in enumerate(rows)]


def row_id_from_path(path: str) -> int | None:
    parts = path.strip("/").split("/")
    if len(parts) == 3 and parts[:2] == ["api", "aliases"]:
        try:
            return int(parts[2])
        except ValueError:
            return None
    return None


def content_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".css":
        return "text/css; charset=utf-8"
    if suffix == ".js":
        return "application/javascript; charset=utf-8"
    return "text/html; charset=utf-8"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local context alias CSV editor.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8788, type=int)
    parser.add_argument("--dictionary", default=DEFAULT_DICTIONARY, type=Path)
    args = parser.parse_args()

    AliasEditorHandler.dictionary_path = args.dictionary.resolve()
    server = ThreadingHTTPServer((args.host, args.port), AliasEditorHandler)
    print(f"Context alias editor: http://{args.host}:{args.port}/")
    print(f"Dictionary: {AliasEditorHandler.dictionary_path}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
