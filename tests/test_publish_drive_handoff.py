import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "discord-ingest"
    / "publish_drive_handoff.py"
)
SPEC = importlib.util.spec_from_file_location("publish_drive_handoff", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PublishDriveHandoffTests(unittest.TestCase):
    def payload(self, content="first"):
        return {
            "generated_at": "2026-09-10T00:00:00Z",
            "channel_id": "channel-1",
            "target_date": "2026-09-10",
            "timezone": "Asia/Tokyo",
            "messages": [{"message_id": "1", "content": content}],
        }

    def test_publishes_once_and_skips_unchanged_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.json"
            inbox = root / "inbox"
            state = root / "state.json"
            source.write_text(json.dumps(self.payload()), encoding="utf-8")

            first = MODULE.publish(source, inbox, state)
            second = MODULE.publish(source, inbox, state)

            self.assertIsNotNone(first)
            self.assertTrue(first.exists())
            self.assertIsNone(second)
            self.assertEqual(1, len(list(inbox.glob("*.json"))))

    def test_skips_payload_without_messages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.json"
            inbox = root / "inbox"
            state = root / "state.json"
            payload = self.payload()
            payload["messages"] = []
            source.write_text(json.dumps(payload), encoding="utf-8")

            result = MODULE.publish(source, inbox, state)

            self.assertIsNone(result)
            self.assertFalse(inbox.exists())
            self.assertFalse(state.exists())

    def test_publishes_again_when_message_content_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.json"
            inbox = root / "inbox"
            state = root / "state.json"
            source.write_text(json.dumps(self.payload()), encoding="utf-8")
            MODULE.publish(source, inbox, state)
            source.write_text(json.dumps(self.payload("updated")), encoding="utf-8")

            result = MODULE.publish(source, inbox, state)

            self.assertIsNotNone(result)
            self.assertEqual(2, len(list(inbox.glob("*.json"))))


if __name__ == "__main__":
    unittest.main()
