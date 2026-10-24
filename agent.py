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
from uagents import Agent, Context, Protocol

from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from tools import (
    parse_case,
    find_missing_fields,
    create_draft_referral,
)

from matching import (
    compare_reports,
    find_potential_matches,
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
    matches = []

    if case_data["report_type"] == "missing":
        return find_potential_matches(
            case_data,
            saved_cases,
            minimum_score=35,
        )

    # A new found report is compared with saved missing reports.
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


@protocol.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(acknowledged_msg_id=msg.msg_id),
    )

    report_text = ""

    for item in msg.content:
        if isinstance(item, TextContent):
            report_text += item.text + "\n"

    if not report_text.strip():
        response = "Please provide a fictional demo report."

    else:
        try:
            case_data = parse_case(report_text)

            if not case_data["report_type"]:
                response = (
                    "Please specify the report type as either "
                    "'Type: missing' or 'Type: found'.\n\n"
                    "Use fictional demo details only."
                )

            else:
                missing_fields = find_missing_fields(case_data)

                guidance_result = {
                    "passage": None,
                    "source_title": (
                        "Unavailable — demo guidance not connected"
                    ),
                    "source_url": None,
                }

                draft = create_draft_referral(
                    case_data,
                    guidance_result,
                    missing_fields,
                )

                saved_cases = load_cases()

                # Compare against previous reports before saving this one.
                matches = get_matches(case_data, saved_cases)

                # Save this fictional report for later comparisons.
                saved_cases.append(case_data)
                save_cases(saved_cases)

                result = {
                    "draft": draft,
                    "potential_matches": matches,
                    "reports_in_demo_store": len(saved_cases),
                    "safety_note": (
                        "Fictional demo only. A score is not proof "
                        "of identity. Human verification is required. "
                        "No referral has been sent."
                    ),
                }

                response = (
                    "CHILDSAFE AI — DEMO RESULT\n\n"
                    + json.dumps(
                        result,
                        indent=2,
                        ensure_ascii=False,
                    )
                )

        except Exception:
            ctx.logger.exception("Failed to process report")
            response = (
                "The report could not be processed. "
                "Please try again with a fictional demo report."
            )

    await ctx.send(
        sender,
        ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[
                TextContent(type="text", text=response),
                EndSessionContent(type="end-session"),
            ],
        ),
    )


@protocol.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info("Received acknowledgement from %s", sender)


agent.include(protocol, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
