"""
Nigeria Country Package - Data Mapping

Provider Payload -> Country Mapping -> Canonical Event -> Workflow
Engine. If OPay, PalmPay or Paga change their payload shape, only these
functions change - the Kernel never does.
"""

from typing import Any


def map_opay_callback(payload: dict[str, Any]) -> dict[str, Any] | None:
    """OPay payment callback -> canonical event."""
    status = payload.get("status")

    if status != "SUCCESS":
        return {
            "event": "payment.opay.failed",
            "data": {
                "status": status,
                "reason": payload.get("message", ""),
            },
        }

    return {
        "event": "payment.opay.received",
        "data": {
            "amount": payload.get("amount"),
            "reference": payload.get("reference"),
            "customer_msisdn": payload.get("payerId"),
            "order_id": payload.get("orderNo"),
        },
    }


def map_palmpay_callback(payload: dict[str, Any]) -> dict[str, Any] | None:
    """PalmPay collection callback -> canonical event."""
    if payload.get("respCode") != "00000000":
        return None
    return {
        "event": "payment.palmpay.received",
        "data": {
            "amount": payload.get("orderAmount"),
            "order_no": payload.get("orderNo"),
            "customer_number": payload.get("customerNumber"),
        },
    }


def map_paga_callback(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Paga transaction notification -> canonical event."""
    if str(payload.get("responseCode")) != "0":
        return None
    return {
        "event": "payment.paga.received",
        "data": {
            "amount": payload.get("amount"),
            "reference_number": payload.get("referenceNumber"),
            "payer": payload.get("payerDetails", {}).get("phoneNumber"),
        },
    }


MAPPERS = {
    "opay": map_opay_callback,
    "palmpay": map_palmpay_callback,
    "paga": map_paga_callback,
}


def map_payload(provider: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    mapper = MAPPERS.get(provider)
    return mapper(payload) if mapper else None
