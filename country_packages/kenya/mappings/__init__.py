"""
Kenya Country Package - Data Mapping

Provider Payload -> Country Mapping -> Canonical Event -> Workflow
Engine. If M-Pesa or Airtel change their payload shape, only these
functions change - the Kernel and its Workflow Engine never do.
"""

from typing import Any


def map_mpesa_stk_callback(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Daraja STK Push callback -> payment.mpesa.received / .failed"""
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


def map_airtel_callback(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Airtel Money collection callback -> payment.received"""
    transaction = payload.get("transaction", {})
    if transaction.get("status_code") != "TS":
        return None
    return {
        "event": "payment.received",
        "data": {
            "amount": transaction.get("amount"),
            "currency": "KES",
            "reference": transaction.get("id"),
            "payer": payload.get("msisdn"),
        },
    }


MAPPERS = {
    "mpesa": map_mpesa_stk_callback,
    "airtel_money": map_airtel_callback,
}


def map_payload(provider: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    mapper = MAPPERS.get(provider)
    return mapper(payload) if mapper else None
