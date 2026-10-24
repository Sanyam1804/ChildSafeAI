
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

from matching import find_candidates
from reports import MISSING_REPORTS


load_dotenv()

client = OpenAI(
    api_key=os.environ["ASI1_API_KEY"],
    base_url="https://api.asi1.ai/v1",
)

agent = Agent(
    name="ChildSafe AI",
    seed=os.environ["AGENT_SEED"],
    port=8001,
    mailbox=True,
    publish_agent_details=True,
)

protocol = Protocol(spec=chat_protocol_spec)


def ask_asi1(message):
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



def process_message(message):
    print("ORIGINAL MESSAGE:", repr(message))

    cleaned_message = message.strip()

    # Agentverse may prepend the recipient's agent address.
    # Remove that prefix before checking the command.
    if cleaned_message.startswith("@") and " " in cleaned_message:
        first_part, remaining = cleaned_message.split(maxsplit=1)

        if first_part.startswith("@agent"):
            cleaned_message = remaining.strip()

    print("MESSAGE AFTER PREFIX REMOVAL:", repr(cleaned_message))

    # Route /match requests to the matching engine.
    first_word = (
        cleaned_message.split(maxsplit=1)[0].casefold()
        if cleaned_message
        else ""
    )

    if first_word == "/match":
        print("ROUTING TO MATCHING ENGINE")
        raw_data = cleaned_message[len("/match"):].strip()
        return process_match(raw_data)

    print("ROUTING TO ASI:One")
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

    ctx.logger.info(f"Incoming chat message: {message[:150]}")

    try:
        ctx.logger.info("ROUTING TEST: calling process_message")

        if message:
            answer = process_message(message)
        else:
            answer = (
                "Please send a message or a fictional case report."
            )

        print("FINAL ANSWER BEING SENT TO AGENTVERSE:")
        print(answer)

    except Exception:
        ctx.logger.exception("Message processing failed")
        answer = (
            "I could not process that request. "
            "Please check the local agent logs and try again."
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
    pass


agent.include(protocol, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
