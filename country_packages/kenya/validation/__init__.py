"""
Kenya Country Package - Validation

Country-specific validation for phone numbers, business registration
numbers, national IDs, tax PINs and postal codes. Every `validate_*`
returns (is_valid, normalized_or_none) so a caller can both check and
use the cleaned-up value in one call.
"""

import re

PHONE_PATTERN = re.compile(r"^(?:\+254|254|0)(7\d{8}|1\d{8})$")
KRA_PIN_PATTERN = re.compile(r"^[A-Z]\d{9}[A-Z]$")
NATIONAL_ID_PATTERN = re.compile(r"^\d{7,8}$")
BUSINESS_REGISTRATION_PATTERN = re.compile(r"^(PVT|CPR)-[A-Z0-9]{7}$", re.IGNORECASE)
POSTAL_CODE_PATTERN = re.compile(r"^\d{5}$")


def validate_phone(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    match = PHONE_PATTERN.match(value.strip().replace(" ", ""))
    if not match:
        return False, None
    return True, "254" + match.group(1)


def validate_kra_pin(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip().upper()
    return (True, cleaned) if KRA_PIN_PATTERN.match(cleaned) else (False, None)


def validate_national_id(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip()
    return (True, cleaned) if NATIONAL_ID_PATTERN.match(cleaned) else (False, None)


def validate_business_registration_number(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip().upper()
    return (True, cleaned) if BUSINESS_REGISTRATION_PATTERN.match(cleaned) else (False, None)


def validate_postal_code(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip()
    return (True, cleaned) if POSTAL_CODE_PATTERN.match(cleaned) else (False, None)
