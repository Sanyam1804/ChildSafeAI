
# import json
# from datetime import datetime, timedelta
# from pathlib import Path

# DATA_FILE = Path(__file__).parent / "data" / "cases.json"

# VALID_STATUSES = {
#     "not_sent",
#     "sent",
#     "acknowledged",
#     "escalated"
# }


# def load_cases():
#     DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

#     if not DATA_FILE.exists():
#         return {}

#     try:
#         with open(DATA_FILE, "r", encoding="utf-8") as file:
#             data = json.load(file)

#         return data if isinstance(data, dict) else {}

#     except (json.JSONDecodeError, OSError):
#         raise RuntimeError(
#             "cases.json could not be read. Check the file before continuing."
#         )


# cases = load_cases()


# def save_cases():
#     DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

#     with open(DATA_FILE, "w", encoding="utf-8") as file:
#         json.dump(cases, file, indent=4)


# def create_case(case_id):
#     if case_id in cases:
#         return cases[case_id]

#     case = {
#         "case_id": case_id,
#         "actions": [],
#         "handoff": {
#             "status": "not_sent",
#             "acknowledged": False
#         }
#     }

#     cases[case_id] = case
#     save_cases()
#     return case


# def log_action(case_id, action):
#     case = cases.get(case_id)

#     if case is None:
#         return {"error": "Case not found"}

#     case["actions"].append({
#         "action": action,
#         "timestamp": datetime.now().isoformat()
#     })

#     save_cases()
#     return case


# def get_case(case_id):
#     return cases.get(case_id)


# def update_handoff(case_id, status):
#     case = cases.get(case_id)

#     if case is None:
#         return {"error": "Case not found"}

#     if status not in VALID_STATUSES:
#         return {"error": "Invalid handoff status"}

#     handoff = case["handoff"]
#     current_status = handoff["status"]

#     if status == "sent":
#         if current_status != "not_sent":
#             return {"error": "Case cannot be sent from current status"}

#         now = datetime.now()
#         handoff["status"] = "sent"
#         handoff["sent_at"] = now.isoformat()
#         handoff["deadline"] = (
#             now + timedelta(minutes=30)
#         ).isoformat()
#         handoff["acknowledged"] = False

#     elif status == "acknowledged":
#         return acknowledge_handoff(case_id)

#     elif status == "escalated":
#         return {
#             "error": "Use check_overdue_handoff to trigger escalation"
#         }

#     elif status == "not_sent":
#         if current_status != "not_sent":
#             return {"error": "Cannot reset an active handoff"}

#     log_action(case_id, f"Referral status updated to {status}")
#     save_cases()
#     return handoff


# def acknowledge_handoff(case_id):
#     case = cases.get(case_id)

#     if case is None:
#         return {"error": "Case not found"}

#     handoff = case["handoff"]

#     if handoff["status"] != "sent":
#         return {"error": "No pending referral to acknowledge"}

#     handoff["acknowledged"] = True
#     handoff["status"] = "acknowledged"
#     handoff["acknowledged_at"] = datetime.now().isoformat()

#     log_action(case_id, "Referral acknowledgement received")
#     save_cases()

#     return {
#         "case_id": case_id,
#         "status": "acknowledged",
#         "message": "Referral acknowledgement recorded"
#     }


# def check_overdue_handoff(case_id):
#     case = cases.get(case_id)

#     if case is None:
#         return {"error": "Case not found"}

#     handoff = case["handoff"]

#     if handoff["status"] == "acknowledged":
#         return {
#             "case_id": case_id,
#             "status": "acknowledged",
#             "message": "No escalation required"
#         }

#     if handoff["status"] == "escalated":
#         return {
#             "case_id": case_id,
#             "status": "escalated",
#             "message": "Escalation already recorded"
#         }

#     if handoff["status"] != "sent":
#         return {
#             "case_id": case_id,
#             "status": handoff["status"],
#             "message": "No escalation required"
#         }

#     deadline = datetime.fromisoformat(handoff["deadline"])

#     if datetime.now() >= deadline:
#         handoff["status"] = "escalated"

#         log_action(
#             case_id,
#             "Escalation: referral acknowledgement overdue"
#         )

#         save_cases()

#         return {
#             "case_id": case_id,
#             "status": "escalated",
#             "message": "Referral acknowledgement overdue"
#         }

#     return {
#         "case_id": case_id,
#         "status": "sent",
#         "message": "Waiting for acknowledgement"
#     }

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "cases.json"

VALID_STATUSES = {
    "not_sent",
    "sent",
    "acknowledged",
    "escalated"
}


def now_iso():
    return datetime.now().astimezone().isoformat()


def validate_case_id(case_id):
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("Case ID must be a non-empty string")


