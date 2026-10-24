
import re


def parse_case(report_text):
    report = report_text.strip()

    # Extract a reported time, if one is explicitly mentioned.
    time_match = re.search(
        r"\b(?:around|at|approximately)\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM)\b",
        report,
        re.IGNORECASE
    )

    reported_time = time_match.group(0) if time_match else None

    # Extract a location using simple location phrases.
    location_match = re.search(
        r"\b(?:near|at)\s+(.+?)(?=\s+\b(?:around|at)\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM)\b|[,.]|$)",
        report,
        re.IGNORECASE
    )

    reported_location = location_match.group(1).strip() if location_match else None

    # Extract the reporter, if the report mentions one.
    source_match = re.search(
        r"\breporter\s+is\s+(.+?)(?:[,.]|$)",
        report,
        re.IGNORECASE
    )

    source = source_match.group(1).strip() if source_match else None

    # Keep the original report as the description.
    description = report if report else None

    # Only flag a concern when the report explicitly mentions it.
    if re.search(r"\balone\b", report, re.IGNORECASE):
        immediate_concern = "Reported alone; requires human assessment"
    else:
        immediate_concern = None

    # This demo does not identify children.
    # Age is unknown unless an age is explicitly mentioned.
    age_match = re.search(
        r"\b(\d{1,2})\s*(?:years?\s*old|year-old)\b",
        report,
        re.IGNORECASE
    )

    unknown_fields = []

    if not age_match:
        unknown_fields.append("age")

    # Identity is not inferred or matched by this tool.
    unknown_fields.append("identity")

    return {
        "case_id": "DEMO-001",
        "reported_location": reported_location,
        "reported_time": reported_time,
        "description": description,
        "immediate_concern": immediate_concern,
        "source": source,
        "unknown_fields": unknown_fields
    }


def find_missing_fields(case_data):
    required_fields = [
        "reported_location",
        "reported_time",
        "description",
        "source"
    ]

    missing_fields = []

    for field in required_fields:
        value = case_data.get(field)

        if not value or not str(value).strip():
            missing_fields.append(field)

    return missing_fields


def create_draft_referral(case_data, guidance_result, missing_fields):
    # Show only the guidance actually returned by P3.
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

    draft = {
        "status": "DRAFT — NOT SENT",
        "case_id": case_data.get("case_id", "DEMO-001"),
        "reported_facts": {
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

    return draft
