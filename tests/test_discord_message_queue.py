from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "discord-ingest" / "ingest_discord.py"


def load_ingest_module():
    spec = importlib.util.spec_from_file_location("ingest_discord", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load ingest_discord module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ingest = load_ingest_module()


def message(message_id: str, content: str, created_at: str) -> dict:
    return {
        "message_id": message_id,
        "created_at": created_at,
        "created_at_local": created_at,
        "author_name": "tester",
        "content": content,
        "attachments": [],
    }


class DiscordMessageQueueTest(unittest.TestCase):
    def test_merge_payload_by_message_id_appends_new_messages(self) -> None:
        existing = {
            "target_date": "2026-07-04",
            "messages": [message("1", "old", "2026-07-04T09:00:00+09:00")],
        }
        incoming = {
            "target_date": "2026-07-04",
            "messages": [
                message("1", "old", "2026-07-04T09:00:00+09:00"),
                message("2", "new", "2026-07-04T10:00:00+09:00"),
            ],
        }

        merged, summary = ingest.merge_payload_by_message_id(existing, incoming)

        self.assertEqual([item["message_id"] for item in merged["messages"]], ["1", "2"])
        self.assertEqual(merged["message_count"], 2)
        self.assertEqual(summary["existing_message_count"], 1)
        self.assertEqual(summary["incoming_message_count"], 2)
        self.assertEqual(summary["new_message_count"], 1)
        self.assertEqual(summary["changed_existing_count"], 0)

    def test_merge_payload_keeps_existing_when_duplicate_content_changed(self) -> None:
        existing = {
            "target_date": "2026-07-04",
            "messages": [message("1", "original", "2026-07-04T09:00:00+09:00")],
        }
        incoming = {
            "target_date": "2026-07-04",
            "messages": [message("1", "edited", "2026-07-04T09:00:00+09:00")],
        }

        merged, summary = ingest.merge_payload_by_message_id(existing, incoming)

        self.assertEqual(merged["messages"][0]["content"], "original")
        self.assertEqual(summary["changed_existing_count"], 1)

    def test_update_queue_preserves_existing_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            queue_path = temp_path / "state" / "discord_message_queue.json"
            queue_path.parent.mkdir(parents=True)
            queue_path.write_text(
                json.dumps(
                    {
                        "schemaVersion": "1.0",
                        "updatedAt": "2026-07-04T00:00:00+09:00",
                        "messages": {
                            "1": {
                                "messageId": "1",
                                "contentHash": ingest.content_hash(
                                    message("1", "old", "2026-07-04T09:00:00+09:00")
                                ),
                                "statuses": {
                                    "fetched": True,
                                    "todoCandidateGenerated": True,
                                    "reviewed": True,
                                },
                                "files": {
                                    "discordMessagesFile": "old.json",
                                    "todoCandidatesFile": "todo.json",
                                },
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            payload = {
                "target_date": "2026-07-04",
                "messages": [
                    message("1", "old", "2026-07-04T09:00:00+09:00"),
                    message("2", "new", "2026-07-04T10:00:00+09:00"),
                ],
            }

            summary = ingest.update_queue(queue_path, payload, temp_path / "out.json")
            queue = json.loads(queue_path.read_text(encoding="utf-8"))

        self.assertEqual(summary, {"queue_added": 1, "queue_updated": 1, "queue_total": 2})
        self.assertTrue(queue["messages"]["1"]["statuses"]["todoCandidateGenerated"])
        self.assertTrue(queue["messages"]["1"]["statuses"]["reviewed"])
        self.assertEqual(
            queue["messages"]["1"]["files"]["discordMessagesFile"],
            str(temp_path / "out.json"),
        )
        self.assertEqual(queue["messages"]["2"]["statuses"]["fetched"], True)
        self.assertEqual(queue["messages"]["2"]["statuses"]["reviewed"], False)


if __name__ == "__main__":
    unittest.main()
