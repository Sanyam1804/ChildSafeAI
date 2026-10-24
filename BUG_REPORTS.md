
# ChildSafeAI — Bug & Issue Report

## BUG-001: Fixed Case ID Reused Across Reports

**Status:** Open — investigation required  
**Severity:** Medium  
**Area:** Report Processing / Case Management  
**File:** `tools.py`  
**Function:** `parse_case()`

### Observation
The current implementation returns `DEMO-001` as the case ID for every parsed report.

### Reproduction Evidence
Two separate synthetic reports were passed to `parse_case()`.

Observed output:
- Case 1 ID: `DEMO-001`
- Case 2 ID: `DEMO-001`
- Same ID: `True`

**Conclusion:** The fixed case ID behaviour is confirmed. The impact on downstream storage and audit records still needs integration testing.

### Expected Behaviour
Each distinct case should have a stable, unique case ID so that reports and their audit records are not accidentally mixed.

### Actual Behaviour
Separate calls to `parse_case()` currently return the same case ID.

### Potential Impact
If multiple cases are processed, records could become difficult to distinguish or could be associated with the wrong case.

### Evidence
The case ID is hard-coded in the return dictionary in `parse_case()`.

### Recommended Next Step
Coordinate with the report-processing owner (P2) to agree on a safe, consistent case-ID strategy before changing the implementation.

### Verification Required
- [ ] Confirm the issue with two distinct synthetic reports.
- [ ] Agree on expected case-ID behaviour with P2 and the workflow owner.
- [ ] Verify distinct cases can be tracked consistently.
- [ ] Verify retries do not create unintended duplicate records.
