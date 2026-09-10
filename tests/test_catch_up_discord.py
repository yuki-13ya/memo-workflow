from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "discord-ingest"
sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("catch_up_discord", SCRIPT_DIR / "catch_up_discord.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class CatchUpDiscordTests(unittest.TestCase):
    def test_starts_one_day_before_latest_queued_message(self):
        queue = {
            "messages": {
                "1": {"createdAt": "2026-07-04T23:00:00+00:00"},
                "2": {"createdAt": "2026-07-06T01:00:00+00:00"},
            }
        }
        result = MODULE.range_start(
            queue, ZoneInfo("Asia/Tokyo"), date(2026, 7, 10), None, 1
        )
        self.assertEqual(date(2026, 7, 5), result)

    def test_empty_queue_uses_initial_from(self):
        result = MODULE.range_start(
            {"messages": {}},
            ZoneInfo("Asia/Tokyo"),
            date(2026, 7, 10),
            date(2026, 7, 1),
            1,
        )
        self.assertEqual(date(2026, 7, 1), result)
