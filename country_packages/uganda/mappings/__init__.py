"""
Uganda Country Package - Data Mapping

Provider Payload -> Country Mapping -> Canonical Event -> Workflow
Engine. If MTN MoMo or Airtel Money change their payload shape, only
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


def map_airtel_callback(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Airtel Money collection callback -> canonical event."""
    transaction = payload.get("transaction", {})
    status_code = transaction.get("status_code")

    if status_code != "TS":
        return {
            "event": "payment.airtel.failed",
            "data": {
                "status_code": status_code,
                "reason": transaction.get("message", ""),
            },
        }

    return {
        "event": "payment.airtel.received",
        "data": {
            "amount": transaction.get("amount"),
            "reference": transaction.get("id"),
            "msisdn": payload.get("msisdn"),
        },
    }


MAPPERS = {
    "mtn_momo_ug": map_mtn_momo_callback,
    "airtel_money_ug": map_airtel_callback,
}


def map_payload(provider: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    mapper = MAPPERS.get(provider)
    return mapper(payload) if mapper else None
