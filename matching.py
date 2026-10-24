
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
