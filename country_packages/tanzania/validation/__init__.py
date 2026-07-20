"""
Tanzania Country Package - Validation

Country-specific validation for phone numbers, business registration
numbers, the NIDA National ID and TIN. Every `validate_*` returns
(is_valid, normalized_or_none).
"""

import re

PHONE_PATTERN = re.compile(r"^(?:\+255|255|0)(6\d{8}|7\d{8})$")
TIN_PATTERN = re.compile(r"^\d{9}$")
# NIDA National ID: 20 digits, e.g. 19900101-12345-00001-23
NIDA_PATTERN = re.compile(r"^\d{8}-\d{5}-\d{5}-\d{2}$")
BUSINESS_REGISTRATION_PATTERN = re.compile(r"^\d{6,9}$")  # BRELA certificate number shape


def validate_phone(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    match = PHONE_PATTERN.match(value.strip().replace(" ", ""))
    if not match:
        return False, None
    return True, "255" + match.group(1)


def validate_tin(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip()
    return (True, cleaned) if TIN_PATTERN.match(cleaned) else (False, None)


def validate_nida(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip()
    return (True, cleaned) if NIDA_PATTERN.match(cleaned) else (False, None)


def validate_business_registration_number(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip()
    return (True, cleaned) if BUSINESS_REGISTRATION_PATTERN.match(cleaned) else (False, None)
