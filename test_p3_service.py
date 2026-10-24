
from uuid import uuid4

from p3_service import (
    search_procedures,
    open_case,
    record_case_action,
    simulate_referral,
    record_acknowledgement,
    check_referral_status,
)


case_id = f"SERVICE_{uuid4().hex[:8]}"

# 1. Search procedures
result = search_procedures("child assistance railway station")
assert result["success"]
assert result["count"] > 0
print("SERVICE TEST 1 PASSED: Procedure retrieval")

# 2. Open a new case
result = open_case(case_id)
assert result["success"]
assert result["created"]
print("SERVICE TEST 2 PASSED: Case creation")

# 3. Record an action
result = record_case_action(case_id, "Demo action recorded")
assert result["success"]
print("SERVICE TEST 3 PASSED: Action logging")

# 4. Verify human review gate
result = simulate_referral(case_id)
assert result["success"] is False
print("SERVICE TEST 4 PASSED: Review gate")

# 5. Simulate an approved handoff
result = simulate_referral(case_id, human_reviewed=True)
assert result["success"], result
print("SERVICE TEST 5 PASSED: Simulated referral")

# 6. Record acknowledgement
result = record_acknowledgement(case_id)
assert result["success"], result
print("SERVICE TEST 6 PASSED: Acknowledgement")

# 7. Check status
result = check_referral_status(case_id)
assert result["success"], result
assert result["result"]["status"] == "acknowledged"
print("SERVICE TEST 7 PASSED: Referral status")

print("\nAll P3 service tests passed.")
