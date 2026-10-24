
from tools import retrieve_protocol

from case_store import (
    create_case,
    log_action,
    get_case,
    update_handoff,
    check_overdue_handoff,
    acknowledge_handoff,
)


def search_procedures(query):
    """Retrieve relevant safeguarding procedures."""
    results = retrieve_protocol(query)

    return {
        "success": True,
        "count": len(results),
        "results": results,
    }


def open_case(case_id):
    """Create or retrieve a case."""
    if not case_id or not case_id.strip():
        return {"error": "Case ID is required"}

    case = get_case(case_id)

    if case is None:
        case = create_case(case_id)
        return {"success": True, "case": case, "created": True}

    return {"success": True, "case": case, "created": False}


def record_case_action(case_id, action):
    """Record an action against an existing case."""
    if not isinstance(action, str) or not action.strip():
        return {"error": "Action is required"}

    result = log_action(case_id, action)

    if "error" in result:
        return result

    return {"success": True, "case": result}


def simulate_referral(case_id, human_reviewed=False):
    """
    Simulate a referral handoff.
    This does not contact any real authority.
    """
    if human_reviewed is not True:
        return {
            "success": False,
            "message": "Authorised human review is required."
        }

    result = update_handoff(case_id, "sent")

    if "error" in result:
        return {"success": False, "result": result}

    return {
        "success": True,
        "message": "Simulated referral handoff recorded.",
        "handoff": result,
    }


def record_acknowledgement(case_id):
    """Record acknowledgement of a simulated referral."""
    result = acknowledge_handoff(case_id)

    if "error" in result:
        return {"success": False, "result": result}

    return {"success": True, "result": result}


def check_referral_status(case_id):
    """Check whether a referral needs escalation."""
    result = check_overdue_handoff(case_id)

    if "error" in result:
        return {"success": False, "result": result}

    return {"success": True, "result": result}
