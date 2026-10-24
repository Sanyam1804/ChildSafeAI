
from datetime import datetime, timedelta

from case_store import (
    cases,
    save_cases,
    create_case,
    log_action,
    get_case,
    update_handoff,
    check_overdue_handoff,
    acknowledge_handoff
)


# Use separate test IDs to avoid overwriting existing cases.


# Test 1: Create a case and save an action

case_id = "TEST_P3_001"

case = create_case(case_id)
initial_actions = len(case["actions"])

log_action(case_id, "Test action recorded")

updated_case = get_case(case_id)

assert updated_case is not None
assert len(updated_case["actions"]) == initial_actions + 1

print("TEST 1 PASSED: Case creation and action logging")



# Test 2: Referral sent, acknowledgement still pending

from uuid import uuid4

case_id = f"TEST_PENDING_{uuid4().hex[:8]}"

create_case(case_id)

result = update_handoff(case_id, "sent")

assert result.get("status") == "sent", result

result = check_overdue_handoff(case_id)

assert result.get("status") == "sent", result
assert result["message"] == "Waiting for acknowledgement"

print("TEST 2 PASSED: Pending acknowledgement")



# Test 3: Acknowledgement received

from uuid import uuid4

case_id = f"TEST_ACK_{uuid4().hex[:8]}"

create_case(case_id)

result = update_handoff(case_id, "sent")
assert result.get("status") == "sent", result

result = acknowledge_handoff(case_id)
assert result.get("status") == "acknowledged", result

result = check_overdue_handoff(case_id)
assert result.get("status") == "acknowledged", result

print("TEST 3 PASSED: Acknowledgement prevents escalation")


# Test 4: Overdue referral escalates
create_case("TEST_P3_004")
update_handoff("TEST_P3_004", "sent")

case = get_case("TEST_P3_004")
case["handoff"]["deadline"] = (
    datetime.now() - timedelta(minutes=1)
).isoformat()

save_cases()

result = check_overdue_handoff("TEST_P3_004")

assert result["status"] == "escalated"

print("TEST 4 PASSED: Overdue referral escalated")


# Test 5: Repeated checks do not duplicate escalation actions
case = get_case("TEST_P3_004")

before = sum(
    1 for action in case["actions"]
    if action["action"] ==
    "Escalation: referral acknowledgement overdue"
)

check_overdue_handoff("TEST_P3_004")

after = sum(
    1 for action in case["actions"]
    if action["action"] ==
    "Escalation: referral acknowledgement overdue"
)

assert before == after

print("TEST 5 PASSED: No duplicate escalation")


# Test 6: Invalid status is rejected
create_case("TEST_P3_005")

result = update_handoff("TEST_P3_005", "unknown_status")

assert "error" in result

print("TEST 6 PASSED: Invalid status rejected")


# Test 7: Case data exists in persistent storage
assert "TEST_P3_004" in cases

print("TEST 7 PASSED: Case exists in persistent store")

print("\nAll P3 tests passed successfully.")
