import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from context_aliases import annotate_message, load_dictionary


def classify_messages(source_data, entries):
    results = []

    for message in source_data.get("messages", []):
        results.append(annotate_message(message, entries))

    return results


def write_markdown(path, source_data, dictionary_path, results):
    lines = [
        f"# Context Alias Test: {source_data.get('target_date', 'unknown')}",
        "",
        f"- source: `{source_data.get('target_date', 'unknown')}`",
        f"- dictionary: `{dictionary_path}`",
        f"- generated_at: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "## Results",
        "",
    ]

    for result in results:
        lines.extend(
            [
                f"### {result['created_at_local']} / {result['message_id']}",
                "",
                f"- status: `{result['context_match_status']}`",
                f"- context_label: `{result['context_label']}`",
                f"- category_hint: `{result['category_hint']}`",
                f"- flags_hint: `{', '.join(result['flags_hint'])}`",
                f"- ticktick_list_name: `{result['ticktick_list_name']}`",
                "",
                "```text",
                result["content"],
                "```",
                "",
            ]
        )

        if result["matched_candidates"]:
            lines.append("Matched candidates:")
            for candidate in result["matched_candidates"]:
                terms = ", ".join(
                    f"{term['term']} ({term['match_type']})"
                    for term in candidate["matched_terms"]
                )
                lines.append(f"- {candidate['canonical_name']}: {terms}")
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Test context alias dictionary against Phase 1 Discord JSON."
    )
    parser.add_argument("--input", required=True, type=Path, help="Phase 1 JSON file")
    parser.add_argument(
        "--dictionary",
        default=Path("config/context_aliases.csv"),
        type=Path,
        help="Context alias CSV dictionary",
    )
    parser.add_argument(
        "--output-dir",
        default=Path("outputs"),
        type=Path,
        help="Directory for test outputs",
    )
    args = parser.parse_args()

    entries = load_dictionary(args.dictionary)
    with args.input.open("r", encoding="utf-8") as handle:
        source_data = json.load(handle)

    results = classify_messages(source_data, entries)
    target_date = source_data.get("target_date") or "unknown-date"
    args.output_dir.mkdir(parents=True, exist_ok=True)

    output_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(args.input),
        "dictionary_file": str(args.dictionary),
        "target_date": target_date,
        "dictionary_entry_count": len(entries),
        "message_count": len(results),
        "matched_message_count": sum(
            1 for result in results if result["context_match_status"] != "unmatched"
        ),
        "results": results,
    }

    json_path = args.output_dir / f"context_alias_test_{target_date}.json"
    md_path = args.output_dir / f"context_alias_test_{target_date}.md"

    json_path.write_text(
        json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_markdown(md_path, source_data, args.dictionary, results)

    print(f"dictionary entries: {len(entries)}")
    print(f"messages checked: {len(results)}")
    print(f"matched messages: {output_data['matched_message_count']}")
    print(f"json output: {json_path}")
    print(f"markdown output: {md_path}")


if __name__ == "__main__":
    main()
