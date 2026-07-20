"""
Nigeria Country Package - Validation

Country-specific validation for phone numbers, CAC registration
numbers, the National Identification Number (NIN), Bank Verification
Number (BVN) and TIN. Every `validate_*` returns
(is_valid, normalized_or_none).
"""

import re

PHONE_PATTERN = re.compile(r"^(?:\+234|234|0)([789]\d{9})$")
TIN_PATTERN = re.compile(r"^\d{8}-\d{4}$")
NIN_PATTERN = re.compile(r"^\d{11}$")
BVN_PATTERN = re.compile(r"^\d{11}$")
# CAC registration numbers: RC (companies) or BN (business names) followed by digits.
CAC_PATTERN = re.compile(r"^(RC|BN)\d{4,8}$", re.IGNORECASE)


def validate_phone(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    match = PHONE_PATTERN.match(value.strip().replace(" ", ""))
    if not match:
        return False, None
    return True, "234" + match.group(1)


def validate_tin(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip()
    return (True, cleaned) if TIN_PATTERN.match(cleaned) else (False, None)


def validate_nin(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip()
    return (True, cleaned) if NIN_PATTERN.match(cleaned) else (False, None)


def validate_bvn(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip()
    return (True, cleaned) if BVN_PATTERN.match(cleaned) else (False, None)


def validate_cac_registration_number(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip().upper()
    return (True, cleaned) if CAC_PATTERN.match(cleaned) else (False, None)
