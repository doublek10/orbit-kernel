"""
CSV Statement Import

Every provider adapter so far is either fully mocked (mock_mobile_money)
or would need real, signed API credentials Orbit doesn't have yet (a
bank, a live mobile money API). This one is different: it's a genuinely
real integration that works today with a company's actual data, because
banks and mobile money providers already let businesses export a CSV/
Excel statement - this just needs to parse whatever they hand it.

Expected columns (case-insensitive, order doesn't matter):
    date, description, amount            (signed: negative = outflow)
  or
    date, description, amount, direction (direction = inflow|outflow, amount unsigned)

Unrecognized columns are ignored. Rows that can't be parsed are skipped
and reported back, rather than failing the whole import - a partial,
honest result beats an all-or-nothing wall.
"""

import csv
import io
from datetime import datetime


def parse_statement_csv(csv_text: str) -> tuple[list[dict], list[str]]:
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    if reader.fieldnames is None:
        return [], ["No header row found"]

    fields = {name.strip().lower(): name for name in reader.fieldnames}
    errors: list[str] = []
    transactions: list[dict] = []

    required = {"date", "description", "amount"}
    missing = required - set(fields.keys())
    if missing:
        return [], [f"Missing required column(s): {', '.join(sorted(missing))}"]

    for i, row in enumerate(reader, start=2):  # row 1 is the header
        try:
            raw_date = row[fields["date"]].strip()
            description = row[fields["description"]].strip()
            raw_amount = row[fields["amount"]].strip().replace(",", "")
            amount = float(raw_amount)

            if "direction" in fields and row[fields["direction"]].strip():
                direction = row[fields["direction"]].strip().lower()
                if direction not in ("inflow", "outflow"):
                    raise ValueError(f"invalid direction '{direction}'")
                amount = abs(amount)
            else:
                direction = "inflow" if amount >= 0 else "outflow"
                amount = abs(amount)

            occurred_at = _parse_date(raw_date)

            transactions.append(
                {
                    "direction": direction,
                    "amount": amount,
                    "description": description,
                    "occurred_at": occurred_at,
                }
            )
        except (KeyError, ValueError) as exc:
            errors.append(f"Row {i}: {exc}")

    return transactions, errors


def _parse_date(raw: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"unrecognized date format '{raw}'")
