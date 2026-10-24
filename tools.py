
import re
from uuid import uuid4


def get_field(report, field):
    pattern = rf"(?im)^\s*{re.escape(field)}\s*:\s*(.+?)\s*$"
    match = re.search(pattern, report)

    if match:
        return match.group(1).strip()

    return None


def parse_case(report_text):
    report = report_text.strip()

    report_type = get_field(report, "Type")
    age_text = get_field(report, "Age")
    clothing = get_field(report, "Clothing")
    location = get_field(report, "Location")
    reported_time = get_field(report, "Time")
    description = get_field(report, "Description")
    source = get_field(report, "Reporter")

    if report_type:
        report_type = report_type.lower().strip()

    if report_type not in ("missing", "found"):
        report_type = None

    age = None

    if age_text:
        age_match = re.search(r"\d{1,2}", age_text)
        if age_match:
            age = int(age_match.group())

    unknown_fields = []

    if age is None:
        unknown_fields.append("age")

    if not clothing:
        unknown_fields.append("clothing")

    # Identity is never inferred or confirmed.
    unknown_fields.append("identity")

    return {
        "case_id": "DEMO-" + uuid4().hex[:8].upper(),
        "report_type": report_type,
        "age": age,
        "clothing": clothing,
        "location": location,
        "time": reported_time,
        "description": description,
        "source": source,
        "reported_location": location,
        "reported_time": reported_time,
        "immediate_concern": (
            "Reported alone; requires human assessment"
            if re.search(r"\balone\b", report, re.IGNORECASE)
            else None
        ),
        "unknown_fields": unknown_fields
    }


def find_missing_fields(case_data):
    required_fields = [
        "report_type",
        "reported_location",
        "reported_time",
        "description",
        "source"
    ]

    missing_fields = []

    for field in required_fields:
        value = case_data.get(field)

        if value is None or not str(value).strip():
            missing_fields.append(field)

    return missing_fields


def create_draft_referral(case_data, guidance_result, missing_fields):
    if isinstance(guidance_result, dict):
        guidance_text = guidance_result.get("passage")
        guidance_source = guidance_result.get("source_title")
    else:
        guidance_text = None
        guidance_source = None

    if not guidance_text:
        guidance_text = "No relevant approved guidance was found."
        guidance_source = "Unavailable"

    if missing_fields:
        missing_text = ", ".join(missing_fields)
    else:
        missing_text = "No required fields are missing."

    return {
        "status": "DRAFT — NOT SENT",
        "case_id": case_data.get("case_id"),
        "report_type": case_data.get("report_type"),
        "reported_facts": {
            "age": case_data.get("age"),
            "clothing": case_data.get("clothing"),
            "location": case_data.get("reported_location"),
            "time": case_data.get("reported_time"),
            "description": case_data.get("description"),
            "source": case_data.get("source"),
            "reported_concern": case_data.get("immediate_concern")
        },
        "unknown_fields": case_data.get("unknown_fields", []),
        "missing_required_fields": missing_text,
        "guidance": guidance_text,
        "guidance_source": guidance_source,
        "next_step": "Human review is required before any referral."
    }
