
import asyncio

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import os
import json
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from matching import (
    find_candidates,
    compare_reports,
    find_potential_matches,
)
from reports import MISSING_REPORTS
from tools import (
    parse_case,
    find_missing_fields,
    create_draft_referral,
)

load_dotenv()

seed = os.getenv("AGENT_SEED")

if not seed:
    raise RuntimeError("AGENT_SEED is missing from .env")

agent = Agent(
    name="childsafe-ai",
    seed=seed,
    port=8001,
    mailbox=True,
    publish_agent_details=True,
)

protocol = Protocol(spec=chat_protocol_spec)

STORE_FILE = "demo_cases.json"


def ask_asi1(message):
    api_key = os.getenv("ASI1_API_KEY")

    if not api_key:
        return "ASI1_API_KEY is missing from .env."

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.asi1.ai/v1",
    )

    response = client.chat.completions.create(
        model="asi1",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are ChildSafe AI, an assistant for organizing "
                    "lost-child and separated-family reports. "
                    "Distinguish reported information from verified "
                    "information. Never invent case details or claim "
                    "a match, contact, or reunification is verified "
                    "unless it actually is. Protect children's personal "
                    "information. Never disclose a child's precise "
                    "location to an unverified person. Matching "
                    "suggestions require independent human verification. "
                    "If a child may be in immediate danger, recommend "
                    "contacting local emergency services or authorized "
                    "child-protection personnel. "
                    "Use these headings: CASE SUMMARY, KNOWN "
                    "INFORMATION, MISSING INFORMATION, POSSIBLE NEXT "
                    "STEPS, VERIFICATION REQUIREMENTS, HUMAN REVIEW."
                ),
            },
            {"role": "user", "content": message},
        ],
    )

    return (
        response.choices[0].message.content
        or "No response generated."
    )


def process_match(raw_data):
    if not raw_data:
        return (
            'Please provide JSON after /match. Example:\n'
            '/match {"age": 7, "area": "Jaipur Railway Station", '
            '"clothing_color": "blue"}'
        )

    try:
        found_child = json.loads(raw_data)
    except json.JSONDecodeError:
        return (
            'Invalid JSON. Example:\n'
            '/match {"age": 7, "area": "Jaipur Railway Station", '
            '"clothing_color": "blue"}'
        )

    if not isinstance(found_child, dict):
        return "Invalid input. Provide a JSON object."

    allowed_fields = {"age", "area", "clothing_color"}
    unknown_fields = set(found_child) - allowed_fields

    if unknown_fields:
        return (
            "Unsupported fields: "
            + ", ".join(sorted(unknown_fields))
            + ". Allowed fields: age, area, clothing_color."
        )

    age = found_child.get("age")

    if age is not None and (
        isinstance(age, bool)
        or not isinstance(age, int)
        or age < 0
        or age > 120
    ):
        return "Age must be a valid non-negative integer."

    for field in ("area", "clothing_color"):
        value = found_child.get(field)

        if value is not None and not isinstance(value, str):
            return f"{field} must be text."

        if isinstance(value, str):
            value = value.strip()
            found_child[field] = value or None

    candidates = find_candidates(found_child, MISSING_REPORTS)

    if not candidates:
        return (
            "Insufficient comparable information to rank candidates. "
            "No match has been established."
        )

    lines = [
        "DEMO MATCHING RESULTS",
        "",
        "These are fictional demonstration records.",
        "Screening scores are heuristic comparisons, not probabilities "
        "of identity or proof of a family relationship.",
        "",
    ]

    for candidate in candidates:
        lines.extend([
            f"Report ID: {candidate['report_id']}",
            f"Screening score: {candidate['score']}%",
            "Comparison reasons: "
            + (
                ", ".join(candidate["reasons"])
                if candidate["reasons"]
                else "No matching fields"
            ),
            "Status: Requires human verification",
            "",
        ])

    lines.extend([
        "HUMAN REVIEW REQUIRED",
        "No identity or guardianship has been verified.",
        "Do not disclose a child's location or authorize reunification "
        "based on these scores.",
        "Authorized personnel must independently verify identity "
        "and guardianship.",
    ])

    return "\n".join(lines)


