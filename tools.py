
import json
import re
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
