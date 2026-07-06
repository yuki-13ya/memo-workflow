#!/usr/bin/env python3
"""Phase 2 topic classification.

Reads Phase 1 Discord JSON, applies the context alias dictionary, optionally
asks Gemini for topic classification, then writes Phase 2 JSON and Markdown.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from context_aliases import annotate_message, load_dictionary


INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
DEFAULT_MODEL = "gemini-3.5-flash"
POLICY_VERSION = "phase2-topic-classification-v0.1"

ALLOWED_CATEGORIES = {
    "work",
    "health_lifestyle",
    "personal",
    "reference",
    "uncategorized",
}
ALLOWED_FLAGS = {
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
ALLOWED_CONFIDENCE = {"high", "medium", "low"}


class Phase2Error(RuntimeError):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(f"[{stage}] {message}")
        self.stage = stage


def load_dotenv(path: Path | None) -> None:
    if not path or not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_phase1_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise Phase2Error("input", f"input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise Phase2Error("input", f"input file is not valid JSON: {path}") from exc

    if not isinstance(data.get("messages"), list):
        raise Phase2Error("input", "input JSON does not include messages[]")
    return data


def build_ai_payload(source_data: dict[str, Any], annotated_messages: list[dict[str, Any]]) -> dict[str, Any]:
    messages = []
    for message in annotated_messages:
        messages.append(
            {
                "message_id": message["message_id"],
                "created_at_local": message["created_at_local"],
                "author_name": message["author_name"],
                "content": message["content"],
                "attachments": [
                    {
                        "filename": attachment.get("filename"),
                        "content_type": attachment.get("content_type"),
                        "download_status": attachment.get("download_status"),
                        "local_path": attachment.get("local_path"),
                    }
                    for attachment in message.get("attachments", [])
                ],
                "context_label": message["context_label"],
                "context_match_status": message["context_match_status"],
                "category_hint": message["category_hint"],
                "flags_hint": message["flags_hint"],
            }
        )

    return {
        "target_date": source_data.get("target_date"),
        "timezone": source_data.get("timezone"),
        "category_candidates": sorted(ALLOWED_CATEGORIES),
        "flag_candidates": sorted(ALLOWED_FLAGS),
        "messages": messages,
    }


def build_prompt(payload: dict[str, Any]) -> str:
    return (
        "あなたはDiscordに投稿された雑メモを、原文を変更せずにトピック分類する係です。\n"
        "出力は必ず指定JSONスキーマに従ってください。\n"
        "本文の修正、要約、補足を原文の代わりにしないでください。\n"
        "topic_titleやclassification_reasonにも、本文にない場所、関係、所属、理由を推測で足さないでください。\n"
        "たとえば「お母さん」「庭」だけから「実家」と決めつけず、本文にある表現だけを使ってください。\n"
        "context_labelが辞書照合で確定している場合は尊重してください。\n"
        "判断に迷うものはuncategorizedまたはneeds_reviewにしてください。\n"
        "TickTick、Notion、Discordへの操作は行わず、分類案だけを返してください。\n\n"
        f"入力JSON:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic_title": {"type": "string"},
                        "raw_context_label": {"type": "string"},
                        "category": {"type": "string", "enum": sorted(ALLOWED_CATEGORIES)},
                        "flags": {
                            "type": "array",
                            "items": {"type": "string", "enum": sorted(ALLOWED_FLAGS)},
                        },
                        "confidence": {"type": "string", "enum": sorted(ALLOWED_CONFIDENCE)},
                        "classification_reason": {"type": "string"},
                        "message_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "topic_title",
                        "raw_context_label",
                        "category",
                        "flags",
                        "confidence",
                        "classification_reason",
                        "message_ids",
                    ],
                },
            },
            "unclassified_message_ids": {"type": "array", "items": {"type": "string"}},
            "warnings": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["topics", "unclassified_message_ids", "warnings"],
    }


def call_gemini(api_key: str, model: str, prompt: str) -> dict[str, Any]:
    body = {
        "model": model,
        "input": prompt,
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": response_schema(),
        },
    }
    request = urllib.request.Request(
        INTERACTIONS_URL,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise Phase2Error("ai", f"Gemini request failed: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise Phase2Error("ai", f"Gemini request failed: {exc.reason}") from exc

    output_text = extract_output_text(response_body)
    if not output_text:
        raise Phase2Error("ai", "Gemini response did not include model output text")

    try:
        return json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise Phase2Error("ai", "Gemini output_text was not valid JSON") from exc


def extract_output_text(response_body: dict[str, Any]) -> str | None:
    if isinstance(response_body.get("output_text"), str):
        return response_body["output_text"]

    for step in response_body.get("steps", []):
        if not isinstance(step, dict) or step.get("type") != "model_output":
            continue
        for content in step.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                return content["text"]

    return None


def validate_ai_result(result: dict[str, Any], message_ids: set[str]) -> list[str]:
    warnings: list[str] = []
    used_message_ids: set[str] = set()

    if not isinstance(result.get("topics"), list):
        raise Phase2Error("ai_validation", "AI result does not include topics[]")

    for index, topic in enumerate(result["topics"], start=1):
        if topic.get("category") not in ALLOWED_CATEGORIES:
            raise Phase2Error("ai_validation", f"topic {index} has invalid category")
        if topic.get("confidence") not in ALLOWED_CONFIDENCE:
            raise Phase2Error("ai_validation", f"topic {index} has invalid confidence")

        invalid_flags = [flag for flag in topic.get("flags", []) if flag not in ALLOWED_FLAGS]
        if invalid_flags:
            raise Phase2Error("ai_validation", f"topic {index} has invalid flags: {invalid_flags}")

        for message_id in topic.get("message_ids", []):
            if message_id not in message_ids:
                warnings.append(f"AI referenced unknown message_id: {message_id}")
            elif message_id in used_message_ids:
                warnings.append(f"message_id appears in multiple topics: {message_id}")
            else:
                used_message_ids.add(message_id)

    return warnings


def build_fallback_result(annotated_messages: list[dict[str, Any]], reason: str) -> dict[str, Any]:
    return {
        "topics": [],
        "unclassified_message_ids": [message["message_id"] for message in annotated_messages],
        "warnings": [reason],
    }


def materialize_topics(ai_result: dict[str, Any], annotated_messages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    messages_by_id = {message["message_id"]: message for message in annotated_messages}
    used_ids: set[str] = set()
    topics: list[dict[str, Any]] = []

    for index, topic in enumerate(ai_result.get("topics", []), start=1):
        topic_messages = []
        for message_id in topic.get("message_ids", []):
            message = messages_by_id.get(message_id)
            if message:
                topic_messages.append(message)
                used_ids.add(message_id)

        if not topic_messages:
            continue

        first_with_context = next(
            (message for message in topic_messages if message.get("context_label")),
            None,
        )
        context_label = first_with_context["context_label"] if first_with_context else topic.get("raw_context_label", "")
        context_status = first_with_context["context_match_status"] if first_with_context else "ai_inferred"

        topics.append(
            {
                "topic_id": f"topic-{index:03d}",
                "topic_title": topic.get("topic_title", ""),
                "context_label": context_label,
                "raw_context_label": topic.get("raw_context_label", ""),
                "context_match_status": context_status,
                "category": topic.get("category", "uncategorized"),
                "flags": topic.get("flags", []),
                "confidence": topic.get("confidence", "low"),
                "classification_reason": topic.get("classification_reason", ""),
                "messages": topic_messages,
            }
        )

    explicit_unclassified = set(ai_result.get("unclassified_message_ids", []))
    unclassified = [
        message
        for message in annotated_messages
        if message["message_id"] not in used_ids or message["message_id"] in explicit_unclassified
    ]
    return topics, unclassified


def format_inline_code(value: Any) -> str:
    text = str(value or "")
    return f"`{text}`" if text else "`(empty)`"


def format_flags(flags: list[str]) -> str:
    return ", ".join(flags) if flags else "(none)"


def topic_review_points(topic: dict[str, Any]) -> list[str]:
    points: list[str] = []
    flags = set(topic.get("flags", []))
    context_status = topic.get("context_match_status", "")

    if "needs_review" in flags:
        points.append("needs_review flag is set")
    if topic.get("confidence") == "low":
        points.append("confidence is low")
    if topic.get("category") == "uncategorized":
        points.append("category is uncategorized")
    if context_status == "ambiguous":
        points.append("context dictionary matched multiple candidates")
    if context_status == "ai_inferred":
        points.append("context was inferred by AI or left outside the dictionary")
    if "task_hint" in flags and not topic.get("context_label"):
        points.append("task_hint has no dictionary-confirmed context_label")

    return points


def message_attachment_lines(message: dict[str, Any]) -> list[str]:
    attachments = message.get("attachments", [])
    if not attachments:
        return []

    lines = ["", "Attachments:"]
    for attachment in attachments:
        filename = attachment.get("filename") or "(no filename)"
        status = attachment.get("download_status") or "(unknown status)"
        local_path = attachment.get("local_path") or ""
        content_type = attachment.get("content_type") or ""
        detail_parts = [f"status={status}"]
        if content_type:
            detail_parts.append(f"type={content_type}")
        if local_path:
            detail_parts.append(f"local_path={local_path}")
        lines.append(f"- {filename} ({', '.join(detail_parts)})")
    return lines


def write_markdown(path: Path, output_data: dict[str, Any]) -> None:
    topics = output_data.get("topics", [])
    unclassified_messages = output_data.get("unclassified_messages", [])
    category_counts: dict[str, int] = {}
    flag_counts: dict[str, int] = {}
    review_topics: list[tuple[dict[str, Any], list[str]]] = []

    for topic in topics:
        category = topic.get("category", "uncategorized")
        category_counts[category] = category_counts.get(category, 0) + 1
        for flag in topic.get("flags", []):
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

        review_points = topic_review_points(topic)
        if review_points:
            review_topics.append((topic, review_points))

    total_messages = sum(len(topic.get("messages", [])) for topic in topics) + len(unclassified_messages)

    lines = [
        f"# Topic Classification: {output_data.get('target_date')}",
        "",
        f"- source: `{output_data.get('source_file')}`",
        f"- dictionary: `{output_data.get('dictionary_file')}`",
        f"- policy: `{output_data.get('classification_policy_version')}`",
        f"- generated_at: `{output_data.get('generated_at')}`",
        f"- ai_called: `{output_data.get('ai_called')}`",
        f"- dry_run: `{output_data.get('dry_run')}`",
        "",
    ]

    lines.extend(
        [
            "## Review Summary",
            "",
            f"- topics: {len(topics)}",
            f"- messages: {total_messages}",
            f"- unclassified_messages: {len(unclassified_messages)}",
            f"- review_topics: {len(review_topics)}",
            "",
            "### Category Counts",
            "",
        ]
    )
    if category_counts:
        for category, count in sorted(category_counts.items()):
            lines.append(f"- {category}: {count}")
    else:
        lines.append("- (none)")
    lines.extend(["", "### Flag Counts", ""])
    if flag_counts:
        for flag, count in sorted(flag_counts.items()):
            lines.append(f"- {flag}: {count}")
    else:
        lines.append("- (none)")
    lines.append("")

    if output_data.get("warnings"):
        lines.append("## Warnings")
        lines.append("")
        for warning in output_data["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")

    lines.append("## Review Needed")
    lines.append("")
    if not review_topics and not unclassified_messages:
        lines.append("_No automatic review candidates._")
        lines.append("")
    for topic, review_points in review_topics:
        lines.append(f"### {topic['topic_id']}: {topic['topic_title']}")
        lines.append("")
        lines.append(f"- category: {format_inline_code(topic.get('category'))}")
        lines.append(f"- flags: `{format_flags(topic.get('flags', []))}`")
        lines.append(f"- context_label: {format_inline_code(topic.get('context_label'))}")
        lines.append(f"- context_match_status: {format_inline_code(topic.get('context_match_status'))}")
        lines.append(f"- confidence: {format_inline_code(topic.get('confidence'))}")
        lines.append("- review_points:")
        for point in review_points:
            lines.append(f"  - {point}")
        lines.append("")
    if unclassified_messages:
        lines.append("### Unclassified Messages")
        lines.append("")
        lines.append(f"- count: {len(unclassified_messages)}")
        lines.append("- review_points:")
        lines.append("  - classification was not assigned")
        lines.append("  - confirm whether these should stay unclassified or be added to a topic")
        lines.append("")

    lines.append("## Topics")
    lines.append("")
    if not output_data.get("topics"):
        lines.append("_No classified topics._")
        lines.append("")

    for topic in output_data.get("topics", []):
        lines.extend(
            [
                f"### {topic['topic_id']}: {topic['topic_title']}",
                "",
                f"- context_label: `{topic['context_label']}`",
                f"- raw_context_label: `{topic.get('raw_context_label', '')}`",
                f"- context_match_status: `{topic['context_match_status']}`",
                f"- category: `{topic['category']}`",
                f"- flags: `{format_flags(topic['flags'])}`",
                f"- confidence: `{topic['confidence']}`",
                f"- review_points: `{format_flags(topic_review_points(topic))}`",
                f"- reason: {topic['classification_reason']}",
                "",
            ]
        )
        for message in topic["messages"]:
            lines.extend(
                [
                    f"#### {message['created_at_local']} / {message['message_id']}",
                    "",
                    "```text",
                    message["content"],
                    "```",
                    "",
                ]
            )
            lines.extend(message_attachment_lines(message))
            if message.get("matched_candidates"):
                lines.append("")
                lines.append("Dictionary matches:")
                for candidate in message["matched_candidates"]:
                    matched_terms = ", ".join(
                        f"{term['term']} ({term['match_type']})"
                        for term in candidate.get("matched_terms", [])
                    )
                    lines.append(f"- {candidate['canonical_name']}: {matched_terms}")
                lines.append("")

    lines.append("## Unclassified Messages")
    lines.append("")
    for message in output_data.get("unclassified_messages", []):
        lines.extend(
            [
                f"### {message['created_at_local']} / {message['message_id']}",
                "",
                f"- context_label: `{message.get('context_label', '')}`",
                f"- context_match_status: `{message.get('context_match_status', '')}`",
                "",
                "```text",
                message.get("content", ""),
                "```",
                "",
            ]
        )
        lines.extend(message_attachment_lines(message))

    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify Phase 1 Discord messages into Phase 2 topics.")
    parser.add_argument("--input", required=True, type=Path, help="Phase 1 Discord JSON")
    parser.add_argument("--dictionary", default=Path("config/context_aliases.csv"), type=Path)
    parser.add_argument("--output-dir", default=Path("outputs"), type=Path)
    parser.add_argument("--env-file", type=Path, help="Optional .env file to read")
    parser.add_argument("--model", default=os.getenv("MEMO_WORKFLOW_GEMINI_MODEL", DEFAULT_MODEL))
    parser.add_argument("--dry-run", action="store_true", help="Do not call Gemini; write fallback output")
    parser.add_argument("--use-ai", action="store_true", help="Explicitly allow calling Gemini")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(args.env_file)

    source_data = load_phase1_json(args.input)
    dictionary_entries = load_dictionary(args.dictionary)
    annotated_messages = [
        annotate_message(message, dictionary_entries)
        for message in source_data.get("messages", [])
    ]

    warnings: list[str] = []
    ai_result: dict[str, Any]
    ai_called = False
    if args.dry_run:
        ai_result = build_fallback_result(annotated_messages, "dry_run: Gemini was not called")
    elif not args.use_ai:
        ai_result = build_fallback_result(
            annotated_messages,
            "--use-ai was not specified; Gemini was not called",
        )
    else:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            ai_result = build_fallback_result(
                annotated_messages,
                "GEMINI_API_KEY is missing; Gemini was not called",
            )
        else:
            payload = build_ai_payload(source_data, annotated_messages)
            prompt = build_prompt(payload)
            try:
                ai_called = True
                ai_result = call_gemini(api_key, args.model, prompt)
                warnings.extend(
                    validate_ai_result(
                        ai_result,
                        {message["message_id"] for message in annotated_messages},
                    )
                )
            except Phase2Error as exc:
                ai_result = build_fallback_result(annotated_messages, str(exc))

    topics, unclassified_messages = materialize_topics(ai_result, annotated_messages)
    target_date = source_data.get("target_date") or "unknown-date"
    args.output_dir.mkdir(parents=True, exist_ok=True)

    warnings.extend(ai_result.get("warnings", []))
    output_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(args.input),
        "dictionary_file": str(args.dictionary),
        "target_date": target_date,
        "timezone": source_data.get("timezone"),
        "classification_policy_version": POLICY_VERSION,
        "ai_provider": "gemini",
        "ai_model": args.model,
        "ai_called": ai_called,
        "dry_run": args.dry_run,
        "topics": topics,
        "unclassified_messages": unclassified_messages,
        "warnings": sorted(set(warnings)),
    }

    json_path = args.output_dir / f"topic_classification_{target_date}.json"
    md_path = args.output_dir / f"topic_classification_{target_date}.md"
    json_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(md_path, output_data)

    print(f"messages: {len(annotated_messages)}")
    print(f"topics: {len(topics)}")
    print(f"unclassified: {len(unclassified_messages)}")
    print(f"warnings: {len(output_data['warnings'])}")
    print(f"json output: {json_path}")
    print(f"markdown output: {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
