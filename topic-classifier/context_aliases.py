import csv
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = {
    "canonical_name",
    "aliases",
    "related_names",
    "ticktick_list_name",
    "category_hint",
    "flags_hint",
    "active",
    "notes",
}


def split_list(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def load_dictionary(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"dictionary is missing required columns: {missing_text}")

        entries: list[dict[str, Any]] = []
        for row_number, row in enumerate(reader, start=2):
            if (row.get("active") or "").strip().lower() not in {"true", "1", "yes", "y"}:
                continue

            canonical_name = (row.get("canonical_name") or "").strip()
            if not canonical_name:
                raise ValueError(f"dictionary row {row_number} has empty canonical_name")

            entries.append(
                {
                    "row_number": row_number,
                    "canonical_name": canonical_name,
                    "aliases": split_list(row.get("aliases")),
                    "related_names": split_list(row.get("related_names")),
                    "ticktick_list_name": (row.get("ticktick_list_name") or "").strip(),
                    "category_hint": (row.get("category_hint") or "").strip(),
                    "flags_hint": split_list(row.get("flags_hint")),
                    "notes": (row.get("notes") or "").strip(),
                }
            )

    return entries


def find_matches(content: str, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    text = content or ""

    for entry in entries:
        matched_terms: list[dict[str, str]] = []

        if entry["canonical_name"] and entry["canonical_name"] in text:
            matched_terms.append(
                {"term": entry["canonical_name"], "match_type": "canonical_name"}
            )

        for alias in entry["aliases"]:
            if alias in text:
                matched_terms.append({"term": alias, "match_type": "alias"})

        for related_name in entry["related_names"]:
            if related_name in text:
                matched_terms.append(
                    {"term": related_name, "match_type": "related_name"}
                )

        if matched_terms:
            matches.append({**entry, "matched_terms": matched_terms})

    return matches


def status_for_matches(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return "unmatched"
    if len(matches) > 1:
        return "ambiguous"

    match_types = {term["match_type"] for term in matches[0]["matched_terms"]}
    if "canonical_name" in match_types:
        return "canonical_matched"
    if "alias" in match_types:
        return "alias_matched"
    if "related_name" in match_types:
        return "related_name_matched"
    return "unmatched"


def annotate_message(message: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    matches = find_matches(message.get("content", ""), entries)
    status = status_for_matches(matches)
    single_match = matches[0] if len(matches) == 1 else None

    flags: list[str] = []
    if single_match:
        flags.extend(single_match["flags_hint"])
    elif len(matches) > 1:
        flags.append("needs_review")

    return {
        "message_id": message.get("message_id"),
        "created_at_local": message.get("created_at_local"),
        "author_name": message.get("author_name"),
        "content": message.get("content", ""),
        "attachments": message.get("attachments", []),
        "context_match_status": status,
        "context_label": single_match["canonical_name"] if single_match else "",
        "category_hint": single_match["category_hint"] if single_match else "",
        "flags_hint": sorted(set(flags)),
        "ticktick_list_name": single_match["ticktick_list_name"] if single_match else "",
        "matched_candidates": [
            {
                "canonical_name": match["canonical_name"],
                "matched_terms": match["matched_terms"],
                "ticktick_list_name": match["ticktick_list_name"],
                "category_hint": match["category_hint"],
                "flags_hint": match["flags_hint"],
                "notes": match["notes"],
            }
            for match in matches
        ],
    }
