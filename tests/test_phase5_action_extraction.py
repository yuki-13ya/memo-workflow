from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "phase5-todo-candidates"
    / "export_todo_candidates.py"
)


def load_phase5_module():
    spec = importlib.util.spec_from_file_location("export_todo_candidates", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load export_todo_candidates module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


phase5 = load_phase5_module()


TODO_MESSAGE = {
    "message_id": "todo-message-1",
    "created_at_local": "2026-07-04T13:28:13+09:00",
    "author_name": "tester",
    "content": (
        "来月の集まりの予定を担当者に伝えないといけないな。\n\n"
        "あと、備品を買いたい。\n"
        "打ち合わせ用の延長コードと名札ケース。\n"
        "ネットで買うか、店舗に行くか迷う。\n\n"
        "企画の話が変わったのは痛かったなぁ。\n"
        "だけど、研修として使えそうなので、ちょっと組み直そうと思う。\n"
        "専門家に相談しないといけない。\n\n"
        "案内資料を作らないと。これはちょっと急ぎかも。\n"
        "だけど、申込フォームの確認の方が先。"
    ),
    "attachments": [],
}


class Phase5ActionExtractionTest(unittest.TestCase):
    def test_mixed_diary_and_todo_message_extracts_distinct_actions(self) -> None:
        source_data = {
            "topics": [
                {
                    "topic_id": "topic-001",
                    "topic_title": "雨の日の散歩の記録",
                    "category": "personal",
                    "flags": ["outing_related", "health_or_care"],
                    "confidence": "high",
                    "context_match_status": "ai_inferred",
                    "messages": [
                        {
                            "message_id": "diary-message-1",
                            "created_at_local": "2026-07-04T09:00:00+09:00",
                            "content": "雨の中を散歩。\n少し疲れている気がする。",
                            "attachments": [],
                        }
                    ],
                },
                {
                    "topic_id": "topic-002",
                    "topic_title": "来月の集まりの予定の伝達",
                    "classification_reason": "来月の集まりの予定を担当者に伝える用事。",
                    "category": "personal",
                    "flags": ["travel_related", "schedule_related", "task_hint"],
                    "confidence": "high",
                    "context_match_status": "ai_inferred",
                    "messages": [TODO_MESSAGE],
                },
                {
                    "topic_id": "topic-003",
                    "topic_title": "打ち合わせ備品の購入検討",
                    "classification_reason": "打ち合わせ用の延長コードと名札ケースの購入検討。",
                    "category": "personal",
                    "flags": ["task_hint"],
                    "confidence": "high",
                    "context_match_status": "ai_inferred",
                    "messages": [TODO_MESSAGE],
                },
                {
                    "topic_id": "topic-004",
                    "topic_title": "研修企画の組み直し、案内資料作成、申込フォーム確認",
                    "classification_reason": "専門家への相談、案内資料作成、申込フォーム確認に関する内容。",
                    "category": "work",
                    "flags": ["task_hint"],
                    "confidence": "high",
                    "context_match_status": "ai_inferred",
                    "messages": [TODO_MESSAGE],
                },
            ]
        }

        output, warnings = phase5.build_output(
            source_data,
            Path("topic_classification_queue_batch.json"),
            "2026-07-04",
            "2026-07-04T00:00:00+00:00",
            False,
            [],
        )

        titles = [item["proposedTitle"] for item in output["items"]]

        self.assertEqual(warnings, [])
        self.assertEqual(
            titles,
            [
                "来月の集まりの予定を担当者に伝えないといけない",
                "備品を買いたい（打ち合わせ用の延長コードと名札ケース）",
                "専門家に相談しないといけない",
                "案内資料を作らないと、これはちょっと急ぎ",
                "申込フォームの確認の方が先",
            ],
        )
        self.assertEqual(len(set(titles)), len(titles))


if __name__ == "__main__":
    unittest.main()
