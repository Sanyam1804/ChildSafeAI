
from datetime import date


def compare_cases(found_child, missing_report):
    score = 0
    max_score = 0
    reasons = []

    # Approximate age: useful for screening, not identification
    found_age = found_child.get("age")
    reported_age = missing_report.get("age")

    if found_age is not None and reported_age is not None:
        max_score += 3

        if abs(found_age - reported_age) <= 1:
            score += 3
            reasons.append("Similar reported age")
        elif abs(found_age - reported_age) <= 2:
            score += 1
            reasons.append("Age is within two years")

    # Last-seen area
    found_area = found_child.get("area")
    reported_area = missing_report.get("area")

    if found_area and reported_area:
        max_score += 3

        if found_area.strip().casefold() == reported_area.strip().casefold():
            score += 3
            reasons.append("Same reported area")

    # Reported clothing colour; weak evidence only
    found_clothing = found_child.get("clothing_color")
    reported_clothing = missing_report.get("clothing_color")

    if found_clothing and reported_clothing:
        max_score += 1

        if found_clothing.strip().casefold() == reported_clothing.strip().casefold():
            score += 1
            reasons.append("Clothing colour matches")

    # Calculate a screening score only when enough data is comparable
    if max_score == 0:
        return {
            "report_id": missing_report["report_id"],
            "score": None,
            "reasons": [],
            "status": "Insufficient information"
        }

    percentage = round((score / max_score) * 100)

    return {
        "report_id": missing_report["report_id"],
        "score": percentage,
        "reasons": reasons,
        "status": "Requires human verification"
    }


def find_candidates(found_child, missing_reports):
    candidates = []

    for report in missing_reports:
        result = compare_cases(found_child, report)

        if result["score"] is not None:
            candidates.append(result)

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return candidates


if __name__ == "__main__":
    found_child = {
        "age": 7,
        "area": "Jaipur Railway Station",
        "clothing_color": "blue"
    }

    missing_reports = [
        {
            "report_id": "DEMO-001",
            "age": 7,
            "area": "Jaipur Railway Station",
            "clothing_color": "blue"
        },
        {
            "report_id": "DEMO-002",
            "age": 8,
            "area": "Ajmer Railway Station",
            "clothing_color": "red"
        },
        {
            "report_id": "DEMO-003",
            "age": 7,
            "area": "Jaipur Railway Station",
            "clothing_color": "red"
        }
    ]

    for candidate in find_candidates(found_child, missing_reports):
        print(candidate)

import re


def text_similarity(value1, value2):
    if not value1 or not value2:
        return 0

    words1 = set(re.findall(r"\b\w+\b", str(value1).lower()))
    words2 = set(re.findall(r"\b\w+\b", str(value2).lower()))

    if not words1 or not words2:
        return 0

    common_words = words1.intersection(words2)
    all_words = words1.union(words2)

    return len(common_words) / len(all_words)


def compare_reports(missing_report, found_report):
    weights = {
        "age": 25,
        "clothing": 30,
        "location": 25,
        "time": 15,
        "description": 5
    }

    score = 0
    total_weight = 0
    comparable_fields = []
    reasons = []

    for field, weight in weights.items():
        missing_value = missing_report.get(field)
        found_value = found_report.get(field)

        if missing_value is None or found_value is None:
            continue

        if str(missing_value).strip() == "":
            continue

        if str(found_value).strip() == "":
            continue

        if field == "age":
            try:
                age1 = int(missing_value)
                age2 = int(found_value)
                similarity = max(0, 1 - abs(age1 - age2) / 5)
            except (ValueError, TypeError):
                similarity = text_similarity(missing_value, found_value)
        else:
            similarity = text_similarity(missing_value, found_value)

        score += similarity * weight
        total_weight += weight
        comparable_fields.append(field)

        if similarity >= 0.5:
            reasons.append(field + ": details are similar")
        else:
            reasons.append(field + ": details differ")

    if total_weight > 0:
        final_score = round((score / total_weight) * 100)
    else:
        final_score = 0

    if len(comparable_fields) < 2:
        status = "INSUFFICIENT INFORMATION — HUMAN REVIEW REQUIRED"
    elif final_score >= 60:
        status = "POTENTIAL MATCH — HUMAN VERIFICATION REQUIRED"
    else:
        status = "LOWER-SCORING CANDIDATE — HUMAN REVIEW REQUIRED"

    return {
        "missing_case_id": missing_report.get("case_id"),
        "found_case_id": found_report.get("case_id"),
        "score": final_score,
        "comparable_fields": comparable_fields,
        "reasons": reasons,
        "status": status,
        "identity_confirmed": False
    }


def find_potential_matches(missing_report, found_reports, minimum_score=35):
    matches = []

    for found_report in found_reports:
        if found_report.get("report_type") != "found":
            continue

        result = compare_reports(missing_report, found_report)

        if (
            len(result["comparable_fields"]) >= 2
            and result["score"] >= minimum_score
        ):
            matches.append(result)

    matches.sort(key=lambda item: item["score"], reverse=True)

    return matches


if __name__ == "__main__":
    missing = {
        "case_id": "DEMO-MISS-001",
        "report_type": "missing",
        "age": 8,
        "clothing": "red shirt and blue jeans",
        "location": "near city park",
        "time": "around 5 PM",
        "description": "child carrying a small school bag"
    }

    found = [
        {
            "case_id": "DEMO-FOUND-001",
            "report_type": "found",
            "age": 8,
            "clothing": "red shirt and blue jeans",
            "location": "near city park",
            "time": "around 5 PM",
            "description": "child carrying a small school bag"
        },
        {
            "case_id": "DEMO-FOUND-002",
            "report_type": "found",
            "age": 12,
            "clothing": "black jacket",
            "location": "near railway station",
            "time": "around 9 PM",
            "description": "child carrying a backpack"
        }
    ]

    matches = find_potential_matches(missing, found)

    print("POTENTIAL MATCHES — FICTIONAL DATA ONLY")

    for match in matches:
        print(match)
