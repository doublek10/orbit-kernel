"""
Tanzania Country Package - Data Mapping

Provider Payload -> Country Mapping -> Canonical Event -> Workflow
Engine. If M-Pesa, Tigo Pesa or HaloPesa change their payload shape,
only these functions change - the Kernel never does.
"""

from typing import Any


def map_mpesa_stk_callback(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Vodacom M-Pesa STK Push callback -> payment.mpesa.received / .failed"""
    body = payload.get("Body", {}).get("stkCallback", {})
    result_code = body.get("ResultCode")

    if result_code != 0:
        return {
            "event": "payment.mpesa.failed",
            "data": {
                "result_code": result_code,
                "result_desc": body.get("ResultDesc", ""),
            },
        }

    items = {i["Name"]: i.get("Value") for i in body.get("CallbackMetadata", {}).get("Item", [])}
    return {
        "event": "payment.mpesa.received",
        "data": {
            "amount": items.get("Amount"),
            "mpesa_receipt_number": items.get("MpesaReceiptNumber"),
            "phone_number": items.get("PhoneNumber"),
            "transaction_date": items.get("TransactionDate"),
        },
    }


def map_tigo_pesa_callback(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Tigo Pesa collection callback -> canonical event."""
    status_code = str(payload.get("statusCode"))

    if status_code != "200":
        return {
            "event": "payment.tigo_pesa.failed",
            "data": {
                "status_code": status_code,
                "reason": payload.get("message", ""),
            },
        }

    return {
        "event": "payment.tigo_pesa.received",
        "data": {
            "amount": payload.get("amount"),
            "reference": payload.get("referenceId"),
            "msisdn": payload.get("msisdn"),
        },
    }


def map_halopesa_callback(payload: dict[str, Any]) -> dict[str, Any] | None:
    """HaloPesa collection callback -> canonical event."""
    if payload.get("status") != "SUCCESS":
        return None
    return {
        "event": "payment.halopesa.received",
        "data": {
            "amount": payload.get("amount"),
            "reference": payload.get("transactionId"),
            "msisdn": payload.get("msisdn"),
        },
    }


MAPPERS = {
    "mpesa_tz": map_mpesa_stk_callback,
    "tigo_pesa": map_tigo_pesa_callback,
    "halopesa": map_halopesa_callback,
}


def map_payload(provider: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    mapper = MAPPERS.get(provider)
    return mapper(payload) if mapper else None
