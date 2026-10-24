
import unittest

from tools import (
    parse_case,
    find_missing_fields,
    create_draft_referral,
)


class TestChildSafeAI(unittest.TestCase):

    def test_valid_report_is_parsed(self):
        report = (
            "A child was reported alone near platform 2 "
            "at Jaipur railway station around 10 AM. "
            "The reporter is a station staff member. "
            "The child's age is unknown."
        )

        case_data = parse_case(report)

        self.assertEqual(
            case_data["reported_location"],
            "platform 2 at Jaipur railway station"
        )
        self.assertEqual(case_data["reported_time"], "around 10 AM")
        self.assertIn("age", case_data["unknown_fields"])

    def test_valid_report_has_no_missing_required_fields(self):
        report = (
            "A child was reported alone near platform 2 "
            "at Jaipur railway station around 10 AM. "
            "The reporter is a station staff member."
        )

        case_data = parse_case(report)
        missing_fields = find_missing_fields(case_data)

        self.assertEqual(missing_fields, [])

    def test_referral_draft_is_not_sent(self):
        report = (
            "A child was reported near platform 2 "
            "at Jaipur railway station around 10 AM. "
            "The reporter is a station staff member."
        )

        case_data = parse_case(report)
        missing_fields = find_missing_fields(case_data)

        draft = create_draft_referral(
            case_data,
            {
                "passage": "Synthetic demo guidance.",
                "source_title": "Synthetic demo guidance",
                "source_url": None,
            },
            missing_fields,
        )

        self.assertEqual(draft["status"], "DRAFT — NOT SENT")
        self.assertIn("Human review", draft["next_step"])

    def test_missing_location_is_flagged(self):
        report = (
            "A child was reported alone around 10 AM. "
            "The reporter is a station staff member."
        )

        case_data = parse_case(report)
        missing_fields = find_missing_fields(case_data)

        self.assertIsNone(case_data["reported_location"])
        self.assertIn("reported_location", missing_fields)

    def test_missing_time_is_flagged(self):
        report = (
            "A child was reported alone near platform 2 "
            "at Jaipur railway station. "
            "The reporter is a station staff member."
        )

        case_data = parse_case(report)
        missing_fields = find_missing_fields(case_data)

        self.assertIsNone(case_data["reported_time"])
        self.assertIn("reported_time", missing_fields)

    def test_empty_report_flags_required_fields(self):
        case_data = parse_case("")
        missing_fields = find_missing_fields(case_data)

        self.assertIsNone(case_data["description"])
        self.assertIn("reported_location", missing_fields)
        self.assertIn("reported_time", missing_fields)
        self.assertIn("description", missing_fields)
        self.assertIn("source", missing_fields)

    def test_missing_reporter_is_flagged(self):
        report = (
            "A child was reported alone near platform 2 "
            "at Jaipur railway station around 10 AM."
        )

        case_data = parse_case(report)
        missing_fields = find_missing_fields(case_data)

        self.assertIsNone(case_data["source"])
        self.assertIn("source", missing_fields)

    def test_unknown_age_and_identity_are_preserved(self):
        report = (
            "A child was reported near platform 2 "
            "at Jaipur railway station around 10 AM. "
            "The reporter is a station staff member."
        )

        case_data = parse_case(report)

        self.assertIn("age", case_data["unknown_fields"])
        self.assertIn("identity", case_data["unknown_fields"])

    def test_missing_guidance_uses_fallback(self):
        case_data = parse_case(
            "A child was reported near platform 2 "
            "at Jaipur railway station around 10 AM. "
            "The reporter is a station staff member."
        )

        draft = create_draft_referral(
            case_data,
            None,
            find_missing_fields(case_data),
        )

        self.assertEqual(
            draft["guidance"],
            "No relevant approved guidance was found."
        )
        self.assertEqual(draft["guidance_source"], "Unavailable")
        self.assertEqual(draft["status"], "DRAFT — NOT SENT")

    def test_draft_preserves_parsed_location_and_time(self):
        report = (
            "A child was reported near platform 2 "
            "at Jaipur railway station around 10 AM. "
            "The reporter is a station staff member."
        )

        case_data = parse_case(report)
        draft = create_draft_referral(
            case_data,
            None,
            find_missing_fields(case_data),
        )

        self.assertEqual(
            draft["reported_facts"]["location"],
            case_data["reported_location"],
        )
        self.assertEqual(
            draft["reported_facts"]["time"],
            case_data["reported_time"],
        )


if __name__ == "__main__":
    unittest.main()
