"""
Uganda Country Package - Validation

Country-specific validation for phone numbers, business registration
numbers, the National ID Number (NIN), TIN and postal codes. Every
`validate_*` returns (is_valid, normalized_or_none).
"""

import re

PHONE_PATTERN = re.compile(r"^(?:\+256|256|0)(7\d{8}|3\d{8})$")
TIN_PATTERN = re.compile(r"^\d{10}$")
# NIN format: one letter, 13 digits/letters, one letter, e.g. CM12345678ABCD
NIN_PATTERN = re.compile(r"^[A-Z]{2}\d{9}[A-Z0-9]{4}$")
BUSINESS_REGISTRATION_PATTERN = re.compile(r"^80\d{9}$")  # URSB certificate number shape


def validate_phone(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    match = PHONE_PATTERN.match(value.strip().replace(" ", ""))
    if not match:
        return False, None
    return True, "256" + match.group(1)


def validate_tin(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip()
    return (True, cleaned) if TIN_PATTERN.match(cleaned) else (False, None)


def validate_nin(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip().upper()
    return (True, cleaned) if NIN_PATTERN.match(cleaned) else (False, None)


def validate_business_registration_number(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip()
    return (True, cleaned) if BUSINESS_REGISTRATION_PATTERN.match(cleaned) else (False, None)
