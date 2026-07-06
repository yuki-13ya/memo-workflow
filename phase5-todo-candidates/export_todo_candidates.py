#!/usr/bin/env python3
"""Phase 5 TODO candidate export.

Reads Phase 2 topic classification JSON and writes the local JSON/Markdown
handoff files consumed by the separate ticktick-task project. This script never
calls AI APIs and never writes to TickTick, Notion, or Discord.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
INTAKE_SOURCE = "memo_workflow_todo_candidate"
CREATED_BY = "memo-workflow"
ALLOWED_STATUSES = {"todo_candidate", "hold_candidate", "non_todo"}
ALLOWED_ESTIMATED_MINUTES = (15, 30, 45, 60, 90, 120, 150, 180)
CONFIDENCE_MAP = {
    "high": 0.9,
    "medium": 0.6,
    "low": 0.3,
}


class Phase5Error(RuntimeError):
    """Error with a phase-specific stage label for safe logging."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(f"[{stage}] {message}")
        self.stage = stage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Phase 5 TODO candidate JSON from Phase 2 topic classification JSON."
    )
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format.")
    parser.add_argument(
        "--input",
        type=Path,
        help="Phase 2 topic classification JSON. Defaults to outputs/topic_classification_YYYY-MM-DD.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output TODO candidate JSON. Defaults to outputs/ticktick_todo_candidates_YYYY-MM-DD.json.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional review Markdown output. Defaults to the matching outputs/ticktick_todo_candidates_YYYY-MM-DD.md.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Default output directory used when explicit paths are omitted.",
    )
    parser.add_argument(
        "--dictionary",
        type=Path,
        default=Path("config/context_aliases.csv"),
        help="Context alias CSV used to re-check split bullet candidates.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("logs"),
        help="Directory for the Phase 5 log file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run local read/build/validation/write only. No external services are used in any mode.",
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Skip writing the human review Markdown file.",
    )
    parser.add_argument(
        "--include-non-todo",
        action="store_true",
        help="Also keep topics outside TODO extraction as non_todo candidates.",
    )
    return parser.parse_args()


def setup_logger(log_dir: Path, target_date: str) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("phase5_todo_candidates")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s %(levelname)s stage=%(stage)s %(message)s")
    log_path = log_dir / f"phase5_todo_candidates_{target_date}.log"
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


def load_phase2_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise Phase5Error("input_load", f"input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise Phase5Error("input_load", f"input file is not valid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise Phase5Error("input_validate", "input JSON root must be an object")
    if not isinstance(data.get("topics"), list):
        raise Phase5Error("input_validate", "input JSON does not include topics[]")
    return data


def resolve_target_date(args: argparse.Namespace, source_data: dict[str, Any] | None = None) -> str:
    target_date = args.date or (source_data or {}).get("target_date")
    if not target_date:
        if args.input:
            match = re.search(r"(\d{4}-\d{2}-\d{2})", args.input.name)
            if match:
                target_date = match.group(1)
    if not target_date:
        raise Phase5Error("date_resolve", "target date requires --date or input target_date")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(target_date)):
        raise Phase5Error("date_resolve", "target date must use YYYY-MM-DD")
    return str(target_date)


def default_input_path(target_date: str) -> Path:
    return Path("outputs") / f"topic_classification_{target_date}.json"


def default_output_path(output_dir: Path, target_date: str) -> Path:
    return output_dir / f"ticktick_todo_candidates_{target_date}.json"


