
import json
import re
from uuid import uuid4
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "procedures.json"

REQUIRED_FIELDS = ("id", "title", "content", "source")


def load_procedures():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Procedure database not found: {DATA_FILE}"
        )

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            procedures = json.load(file)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Procedure database contains invalid JSON"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            "Procedure database could not be read"
        ) from exc

    if not isinstance(procedures, list):
        raise RuntimeError(
            "Procedure database must contain a JSON list"
        )

    for index, procedure in enumerate(procedures):
        if not isinstance(procedure, dict):
            raise RuntimeError(
                f"Procedure at index {index} must be an object"
            )

        for field in REQUIRED_FIELDS:
            if not isinstance(procedure.get(field), str):
                raise RuntimeError(
                    f"Procedure at index {index} has invalid field: {field}"
                )

        keywords = procedure.get("keywords")

        if (
            not isinstance(keywords, list)
            or not all(
                isinstance(keyword, str) for keyword in keywords
            )
        ):
            raise RuntimeError(
                f"Procedure at index {index} has invalid keywords"
            )

    return procedures


def retrieve_protocol(query):
    if not isinstance(query, str) or not query.strip():
        return []

    procedures = load_procedures()

    query_words = set(
        re.findall(r"\b\w+\b", query.casefold())
    )

    if not query_words:
        return []

    results = []

    for procedure in procedures:
        searchable_text = " ".join([
            procedure["title"],
            " ".join(procedure["keywords"]),
            procedure["content"]
        ]).casefold()

        searchable_words = set(
            re.findall(r"\b\w+\b", searchable_text)
        )

        matched_words = query_words & searchable_words

        if matched_words:
            results.append({
                "id": procedure["id"],
                "title": procedure["title"],
                "content": procedure["content"],
                "source": procedure["source"],
                "score": len(matched_words)
            })

    results.sort(
        key=lambda item: (
            -item["score"],
            item["title"].casefold(),
            item["id"]
        )
    )

    return results[:3]


def get_field(report, field):
    pattern = rf"(?im)^\s*{re.escape(field)}\s*:\s*(.+?)\s*$"
    match = re.search(pattern, report)

    if match:
        return match.group(1).strip()

    return None


def clean_value(value):
    if not value:
        return None

    value = value.strip().rstrip(".,; ")

    return value or None


def extract_time(report):
    match = re.search(
        r"\b(?:around|at about|at approximately|at)\s+"
        r"\d{1,2}(?::\d{2})?\s*(?:AM|PM|a\.m\.|p\.m\.)\b",
        report,
        re.IGNORECASE,
    )

    if match:
        return match.group(0).strip()

    return None


def extract_location(report):
    match = re.search(
        r"\bnear\s+(.+?)"
        r"(?=\s+(?:around|at about|at approximately)\s+\d"
        r"|\s+the reporter\b"
        r"|\s+the child's\b"
        r"|[.!?]|$)",
        report,
        re.IGNORECASE,
    )

    if match:
        return clean_value(match.group(1))

    return None


def extract_reporter(report):
    patterns = [
        r"\bthe reporter is\s+(.+?)(?=[.!?]|$)",
        r"\breported by\s+(.+?)(?=[.!?]|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, report, re.IGNORECASE)

        if match:
            return clean_value(match.group(1))

    return None


def infer_report_type(report):
    text = report.lower()

    missing_patterns = [
        r"\bmissing child\b",
        r"\bchild is missing\b",
        r"\bchild went missing\b",
        r"\bchild has gone missing\b",
        r"\bchild was reported missing\b",
        r"\bchild is lost\b",
    ]

    found_patterns = [
        r"\bchild was found\b",
        r"\bfound child\b",
        r"\bchild was reported alone\b",
        r"\bchild was seen alone\b",
        r"\bchild found alone\b",
    ]

    if any(re.search(pattern, text) for pattern in missing_patterns):
        return "missing"

    if any(re.search(pattern, text) for pattern in found_patterns):
        return "found"

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
        report_type = infer_report_type(report)

    if not location:
        location = extract_location(report)

    if not reported_time:
        reported_time = extract_time(report)

    if not source:
        source = extract_reporter(report)

    age = None

    if age_text and not re.search(r"\bunknown\b", age_text, re.IGNORECASE):
        age_match = re.search(r"\b\d{1,2}\b", age_text)

        if age_match:
            age = int(age_match.group())

    unknown_fields = []

    if age is None:
        unknown_fields.append("age")

    if not clothing:
        unknown_fields.append("clothing")

    unknown_fields.append("identity")

    if not description and report:
        description = report

    immediate_concern = None

    if re.search(r"\balone\b", report, re.IGNORECASE):
        immediate_concern = "Reported alone; requires human assessment"

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
        "immediate_concern": immediate_concern,
        "unknown_fields": unknown_fields,
    }


def find_missing_fields(case_data):
    required_fields = [
        "report_type",
        "reported_location",
        "reported_time",
        "description",
        "source",
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
            "reported_concern": case_data.get("immediate_concern"),
        },
        "unknown_fields": case_data.get("unknown_fields", []),
        "missing_required_fields": missing_text,
        "guidance": guidance_text,
        "guidance_source": guidance_source,
        "next_step": "Human review is required before any referral.",
    }
