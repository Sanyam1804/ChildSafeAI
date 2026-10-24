
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tools


class TestProcedureRetrieval(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_file = Path(self.temp_dir.name) / "procedures.json"

        self.procedures = [
            {
                "id": "PROC001",
                "title": "Child Assistance",
                "keywords": ["child", "safety"],
                "content": "Provide child assistance and safety guidance.",
                "source": "Training procedure"
            },
            {
                "id": "PROC002",
                "title": "Missing Information",
                "keywords": ["missing", "verification"],
                "content": "Record missing information for verification.",
                "source": "Training procedure"
            },
            {
                "id": "PROC003",
                "title": "Referral Acknowledgement",
                "keywords": ["referral", "acknowledgement"],
                "content": "Track referral acknowledgement and escalation.",
                "source": "Training procedure"
            },
            {
                "id": "PROC004",
                "title": "Extra Procedure",
                "keywords": ["child", "referral"],
                "content": "Extra training procedure.",
                "source": "Training procedure"
            }
        ]

        self.write_data(self.procedures)
        self.patcher = patch.object(
            tools, "DATA_FILE", self.data_file
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def write_data(self, data):
        self.data_file.write_text(
            json.dumps(data),
            encoding="utf-8"
        )

    def test_relevant_results(self):
        results = tools.retrieve_protocol("child safety")
        self.assertTrue(results)
        self.assertEqual(results[0]["id"], "PROC001")

    def test_case_insensitive_search(self):
        results = tools.retrieve_protocol("CHILD SAFETY")
        self.assertTrue(results)
        self.assertEqual(results[0]["id"], "PROC001")

    def test_blank_and_invalid_queries(self):
        self.assertEqual(tools.retrieve_protocol(""), [])
        self.assertEqual(tools.retrieve_protocol("   "), [])
        self.assertEqual(tools.retrieve_protocol(None), [])

    def test_unrelated_query(self):
        self.assertEqual(
            tools.retrieve_protocol("xyzunrelated987"), []
        )

    def test_maximum_three_results(self):
        results = tools.retrieve_protocol("child referral safety")
        self.assertLessEqual(len(results), 3)

    def test_result_fields(self):
        results = tools.retrieve_protocol("child")
        self.assertTrue(results)

        expected = {
            "id", "title", "content", "source", "score"
        }
        self.assertEqual(set(results[0].keys()), expected)

    def test_missing_file(self):
        self.data_file.unlink()

        with self.assertRaises(FileNotFoundError):
            tools.retrieve_protocol("child")

    def test_malformed_json(self):
        self.data_file.write_text("{invalid", encoding="utf-8")

        with self.assertRaises(RuntimeError):
            tools.retrieve_protocol("child")

    def test_wrong_json_structure(self):
        self.write_data({"procedure": "not a list"})

        with self.assertRaises(RuntimeError):
            tools.retrieve_protocol("child")

    def test_missing_required_field(self):
        self.write_data([
            {
                "id": "PROC001",
                "title": "Child Assistance",
                "keywords": ["child"],
                "content": "Help children."
            }
        ])

        with self.assertRaises(RuntimeError):
            tools.retrieve_protocol("child")

    def test_results_are_deterministic(self):
        first = tools.retrieve_protocol("child referral safety")
        second = tools.retrieve_protocol("child referral safety")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)
