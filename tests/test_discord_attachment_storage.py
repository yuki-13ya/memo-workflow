from __future__ import annotations

import importlib.util
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "discord-ingest"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("ingest_discord", SCRIPT_DIR / "ingest_discord.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class DiscordAttachmentStorageTests(unittest.TestCase):
    def test_explicit_root_uses_message_folder_and_original_filename(self):
        records = [
            {
                "message_id": "123456789012345678",
                "attachments": [
                    {
                        "attachment_id": "987",
                        "filename": "IMG_1234.jpg",
                        "url": "https://example.invalid/IMG_1234.jpg",
                        "download_status": "pending",
                    }
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            attachment_root = Path(temp_dir) / "attachments"

            def fake_download(_url: str, destination: Path) -> None:
                destination.write_bytes(b"image")

            with patch.object(MODULE, "download_attachment", side_effect=fake_download):
                MODULE.download_supported_attachments(
                    records,
                    Path(temp_dir) / "outputs",
                    "2026-09-12",
                    logging.getLogger("test"),
                    attachment_root,
                )

            expected = attachment_root / "123456789012345678" / "IMG_1234.jpg"
            self.assertTrue(expected.is_file())
            self.assertEqual(str(expected), records[0]["attachments"][0]["local_path"])
            self.assertEqual("downloaded", records[0]["attachments"][0]["download_status"])

    def test_multiple_images_share_message_folder(self):
        records = [
            {
                "message_id": "123",
                "attachments": [
                    {"attachment_id": "1", "filename": "a.jpg", "url": "x", "download_status": "pending"},
                    {"attachment_id": "2", "filename": "b.png", "url": "y", "download_status": "pending"},
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "attachments"

            def fake_download(_url: str, destination: Path) -> None:
                destination.write_bytes(b"image")

            with patch.object(MODULE, "download_attachment", side_effect=fake_download):
                MODULE.download_supported_attachments(
                    records, Path(temp_dir) / "outputs", "2026-09-12", logging.getLogger("test"), root
                )

            self.assertEqual({"a.jpg", "b.png"}, {path.name for path in (root / "123").iterdir()})


if __name__ == "__main__":
    unittest.main()
