"""
Ghana Country Package - Data Mapping

Provider Payload -> Country Mapping -> Canonical Event -> Workflow
Engine. If MTN MoMo or Vodafone Cash change their payload shape, only
these functions change - the Kernel never does.
"""

from typing import Any


def map_mtn_momo_callback(payload: dict[str, Any]) -> dict[str, Any] | None:
    """MTN MoMo Collections request-to-pay callback -> canonical event."""
    status = payload.get("status")

    if status != "SUCCESSFUL":
        return {
            "event": "payment.mtn_momo.failed",
            "data": {
                "status": status,
                "reason": payload.get("reason", ""),
            },
        }

    return {
        "event": "payment.mtn_momo.received",
        "data": {
            "amount": payload.get("amount"),
            "financial_transaction_id": payload.get("financialTransactionId"),
            "payer_msisdn": payload.get("payer", {}).get("partyId"),
            "external_id": payload.get("externalId"),
        },
    }


def map_vodafone_callback(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Vodafone Cash collection callback -> canonical event."""
    if payload.get("code") != "0000":
        return None
    return {
        "event": "payment.vodafone_cash.received",
        "data": {
            "amount": payload.get("amount"),
            "transaction_id": payload.get("transactionId"),
            "msisdn": payload.get("customerNumber"),
            "reference": payload.get("reference"),
        },
    }


MAPPERS = {
    "mtn_momo_gh": map_mtn_momo_callback,
    "vodafone_cash": map_vodafone_callback,
}


def map_payload(provider: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    mapper = MAPPERS.get(provider)
    return mapper(payload) if mapper else None
