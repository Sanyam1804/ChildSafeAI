
from tools import (
    parse_case,
    find_missing_fields,
    create_draft_referral
)

report = (
    "A child was reported alone near platform 2 at Jaipur railway station "
    "around 10 AM. The reporter is a station staff member. "
    "The child's age is unknown."
)

case_data = parse_case(report)

print("PARSED CASE:")
print(case_data)

missing_fields = find_missing_fields(case_data)

print("\nMISSING REQUIRED FIELDS:")
print(missing_fields)

guidance_result = {
    "passage": "Follow the approved human-review procedure.",
    "source_title": "Synthetic demo guidance",
    "source_url": None
}

draft = create_draft_referral(
    case_data,
    guidance_result,
    missing_fields
)

print("\nREFERRAL DRAFT:")
print(draft)