def default_markdown_path(output_dir: Path, target_date: str) -> Path:
    return output_dir / f"ticktick_todo_candidates_{target_date}.md"


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def text_or_empty(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_confidence(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        numeric = float(value)
        if 0.0 <= numeric <= 1.0:
            return numeric
        return None
    if isinstance(value, str):
        return CONFIDENCE_MAP.get(value.strip().lower())
    return None


def topic_flags(topic: dict[str, Any]) -> list[str]:
    return [str(flag) for flag in as_list(topic.get("flags")) if str(flag)]


def topic_messages(topic: dict[str, Any]) -> list[dict[str, Any]]:
    return [message for message in as_list(topic.get("messages")) if isinstance(message, dict)]


def split_semicolon_list(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def load_context_dictionary(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        entries: list[dict[str, Any]] = []
        for row in reader:
            if (row.get("active") or "").strip().lower() not in {"true", "1", "yes", "y"}:
                continue
            canonical_name = text_or_empty(row.get("canonical_name"))
            if not canonical_name:
                continue
            entries.append(
                {
                    "canonical_name": canonical_name,
                    "aliases": split_semicolon_list(row.get("aliases")),
                    "related_names": split_semicolon_list(row.get("related_names")),
                    "category_hint": text_or_empty(row.get("category_hint")),
                    "flags_hint": split_semicolon_list(row.get("flags_hint")),
                }
            )
    return entries


def find_context_matches(text: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for entry in entries:
        terms = [entry["canonical_name"], *entry["aliases"], *entry["related_names"]]
        if any(term and term in text for term in terms):
            matches.append(entry)
    return matches


def context_for_text(
    text: str,
    entries: list[dict[str, Any]],
) -> tuple[str | None, str, str | None, list[str]]:
    matches = find_context_matches(text, entries)
    if not matches:
        return None, "unmatched", None, []
    if len(matches) > 1:
        flags: list[str] = ["needs_review"]
        for match in matches:
            flags.extend(match["flags_hint"])
        return None, "ambiguous", None, sorted(set(flags))
    match = matches[0]
    return (
        match["canonical_name"],
        "alias_matched",
        match["category_hint"] or None,
        match["flags_hint"],
    )


def build_source_refs(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for message in messages:
        message_id = text_or_empty(message.get("message_id"))
        created_at = text_or_empty(message.get("created_at_local") or message.get("created_at"))
        if message_id or created_at:
            refs.append(
                {
                    "type": "discord_post",
                    "id": message_id,
                    "time": created_at,
                }
            )
    return refs


def extract_evidence_text(messages: list[dict[str, Any]]) -> str:
    contents = [text_or_empty(message.get("content")) for message in messages]
    return "\n\n".join(content for content in contents if content)


def extract_attachments(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    attachments: list[dict[str, Any]] = []
    for message in messages:
        for attachment in as_list(message.get("attachments")):
            if not isinstance(attachment, dict):
                continue
            attachments.append(
                {
                    "messageId": text_or_empty(message.get("message_id")),
                    "attachmentId": attachment.get("attachment_id") or attachment.get("id"),
                    "filename": attachment.get("filename"),
                    "contentType": attachment.get("content_type"),
                    "downloadStatus": attachment.get("download_status"),
                }
            )
    return attachments


def needs_human_review(
    status: str,
    flags: list[str],
    context_status: str,
    context_label: str | None,
    confidence: float | None,
    category: str | None,
) -> list[str]:
    reasons: list[str] = []
    flag_set = set(flags)

    if status == "non_todo":
        return reasons
    if status == "hold_candidate":
        reasons.append("候補として重要そうだが、登録前に確認や分解が必要。")
    if "needs_review" in flag_set:
        reasons.append("Phase 2でneeds_reviewフラグが付いている。")
    if "money_related" in flag_set:
        reasons.append("費用、請求、収入に関係する判断が含まれる可能性がある。")
    if "schedule_related" in flag_set:
        reasons.append("日程、頻度、時間確保に関係する確認が必要。")
    if context_status in {"ambiguous", "ai_inferred", "unmatched", "none"} or not context_label:
        reasons.append("文脈ラベルが未確定または辞書確定ではない。")
    if confidence is not None and confidence < 0.5:
        reasons.append("候補化の確信度が低い。")
    if category == "uncategorized":
        reasons.append("カテゴリがuncategorizedである。")

    return list(dict.fromkeys(reasons))


def build_blocking_hints(
    status: str,
    flags: list[str],
    context_status: str,
    context_label: str | None,
    human_review_required: bool,
) -> list[str]:
    hints: list[str] = []
    flag_set = set(flags)

    if human_review_required:
        hints.append("needs_review")
    if status == "hold_candidate":
        hints.append("needs_breakdown")
    if "schedule_related" in flag_set:
        hints.append("schedule_related")
    if "money_related" in flag_set:
        hints.append("money_related")
    if context_status in {"ambiguous", "ai_inferred", "unmatched", "none"} or not context_label:
        hints.append("context_unclear")
    if status == "non_todo":
        hints.extend(["reference_only", "not_task_like"])

    return list(dict.fromkeys(hints))


def classify_topic(topic: dict[str, Any]) -> str | None:
    flags = set(topic_flags(topic))
    category = text_or_none(topic.get("category"))
    confidence = normalize_confidence(topic.get("confidence"))
    context_label = text_or_none(topic.get("context_label"))
    context_status = text_or_empty(topic.get("context_match_status") or topic.get("contextLabelStatus"))

    if "task_hint" in flags:
        review_reasons = needs_human_review(
            "todo_candidate",
            list(flags),
            context_status,
            context_label,
            confidence,
            category,
        )
        return "hold_candidate" if review_reasons else "todo_candidate"

    reviewable_flags = {"schedule_related", "money_related", "needs_review"}
    if flags & reviewable_flags:
        return "hold_candidate"

    return None


def strip_bullet_marker(line: str) -> str:
    return re.sub(r"^\s*(?:[-*・•]|[0-9]+[.)、])\s*", "", line).strip()


def extract_action_lines(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for message in messages:
        content = text_or_empty(message.get("content"))
        raw_lines = content.splitlines()
        for line_index, raw_line in enumerate(raw_lines):
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped in {"やること", "TODO", "todo", "タスク"}:
                continue
            bullet_line = bool(re.match(r"^\s*(?:[-*・•]|[0-9]+[.)、])\s*", stripped))
            task_text = strip_bullet_marker(stripped)
            if bullet_line or is_task_like_text(task_text):
                detail = action_line_detail(task_text, raw_lines[line_index + 1 :])
                lines.append(
                    {
                        "text": task_text,
                        "detail": detail,
                        "message": message,
                        "bullet": bullet_line,
                    }
                )
    bullet_count = sum(1 for line in lines if line["bullet"])
    if bullet_count >= 2:
        return [line for line in lines if line["bullet"] and is_task_like_text(line["text"])]
    return [line for line in lines if is_task_like_text(line["text"])]


def action_line_detail(task_text: str, following_lines: list[str]) -> str:
    normalized = text_or_empty(task_text)
    if "買いたい" not in normalized:
        return ""
    details: list[str] = []
    for raw_line in following_lines:
        line = raw_line.strip()
        if not line:
            break
        if is_task_like_text(line):
            break
        if any(marker in line for marker in ["迷う", "かな", "かも"]):
            break
        details.append(line.rstrip("。"))
        if len(details) >= 1:
            break
    return " / ".join(details)


def is_task_like_text(text: str) -> bool:
    normalized = text_or_empty(text)
    if not normalized:
        return False
    markers = [
        "やること",
        "ないと",
        "しないと",
        "しなくては",
        "しなければ",
        "買いたい",
        "できていない",
        "出せていない",
        "連絡する",
        "確認する",
        "決める",
        "考える",
        "修正する",
        "納品する",
        "アップ",
        "UP",
        "保存",
        "計算",
        "頑張らないと",
        "進める",
        "方が先",
    ]
    return any(marker in normalized for marker in markers)


def normalize_action_text(text: str) -> str:
    normalized = strip_bullet_marker(text)
    normalized = re.sub(r"^(?:あと|だけど|それから|そうだ)[、,]\s*", "", normalized).strip()
    normalized = re.sub(r"[。．]+$", "", normalized).strip()
    normalized = re.sub(r"(?:かな|かも|な)$", "", normalized).strip()
    normalized = normalized.replace("。これは", "、これは")
    normalized = re.sub(r"(これはちょっと急ぎ)(?:かも)?$", r"\1", normalized).strip()
    return normalized


def action_line_key(action_line: dict[str, Any]) -> tuple[str, str]:
    message = action_line.get("message", {})
    message_id = text_or_empty(message.get("message_id"))
    return message_id, normalize_action_text(text_or_empty(action_line.get("text")))


def topic_relevance_text(topic: dict[str, Any]) -> str:
    parts = [
        text_or_empty(topic.get("topic_title") or topic.get("topicTitle")),
        text_or_empty(topic.get("classification_reason") or topic.get("classificationReason")),
        text_or_empty(topic.get("category")),
        " ".join(topic_flags(topic)),
    ]
    return " ".join(part for part in parts if part)


def action_keywords(text: str) -> list[str]:
    normalized = normalize_action_text(text)
    normalized = re.sub(
        r"(しないといけない|しないと|しなくては|しなければ|しないといけない|"
        r"伝えないといけない|伝えないと|買いたい|作らないと|方が先|これはちょっと急ぎ)",
        " ",
        normalized,
    )
    chunks = re.split(r"[、。・/／\s（）()]+|として|について|こと|もの|ため|あと|だけど|これは|"
                      r"の|を|に|へ|が|は|で|と|や|も|か", normalized)
    stop_words = {"外", "中", "先", "今日", "昨日", "ちょっと", "ラフ", "いけない"}
    keywords = []
    for chunk in chunks:
        word = chunk.strip()
        if len(word) < 2 or word in stop_words:
            continue
        keywords.append(word)
    return keywords


def is_action_relevant_to_topic(action_line: dict[str, Any], topic: dict[str, Any]) -> bool:
    relevance_text = topic_relevance_text(topic)
    action_text = " ".join(
        [
            text_or_empty(action_line.get("text")),
            text_or_empty(action_line.get("detail")),
        ]
    )
    keywords = action_keywords(action_text)
    if not keywords:
        return True
    return any(keyword in relevance_text for keyword in keywords)


def line_flags(text: str, context_flags: list[str]) -> list[str]:
    flags = [*context_flags, "task_hint"]
    if any(marker in text for marker in ["お金", "費用", "請求", "見積", "収入", "売上"]):
        flags.append("money_related")
    if any(marker in text for marker in ["今日", "明日", "日", "時間", "予約", "予定"]):
        flags.append("schedule_related")
    return sorted(set(flags))


def round_to_allowed_minutes(minutes: int | None) -> int | None:
    if minutes is None or minutes <= 0:
        return None
    for allowed in ALLOWED_ESTIMATED_MINUTES:
        if minutes <= allowed:
            return allowed
    return None


def extract_duration_minutes(text: str) -> list[int]:
    normalized = text_or_empty(text)
    if not normalized:
        return []

    minutes: list[int] = []
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*時間半", normalized, flags=re.IGNORECASE):
        minutes.append(round(float(match.group(1)) * 60 + 30))
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:時間(?!半)|h|hr|hrs)", normalized, flags=re.IGNORECASE):
        minutes.append(round(float(match.group(1)) * 60))
    for match in re.finditer(r"(\d+)\s*(?:分|m|min|mins)", normalized, flags=re.IGNORECASE):
        minutes.append(int(match.group(1)))
    return minutes


def keyword_estimated_minutes(text: str) -> int | None:
    normalized = text_or_empty(text)
    if not normalized:
        return None

    keyword_rules = [
        (120, ["動画", "カット編集", "編集して公開"]),
        (90, ["ホームページ", "サイト", "営業", "集客", "資料作成"]),
        (60, ["編集", "修正", "納品", "作成", "作る", "考える", "進める"]),
        (30, ["計算", "予約", "調べる", "決める"]),
        (15, ["連絡", "メッセージ", "確認", "保存", "告知", "お知らせ", "アップロード", "アップ", "UP"]),
    ]
    for minutes, keywords in keyword_rules:
        if any(keyword in normalized for keyword in keywords):
            return minutes
    return None


def estimate_minutes_candidate(
    status: str,
    evidence_text: str,
    proposed_title: str,
    proposed_items: list[str],
) -> int | None:
    if status == "non_todo":
        return None

    for texts in ([evidence_text], proposed_items, [proposed_title]):
        explicit_minutes = [
            minute
            for text in texts
            for minute in extract_duration_minutes(text)
            if minute > 0
        ]
        if explicit_minutes:
            return round_to_allowed_minutes(sum(explicit_minutes))

    keyword_candidates = []
    for text in [evidence_text, proposed_title, *proposed_items]:
        candidate = keyword_estimated_minutes(text)
        if candidate is not None:
            keyword_candidates.append(candidate)
    if keyword_candidates:
        return max(candidate for candidate in keyword_candidates if candidate is not None)
    return None


def title_from_action_text(text: str) -> tuple[str, list[str]]:
    normalized = normalize_action_text(text)
    normalized = re.sub(r"^早く\s*", "", normalized).strip()
    proposed_items: list[str] = []

    if "→" in normalized:
        before_steps, raw_steps = normalized, normalized
        if "ので、" in normalized:
            before_steps, raw_steps = normalized.split("ので、", 1)
        subject = before_steps
        subject = re.sub(r"が出せていない$", "", subject).strip()
        subject = re.sub(r"ができていない$", "", subject).strip()
        steps = [step.strip() for step in raw_steps.split("→") if step.strip()]
        proposed_items = [normalize_step_title(step) for step in steps]
        if any("Youtube" in step or "YouTube" in step or "UP" in step for step in steps):
            return f"{subject}を公開する", proposed_items
        return subject or normalized, proposed_items

    match = re.fullmatch(r"(.+?)、(.+?)関連", normalized)
    if match:
        return f"{match.group(2)}関連で{match.group(1)}", proposed_items

    if "頑張らないと" in normalized:
        subject = normalized.split("頑張らないと", 1)[0]
        subject = re.sub(r"^.*。", "", subject).strip()
        if subject:
            return f"{subject}の次の一手を決める", proposed_items

    match = re.fullmatch(r"(.+?)(?:しないと|伝えないと)(?:いけない|いかん)?", normalized)
    if match:
        target = match.group(1).strip()
        if target.endswith("の計算"):
            return f"{target}をする", proposed_items
        if target.endswith("の保存"):
            return f"{target}対応をする", proposed_items
        return normalized, proposed_items

    return normalized, proposed_items


def build_proposed_items(raw_items: list[str], status: str) -> list[dict[str, Any]]:
    structured_items: list[dict[str, Any]] = []
    for index, raw_item in enumerate(raw_items, start=1):
        title = text_or_empty(raw_item)
        if not title:
            continue
        structured_items.append(
            {
                "title": title,
                "estimatedMinutesCandidate": estimate_minutes_candidate(status, title, title, []),
                "order": index,
            }
        )
    return structured_items


def proposed_item_titles(items: list[dict[str, Any]]) -> list[str]:
    return [text_or_empty(item.get("title")) for item in items if text_or_empty(item.get("title"))]


def normalize_step_title(step: str) -> str:
    normalized = step.strip()
    if normalized.lower() in {"youtubeにup", "youtubeにアップ"}:
        return "YouTubeにアップする"
    if normalized.endswith("する"):
        return normalized
    if normalized.endswith("すること"):
        return normalized
    if normalized in {"お知らせ", "告知"}:
        return f"{normalized}する"
    if normalized in {"カット編集", "編集"}:
        return f"{normalized}する"
    return normalized


def classify_action_line(text: str) -> str:
    if "頑張らないと" in text:
        return "hold_candidate"
    return "todo_candidate"


def build_candidate(
    topic: dict[str, Any],
    index: int,
    source_date: str,
    include_non_todo: bool,
    dictionary_entries: list[dict[str, Any]],
    action_line: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    status = classify_action_line(action_line["text"]) if action_line else classify_topic(topic)
    if status is None:
        if not include_non_todo:
            return None
        status = "non_todo"

    topic_base_flags = topic_flags(topic)
    messages = [action_line["message"]] if action_line else topic_messages(topic)
    topic_id = text_or_empty(topic.get("topic_id") or topic.get("topicId") or f"topic-{index:03d}")
    topic_title = text_or_empty(topic.get("topic_title") or topic.get("topicTitle") or topic_id)
    if action_line:
        action_text = action_line["text"]
        context_label, context_status, category_hint, context_flags = context_for_text(
            action_text,
            dictionary_entries,
        )
        flags = line_flags(action_text, context_flags)
        category = category_hint or text_or_none(topic.get("category"))
        evidence_text = action_text
        source_title, raw_proposed_items = title_from_action_text(action_text)
        detail = text_or_empty(action_line.get("detail"))
        if detail and detail not in source_title:
            source_title = f"{source_title}（{detail}）"
    else:
        flags = topic_base_flags
        context_label = text_or_none(topic.get("context_label") or topic.get("contextLabel"))
        context_status = text_or_empty(
            topic.get("context_match_status") or topic.get("contextLabelStatus") or "none"
        )
        category = text_or_none(topic.get("category"))
        evidence_text = extract_evidence_text(messages)
        source_title = topic_title
        raw_proposed_items = []
    confidence = normalize_confidence(topic.get("confidence"))
    source_refs = build_source_refs(messages)

    review_reasons = needs_human_review(
        status,
        flags,
        context_status,
        context_label,
        confidence,
        category,
    )
    human_review_required = bool(review_reasons)
    blocking_hint = build_blocking_hints(
        status,
        flags,
        context_status,
        context_label,
        human_review_required,
    )

    title = source_title
    if context_label and context_label not in title:
        title = f"{context_label}: {title}"
    proposed_items = build_proposed_items(raw_proposed_items, status)
    estimated_minutes_candidate = estimate_minutes_candidate(
        status,
        evidence_text,
        title,
        proposed_item_titles(proposed_items),
    )
    if status != "non_todo" and estimated_minutes_candidate is None:
        blocking_hint = list(dict.fromkeys([*blocking_hint, "needs_duration_estimate"]))

    source_context = {
        "originalSource": "phase2_topic_classification",
        "topicId": topic_id,
        "topicTitle": topic_title,
        "extractionMode": "message_line" if action_line else "topic",
        "contextLabel": context_label,
        "contextLabelStatus": context_status,
        "category": category,
        "flags": flags,
        "confidence": confidence,
    }

    attachments = extract_attachments(messages)
    if attachments:
        source_context["attachments"] = attachments

    candidate = {
        "sourceId": f"todo-{source_date}-{index:03d}",
        "intakeSource": INTAKE_SOURCE,
        "sourceDate": source_date,
        "sourceTitle": source_title,
        "sourceText": evidence_text,
        "sourceRefs": source_refs,
        "sourceContext": source_context,
        "initialStatus": status,
        "proposedTitle": title,
        "proposedDescription": build_description(status, flags),
        "proposedItems": proposed_items,
        "estimatedMinutesCandidate": estimated_minutes_candidate,
        "needsReview": human_review_required,
        "reviewReason": " ".join(review_reasons) if review_reasons else None,
        "blockingHint": blocking_hint,
        "humanDecision": "",
        "humanMemo": "",
    }

    return candidate


def build_description(status: str, flags: list[str]) -> str:
    if status == "todo_candidate":
        return "Phase 2でtask_hintが付いたトピックから抽出したTODO候補。"
    if status == "hold_candidate":
        if "task_hint" in flags:
            return "Phase 2でtask_hintが付いたが、人間確認や分解が必要なTODO候補。"
        return "task_hintはないが、仕様上確認対象にできる内容として保留候補にしたもの。"
    return "TODO候補として扱わない内容。"


def build_output(
    source_data: dict[str, Any],
    source_file: Path,
    source_date: str,
    created_at: str,
    include_non_todo: bool,
    dictionary_entries: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    topics = source_data.get("topics", [])
    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen_action_keys: set[tuple[str, str]] = set()

    for topic_index, topic in enumerate(topics, start=1):
        if not isinstance(topic, dict):
            warnings.append(f"topic_index={topic_index} skipped_non_object")
            continue
        try:
            action_lines = [
                line
                for line in extract_action_lines(topic_messages(topic))
                if is_action_relevant_to_topic(line, topic)
            ]
            unique_action_lines = []
            for action_line in action_lines:
                key = action_line_key(action_line)
                if key in seen_action_keys:
                    continue
                seen_action_keys.add(key)
                unique_action_lines.append(action_line)
            action_lines = unique_action_lines
            if action_lines:
                candidates = [
                    build_candidate(
                        topic,
                        len(items) + line_index,
                        source_date,
                        include_non_todo,
                        dictionary_entries,
                        action_line,
                    )
                    for line_index, action_line in enumerate(action_lines, start=1)
                ]
            else:
                candidates = [
                    build_candidate(
                        topic,
                        len(items) + 1,
                        source_date,
                        include_non_todo,
                        dictionary_entries,
                    )
                ]
        except Exception as exc:  # noqa: BLE001 - keep stage-level error while continuing safely.
            warnings.append(f"topic_index={topic_index} skipped_error={exc.__class__.__name__}")
            continue
        items.extend(candidate for candidate in candidates if candidate)

    summary = {
        "totalItems": len(items),
        "candidateCount": sum(1 for item in items if item["initialStatus"] == "todo_candidate"),
        "holdCount": sum(1 for item in items if item["initialStatus"] == "hold_candidate"),
        "excludedCount": sum(1 for item in items if item["initialStatus"] == "non_todo"),
        "needsReviewCount": sum(1 for item in items if item["needsReview"]),
    }

    return (
        {
            "schemaVersion": SCHEMA_VERSION,
            "intakeSource": INTAKE_SOURCE,
            "sourceFile": str(source_file),
            "sourceDate": source_date,
            "createdAt": created_at,
            "createdBy": CREATED_BY,
            "summary": summary,
            "items": items,
        },
        warnings,
    )


def validate_output(data: dict[str, Any]) -> None:
    required_top = [
        "schemaVersion",
        "intakeSource",
        "sourceFile",
        "sourceDate",
        "createdAt",
        "createdBy",
        "summary",
        "items",
    ]
    missing_top = [name for name in required_top if name not in data]
    if missing_top:
        raise Phase5Error("output_validate", f"missing top-level fields: {', '.join(missing_top)}")
    if data.get("intakeSource") != INTAKE_SOURCE:
        raise Phase5Error("output_validate", "intakeSource must be memo_workflow_todo_candidate")
    if not isinstance(data.get("items"), list):
        raise Phase5Error("output_validate", "items must be an array")

    required_candidate = [
        "sourceId",
        "intakeSource",
        "sourceDate",
        "sourceTitle",
        "sourceText",
        "sourceRefs",
        "sourceContext",
        "initialStatus",
        "proposedTitle",
        "proposedDescription",
        "proposedItems",
        "estimatedMinutesCandidate",
        "needsReview",
        "reviewReason",
        "blockingHint",
        "humanDecision",
        "humanMemo",
    ]
    for index, candidate in enumerate(data["items"], start=1):
        if not isinstance(candidate, dict):
            raise Phase5Error("output_validate", f"item {index} must be an object")
        missing = [name for name in required_candidate if name not in candidate]
        if missing:
            raise Phase5Error(
                "output_validate",
                f"item {index} missing fields: {', '.join(missing)}",
            )
        if not candidate.get("sourceId"):
            raise Phase5Error("output_validate", f"item {index} sourceId is empty")
        if candidate.get("intakeSource") != INTAKE_SOURCE:
            raise Phase5Error("output_validate", f"item {index} has invalid intakeSource")
        if candidate.get("initialStatus") not in ALLOWED_STATUSES:
            raise Phase5Error("output_validate", f"item {index} has invalid initialStatus")
        if not isinstance(candidate.get("sourceRefs"), list):
            raise Phase5Error("output_validate", f"item {index} sourceRefs must be an array")
        if not isinstance(candidate.get("sourceContext"), dict):
            raise Phase5Error("output_validate", f"item {index} sourceContext must be an object")
        if not isinstance(candidate.get("proposedItems"), list):
            raise Phase5Error("output_validate", f"item {index} proposedItems must be an array")
        for item_index, proposed_item in enumerate(candidate.get("proposedItems", []), start=1):
            if not isinstance(proposed_item, dict):
                raise Phase5Error(
                    "output_validate",
                    f"item {index} proposedItems[{item_index}] must be an object",
                )
            if not text_or_none(proposed_item.get("title")):
                raise Phase5Error(
                    "output_validate",
                    f"item {index} proposedItems[{item_index}] title is required",
                )
            item_minutes = proposed_item.get("estimatedMinutesCandidate")
            if item_minutes is not None and item_minutes not in ALLOWED_ESTIMATED_MINUTES:
                raise Phase5Error(
                    "output_validate",
                    f"item {index} proposedItems[{item_index}] estimatedMinutesCandidate must be one of {ALLOWED_ESTIMATED_MINUTES} or null",
                )
        estimated_minutes = candidate.get("estimatedMinutesCandidate")
        if estimated_minutes is not None and estimated_minutes not in ALLOWED_ESTIMATED_MINUTES:
            raise Phase5Error(
                "output_validate",
                f"item {index} estimatedMinutesCandidate must be one of {ALLOWED_ESTIMATED_MINUTES} or null",
            )
        if not isinstance(candidate.get("needsReview"), bool):
            raise Phase5Error(
                "output_validate",
                f"item {index} needsReview must be boolean",
            )
        if candidate.get("needsReview") and not text_or_none(candidate.get("reviewReason")):
            raise Phase5Error("output_validate", f"item {index} reviewReason is required")
        if not isinstance(candidate.get("blockingHint"), list):
            raise Phase5Error("output_validate", f"item {index} blockingHint must be an array")
        if not isinstance(candidate.get("humanDecision"), str):
            raise Phase5Error("output_validate", f"item {index} humanDecision must be a string")
        if not isinstance(candidate.get("humanMemo"), str):
            raise Phase5Error("output_validate", f"item {index} humanMemo must be a string")

    try:
        json.loads(json.dumps(data, ensure_ascii=False))
    except json.JSONDecodeError as exc:
        raise Phase5Error("output_validate", "output is not JSON serializable") from exc


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, data: dict[str, Any], warnings: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    summary = data["summary"]
    lines = [
        f"# TickTick TODO Candidates: {data['sourceDate']}",
        "",
        f"- source: `{data['sourceFile']}`",
        f"- generated_at: `{data['createdAt']}`",
        f"- schema_version: `{data['schemaVersion']}`",
        "",
        "## Summary",
        "",
        f"- total_items: {summary['totalItems']}",
        f"- todo_candidate: {summary['candidateCount']}",
        f"- hold_candidate: {summary['holdCount']}",
        f"- non_todo: {summary['excludedCount']}",
        f"- needs_review: {summary['needsReviewCount']}",
        f"- warnings: {len(warnings)}",
        "",
    ]

    if warnings:
        lines.extend(["## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.extend(["## Candidates", ""])
    if not data["items"]:
        lines.extend(["_No TODO candidates._", ""])

    for candidate in data["items"]:
        source_context = candidate.get("sourceContext", {})
        source_refs = candidate.get("sourceRefs", [])
        source_ref_ids = [
            text_or_empty(ref.get("id")) for ref in source_refs if isinstance(ref, dict)
        ]
        lines.extend(
            [
                f"### {candidate['sourceId']}: {candidate['proposedTitle']}",
                "",
                f"- initial_status: `{candidate['initialStatus']}`",
                f"- topic_id: `{source_context.get('topicId') or ''}`",
                f"- context_label: `{source_context.get('contextLabel') or ''}`",
                f"- context_label_status: `{source_context.get('contextLabelStatus') or ''}`",
                f"- category: `{source_context.get('category') or ''}`",
                f"- flags: `{', '.join(source_context.get('flags', []))}`",
                f"- confidence: `{source_context.get('confidence')}`",
                f"- estimated_minutes_candidate: `{candidate.get('estimatedMinutesCandidate')}`",
                f"- needs_review: `{candidate['needsReview']}`",
                f"- review_reason: {candidate.get('reviewReason') or ''}",
                f"- blocking_hint: `{', '.join(candidate.get('blockingHint', []))}`",
                f"- source_ref_ids: `{', '.join(source_ref_ids)}`",
                "",
                "```text",
                candidate.get("sourceText") or "",
                "```",
                "",
            ]
        )
        proposed_items = candidate.get("proposedItems", [])
        if proposed_items:
            lines.extend(["proposed_items:", ""])
            for proposed_item in proposed_items:
                if not isinstance(proposed_item, dict):
                    continue
                item_title = text_or_empty(proposed_item.get("title"))
                item_minutes = proposed_item.get("estimatedMinutesCandidate")
                suffix = f" ({item_minutes}m)" if item_minutes else ""
                lines.append(f"- {item_title}{suffix}")
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    logger = logging.getLogger("phase5_todo_candidates")
    try:
        args = parse_args()
        initial_date = args.date
        input_path = args.input or (default_input_path(initial_date) if initial_date else None)
        if input_path is None:
            raise Phase5Error("date_resolve", "--date or --input is required")

        source_data = load_phase2_json(input_path)
        target_date = resolve_target_date(args, source_data)
        logger = setup_logger(args.log_dir, target_date)
        log_info(logger, "input_load", f"input={input_path}")

        output_path = args.output or default_output_path(args.output_dir, target_date)
        markdown_path = args.markdown_output or default_markdown_path(args.output_dir, target_date)
        created_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        dictionary_entries = load_context_dictionary(args.dictionary)

        topics = source_data.get("topics", [])
        log_info(logger, "input_validate", f"topics={len(topics)}")
        output_data, warnings = build_output(
            source_data,
            input_path,
            target_date,
            created_at,
            args.include_non_todo,
            dictionary_entries,
        )
        log_info(
            logger,
            "candidate_build",
            f"items={len(output_data['items'])} warnings={len(warnings)} dry_run={args.dry_run} include_non_todo={args.include_non_todo}",
        )

        validate_output(output_data)
        log_info(logger, "output_validate", "validation succeeded")

        write_json(output_path, output_data)
        if args.no_markdown:
            markdown_path = None
        else:
            write_markdown(markdown_path, output_data, warnings)

        log_info(
            logger,
            "output_save",
            f"json={output_path} markdown={markdown_path or '(skipped)'}",
        )

        print(f"topics: {len(topics)}")
        print(f"items: {len(output_data['items'])}")
        print(f"warnings: {len(warnings)}")
        print(f"json output: {output_path}")
        if markdown_path:
            print(f"markdown output: {markdown_path}")
        print("external writes: none")
        return 0
    except Phase5Error as exc:
        if logger.handlers:
            log_error(logger, exc.stage, str(exc))
        else:
            print(f"ERROR stage={exc.stage} {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
