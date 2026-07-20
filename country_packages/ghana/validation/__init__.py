"""
Ghana Country Package - Validation

Country-specific validation for phone numbers, business registration
numbers, the Ghana Card (national ID), TIN and postal (GhanaPost GPS)
codes. Every `validate_*` returns (is_valid, normalized_or_none).
"""

import re

PHONE_PATTERN = re.compile(r"^(?:\+233|233|0)(2\d{8}|5\d{8})$")
TIN_PATTERN = re.compile(r"^[A-Z]\d{10}$")
GHANA_CARD_PATTERN = re.compile(r"^GHA-\d{9}-\d$")
BUSINESS_REGISTRATION_PATTERN = re.compile(r"^(CS|BN)\d{6,9}$", re.IGNORECASE)
# GhanaPost GPS digital address, e.g. GA-123-4567
GPS_ADDRESS_PATTERN = re.compile(r"^[A-Z]{2}-\d{3,4}-\d{4}$")


def validate_phone(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    match = PHONE_PATTERN.match(value.strip().replace(" ", ""))
    if not match:
        return False, None
    return True, "233" + match.group(1)


def validate_tin(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip().upper()
    return (True, cleaned) if TIN_PATTERN.match(cleaned) else (False, None)


def validate_ghana_card(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip().upper()
    return (True, cleaned) if GHANA_CARD_PATTERN.match(cleaned) else (False, None)


def validate_business_registration_number(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip().upper()
    return (True, cleaned) if BUSINESS_REGISTRATION_PATTERN.match(cleaned) else (False, None)


def validate_gps_address(value: str) -> tuple[bool, str | None]:
    if not value:
        return False, None
    cleaned = value.strip().upper()
    return (True, cleaned) if GPS_ADDRESS_PATTERN.match(cleaned) else (False, None)
