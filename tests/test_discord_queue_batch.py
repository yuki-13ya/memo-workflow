from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).resolve().parents[1] / "discord-ingest" / "queue_batch.py"


def load_queue_batch_module():
    spec = importlib.util.spec_from_file_location("queue_batch", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load queue_batch module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


queue_batch = load_queue_batch_module()


def source_message(message_id: str, content: str) -> dict:
    return {
        "message_id": message_id,
        "created_at": "2026-07-04T00:00:00+00:00",
        "created_at_local": "2026-07-04T09:00:00+09:00",
        "author_name": "tester",
        "content": content,
        "attachments": [],
    }


def queue_entry(message_id: str, source_path: Path, **statuses: bool) -> dict:
    default_statuses = {
        "fetched": True,
        "todoCandidateGenerated": False,
        "reviewed": False,
        "confirmed": False,
        "executed": False,
        "ignored": False,
        "held": False,
    }
    default_statuses.update(statuses)
    return {
        "messageId": message_id,
        "createdAt": "2026-07-04T00:00:00+00:00",
        "createdAtLocal": "2026-07-04T09:00:00+09:00",
        "statuses": default_statuses,
        "files": {
            "discordMessagesFile": str(source_path),
            "todoCandidatesFile": "",
        },
    }


class DiscordQueueBatchTest(unittest.TestCase):
    def test_export_pending_uses_only_unprocessed_messages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / "discord_messages_2026-07-04.json"
            source_path.write_text(
                json.dumps(
                    {
                        "channel_id": "channel-1",
                        "channel_name": "memo",
                        "target_date": "2026-07-04",
                        "timezone": "Asia/Tokyo",
                        "messages": [
                            source_message("1", "pending"),
                            source_message("2", "already generated"),
                            source_message("3", "held"),
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            queue = {
                "messages": {
                    "1": queue_entry("1", source_path),
                    "2": queue_entry("2", source_path, todoCandidateGenerated=True),
                    "3": queue_entry("3", source_path, held=True),
                }
            }

            entries = queue_batch.pending_entries(queue)
            payload = queue_batch.build_batch_payload(temp_path / "state.json", entries)

        self.assertEqual([entry["messageId"] for entry in entries], ["1"])
        self.assertEqual(payload["message_count"], 1)
        self.assertEqual(payload["messages"][0]["message_id"], "1")
        self.assertEqual(payload["queue_batch"]["messageIds"], ["1"])
        self.assertEqual(payload["channel_name"], "memo")
        self.assertEqual(payload["timezone"], "Asia/Tokyo")

    def test_export_pending_does_not_mark_missing_source_as_message_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_path = temp_path / "discord_messages_2026-07-04.json"
            source_path.write_text(
                json.dumps(
                    {
                        "timezone": "Asia/Tokyo",
                        "messages": [source_message("1", "pending")],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            queue = {
                "messages": {
                    "1": queue_entry("1", source_path),
                    "missing": queue_entry("missing", source_path),
                }
            }

            entries = queue_batch.pending_entries(queue)
            payload = queue_batch.build_batch_payload(temp_path / "state.json", entries)

        self.assertEqual(payload["message_count"], 1)
        self.assertEqual(payload["queue_batch"]["messageIds"], ["1"])
        self.assertEqual(payload["queue_batch"]["pendingQueueEntryCount"], 2)
        self.assertEqual(payload["queue_batch"]["warningCount"], 1)

    def test_mark_todo_generated_reads_phase5_source_refs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            queue_path = temp_path / "discord_message_queue.json"
            source_path = temp_path / "todo_candidates.json"
            queue_path.write_text(
                json.dumps(
                    {
                        "messages": {
                            "1": queue_entry("1", temp_path / "source.json"),
                            "2": queue_entry("2", temp_path / "source.json"),
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            source_path.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "sourceRefs": [
                                    {"type": "discord_post", "id": "1"},
                                    {"type": "discord_post", "id": "missing"},
                                ]
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                result = queue_batch.mark_todo_generated(
                    SimpleNamespace(
                        queue_path=queue_path,
                        source_file=source_path,
                        todo_candidates_file=None,
                        dry_run=False,
                    )
                )
            updated = json.loads(queue_path.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertTrue(updated["messages"]["1"]["statuses"]["todoCandidateGenerated"])
        self.assertFalse(updated["messages"]["2"]["statuses"]["todoCandidateGenerated"])
        self.assertEqual(
            updated["messages"]["1"]["files"]["todoCandidatesFile"],
            str(source_path),
        )


if __name__ == "__main__":
    unittest.main()