def load_cases():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not DATA_FILE.exists():
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(
            "cases.json could not be read. Check the file before continuing."
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError("Invalid cases.json structure: expected an object")

    for case_id, case in data.items():
        if not isinstance(case_id, str) or not isinstance(case, dict):
            raise RuntimeError("Invalid case record in cases.json")

        if case.get("case_id") != case_id:
            raise RuntimeError(f"Invalid case ID in record: {case_id}")

        if not isinstance(case.get("actions"), list):
            raise RuntimeError(f"Invalid actions list for case: {case_id}")

        handoff = case.get("handoff")
        if not isinstance(handoff, dict):
            raise RuntimeError(f"Invalid handoff record for case: {case_id}")

        if handoff.get("status") not in VALID_STATUSES:
            raise RuntimeError(f"Invalid handoff status for case: {case_id}")

        if not isinstance(handoff.get("acknowledged"), bool):
            raise RuntimeError(f"Invalid acknowledgement flag for case: {case_id}")

    return data


cases = load_cases()


def save_cases():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=DATA_FILE.parent,
            delete=False
        ) as file:
            temp_path = Path(file.name)
            json.dump(cases, file, indent=4)
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_path, DATA_FILE)

    except OSError as exc:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

        raise RuntimeError("Could not save case data") from exc


def _append_action(case, action):
    case["actions"].append({
        "action": action,
        "timestamp": now_iso()
    })


def create_case(case_id):
    validate_case_id(case_id)
    case_id = case_id.strip()

    if case_id in cases:
        return cases[case_id]

    case = {
        "case_id": case_id,
        "actions": [],
        "handoff": {
            "status": "not_sent",
            "acknowledged": False
        }
    }

    cases[case_id] = case

    try:
        save_cases()
    except RuntimeError:
        del cases[case_id]
        raise

    return case


def log_action(case_id, action):
    validate_case_id(case_id)

    if not isinstance(action, str) or not action.strip():
        raise ValueError("Action must be a non-empty string")

    case = cases.get(case_id)

    if case is None:
        return {"error": "Case not found"}

    _append_action(case, action.strip())
    save_cases()
    return case


def get_case(case_id):
    return cases.get(case_id)


def update_handoff(case_id, status):
    case = cases.get(case_id)

    if case is None:
        return {"error": "Case not found"}

    if status not in VALID_STATUSES:
        return {"error": "Invalid handoff status"}

    handoff = case["handoff"]
    current_status = handoff["status"]

    if status == "acknowledged":
        return acknowledge_handoff(case_id)

    if status == "escalated":
        return {
            "error": "Use check_overdue_handoff to trigger escalation"
        }

    if status == "sent":
        if current_status != "not_sent":
            return {
                "error": "Case cannot be sent from current status"
            }

        now = datetime.now().astimezone()

        handoff["status"] = "sent"
        handoff["sent_at"] = now.isoformat()
        handoff["deadline"] = (
            now + timedelta(minutes=30)
        ).isoformat()
        handoff["acknowledged"] = False

        _append_action(case, "Referral handoff recorded")

    elif status == "not_sent":
        if current_status != "not_sent":
            return {"error": "Cannot reset an active handoff"}

        return handoff

    save_cases()
    return handoff


def acknowledge_handoff(case_id):
    case = cases.get(case_id)

    if case is None:
        return {"error": "Case not found"}

    handoff = case["handoff"]

    if handoff["status"] != "sent":
        return {"error": "No pending referral to acknowledge"}

    handoff["acknowledged"] = True
    handoff["status"] = "acknowledged"
    handoff["acknowledged_at"] = now_iso()

    _append_action(case, "Referral acknowledgement received")
    save_cases()

    return {
        "case_id": case_id,
        "status": "acknowledged",
        "message": "Referral acknowledgement recorded"
    }


def check_overdue_handoff(case_id):
    case = cases.get(case_id)

    if case is None:
        return {"error": "Case not found"}

    handoff = case["handoff"]
    status = handoff["status"]

    if status == "acknowledged":
        return {
            "case_id": case_id,
            "status": status,
            "message": "No escalation required"
        }

    if status == "escalated":
        return {
            "case_id": case_id,
            "status": status,
            "message": "Escalation already recorded"
        }

    if status != "sent":
        return {
            "case_id": case_id,
            "status": status,
            "message": "No escalation required"
        }

    try:
        deadline = datetime.fromisoformat(handoff["deadline"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(
            "Invalid or missing referral deadline"
        ) from exc

    current_time = datetime.now().astimezone()

    # Handle older timestamps that have no timezone information.
    if deadline.tzinfo is None:
        current_time = datetime.now()

    if current_time >= deadline:
        handoff["status"] = "escalated"

        _append_action(
            case,
            "Escalation: referral acknowledgement overdue"
        )

        save_cases()

        return {
            "case_id": case_id,
            "status": "escalated",
            "message": "Referral acknowledgement overdue"
        }

    return {
        "case_id": case_id,
        "status": "sent",
        "message": "Waiting for acknowledgement"
    }