def load_cases():
    if not os.path.exists(STORE_FILE):
        return []

    try:
        with open(STORE_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_cases(cases):
    with open(STORE_FILE, "w", encoding="utf-8") as file:
        json.dump(cases, file, indent=2, ensure_ascii=False)


def get_matches(case_data, saved_cases):
    if case_data.get("report_type") == "missing":
        return find_potential_matches(
            case_data,
            saved_cases,
            minimum_score=35,
        )

    matches = []

    if case_data.get("report_type") != "found":
        return matches

    for old_case in saved_cases:
        if old_case.get("report_type") != "missing":
            continue

        result = compare_reports(old_case, case_data)

        if (
            len(result["comparable_fields"]) >= 2
            and result["score"] >= 35
        ):
            matches.append(result)

    matches.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return matches


def process_report(report_text):
    if not report_text.strip():
        return (
            "Please provide a fictional demo report and specify "
            "'Type: missing' or 'Type: found'."
        )

    try:
        case_data = parse_case(report_text)

        if not case_data.get("report_type"):
            return (
                "Please specify the report type as either "
                "'Type: missing' or 'Type: found'.\n\n"
                "Use fictional demo details only."
            )

        if case_data["report_type"] not in ("missing", "found"):
            return (
                "Invalid report type. Use 'Type: missing' "
                "or 'Type: found'."
            )

        missing_fields = find_missing_fields(case_data)

        guidance_result = {
            "passage": None,
            "source_title": "Unavailable — demo guidance not connected",
            "source_url": None,
        }

        draft = create_draft_referral(
            case_data,
            guidance_result,
            missing_fields,
        )

        saved_cases = load_cases()
        matches = get_matches(case_data, saved_cases)

        saved_cases.append(case_data)
        save_cases(saved_cases)

        result = {
            "draft": draft,
            "potential_matches": matches,
            "reports_in_demo_store": len(saved_cases),
            "safety_note": (
                "Fictional demo only. A score is not proof of identity. "
                "Human verification is required. No referral has been sent."
            ),
        }

        return (
            "CHILDSAFE AI — DEMO RESULT\n\n"
            + json.dumps(result, indent=2, ensure_ascii=False)
        )

    except Exception:
        raise


def process_message(message):
    cleaned_message = message.strip()

    if (
        cleaned_message.startswith("@")
        and " " in cleaned_message
    ):
        first_part, remaining = cleaned_message.split(maxsplit=1)

        if first_part.startswith("@agent"):
            cleaned_message = remaining.strip()

    if not cleaned_message:
        return "Please send a message or a fictional demo report."

    first_word = cleaned_message.split(maxsplit=1)[0].casefold()

    if first_word == "/match":
        raw_data = cleaned_message[len("/match"):].strip()
        return process_match(raw_data)

    if first_word == "/report":
        report_text = cleaned_message[len("/report"):].strip()
        return process_report(report_text)

    lowered_message = cleaned_message.casefold()

    report_indicators = (
        "type: missing",
        "type: found",
        "last seen:",
        "missing child",
        "found child",
        "report type:",
    )

    if any(indicator in lowered_message for indicator in report_indicators):
        return process_report(cleaned_message)

    return ask_asi1(cleaned_message)


@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc),
            acknowledged_msg_id=msg.msg_id,
        ),
    )

    message = "\n".join(
        item.text
        for item in msg.content
        if isinstance(item, TextContent)
    ).strip()

    ctx.logger.info("Incoming chat message: %s", message[:150])

    try:
        answer = process_message(message)
    except Exception:
        ctx.logger.exception("Message processing failed")
        answer = (
            "The request could not be processed. "
            "Check the agent logs and try again with fictional demo details."
        )

    await ctx.send(
        sender,
        ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[
                TextContent(type="text", text=answer),
                EndSessionContent(type="end-session"),
            ],
        ),
    )


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(
    ctx: Context,
    sender: str,
    msg: ChatAcknowledgement,
):
    ctx.logger.info("Received acknowledgement from %s", sender)


agent.include(protocol, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
