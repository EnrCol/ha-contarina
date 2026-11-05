"""Pure parsers for Contarina response shapes, safe to test without Home Assistant."""
from __future__ import annotations
import base64
import binascii
import json
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation
from typing import Any

class ResponseShapeError(ValueError):
    """The service returned a different response shape."""

def jwt_claims(token: str) -> dict[str, Any]:
    """Decode JWT payload for exp/identity ONLY. Does not validate signature."""
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        data = json.loads(base64.urlsafe_b64decode(part))
    except (IndexError, ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise ResponseShapeError("Invalid JWT payload") from exc
    if not isinstance(data, dict) or not isinstance(data.get("exp"), int):
        raise ResponseShapeError("JWT lacks expiration")
    return data

def date_only(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None

def emptying_local_date(value: Any) -> date | None:
    if not isinstance(value, str) or "T" not in value:
        return date_only(value)
    try:
        normalized = value.replace("Z", "+00:00")
        timestamp = datetime.fromisoformat(normalized)
        if timestamp.tzinfo is None:
            return timestamp.date()
        return timestamp.astimezone(ZoneInfo("Europe/Rome")).date()
    except ValueError:
        return date_only(value)

def is_active(record: dict[str, Any], today: date) -> bool:
    starts = date_only(record.get("DATA_INIZIO") or record.get("start_date"))
    ends = date_only(record.get("DATA_FINE") or record.get("end_date"))
    return (starts is None or starts <= today) and (ends is None or ends >= today)

def required_list(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or not all(isinstance(x, dict) for x in payload):
        raise ResponseShapeError("Expected list of objects")
    return payload

def calendar_dates(rows: Any, material_names: dict[str, str] | None = None) -> dict[date, tuple[str, ...]]:
    mapping = material_names or {"S": "Secco", "E": "Vegetale", "U": "Umido", "V": "VPL", "C": "Carta"}
    result: dict[date, tuple[str, ...]] = {}
    for item in required_list(rows):
        day = date_only(item.get("data"))
        contents = item.get("svuotamenti", [])
        if day is None or not isinstance(contents, list):
            continue
        labels: list[str] = []
        for waste in contents:
            if not isinstance(waste, dict):
                continue
            code = str(waste.get("codice_contarina") or "")
            label = mapping.get(code) or waste.get("titolo") or code
            if label and label not in labels:
                labels.append(str(label))
        if labels:
            result[day] = tuple(labels)
    return dict(sorted(result.items()))

def next_collection(rows: dict[date, tuple[str, ...]], today: date) -> tuple[date, tuple[str, ...]] | None:
    return next(((day, labels) for day, labels in sorted(rows.items()) if day >= today), None)

def invoice_status(invoice: dict[str, Any]) -> str:
    try:
        state = int(invoice.get("stato_fattura"))
        loss = int(invoice.get("tipo_perdita"))
    except (ValueError, TypeError):
        return "unknown"
    if state in (3, 6, 9, 12):
        return "paid"
    if state == 8 or (state == 1 and loss in (0, 1, 2, 3, 4, 5, 6, 19, 20)):
        return "unpaid"
    if state == 7 or (state == 2 and loss in (0, 1, 2, 3, 4, 5, 6, 19, 20)):
        return "partially_paid"
    if state == 0 and loss in (0, 19, 20):
        return "due"
    if state in (4, 11) and loss in (0, 24, 25, 26):
        return "compensated"
    if state in (4, 11) and loss == 23:
        return "refund_due"
    if state in (4, 11) and loss == 27:
        return "non_refundable"
    if state in (41, 42):
        return "cancelled"
    return "unknown"

def decimal_amount(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None

def latest_invoice(items: Any) -> dict[str, Any] | None:
    if not isinstance(items, list):
        return None
    usable = [x for x in items if isinstance(x, dict)]
    return max(usable, key=lambda x: date_only(x.get("data_emissione")) or date.min, default=None)

def count_emptyings(items: Any, year: int) -> int:
    seen: set[tuple[Any, ...]] = set()
    for item in required_list(items):
        day = emptying_local_date(item.get("data"))
        if day is None or day.year != year:
            continue
        uid = item.get("id_vuotamento")
        key = ("id", uid) if uid is not None else ("fallback", len(seen))
        seen.add(key)
    return len(seen)

def last_emptying(items: Any) -> date | None:
    values = [emptying_local_date(i.get("data")) for i in required_list(items)]
    return max((x for x in values if x is not None), default=None)

def parse_balance(payload: Any) -> bool:
    if isinstance(payload, bool):
        return payload
    if isinstance(payload, str) and payload.strip().lower() in ("true", "false"):
        return payload.strip().lower() == "true"
    raise ResponseShapeError("Invalid check-balance response")

def iso_start(day: date) -> str:
    local = datetime.combine(day, time.min, ZoneInfo("Europe/Rome"))
    return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

def iso_end(day: date) -> str:
    local = datetime.combine(day, time(23, 59, 59, 999000), ZoneInfo("Europe/Rome"))
    return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.999Z")

# Amounts are grouped by invoice issuance year, not by payment transaction date.
# Credit/refund/compensation/cancellation and unknown states are excluded until
# SOL supplies a verified accounting meaning for them.
BILLABLE_STATUSES = frozenset(("paid", "unpaid", "partially_paid", "due"))
OPEN_STATUSES = frozenset(("unpaid", "partially_paid", "due"))


def display_date(value: date | None) -> str | None:
    """Show a human-readable local date while keeping ISO in attributes."""
    return value.strftime("%d-%m-%Y") if value is not None else None


def invoice_bucket(invoice: dict[str, Any], today: date) -> str | None:
    """Classify an unsettled invoice without claiming that a debt exists."""
    state = invoice_status(invoice)
    if state not in OPEN_STATUSES:
        return None
    due = date_only(invoice.get("scadenza"))
    if due is None:
        return "review"
    if due < today:
        return "overdue"
    return "upcoming" if state == "due" else "review"


def _safe_amount(value: Any) -> Decimal | None:
    amount = decimal_amount(value)
    return amount if amount is not None and amount.is_finite() else None


def invoice_summary(items: Any, year: int, today: date) -> dict[str, Any]:
    """Summarize SOL invoices without assuming amounts are paid or outstanding.

    Totals include known invoice states only and are by issue date. Unknown,
    cancelled, refunded and compensated documents are not netted into totals:
    the API's credit-note accounting is not verified.
    """
    invoices = required_list(items)
    yearly_totals: dict[int, Decimal] = {}
    history: list[dict[str, Any]] = []
    excluded = 0
    open_count = 0
    upcoming_count = 0
    overdue_count = 0
    review_count = 0
    for item in invoices:
        status = invoice_status(item)
        issued = date_only(item.get("data_emissione"))
        due = date_only(item.get("scadenza"))
        amount = _safe_amount(item.get("tot_totalefatt"))
        paid = _safe_amount(item.get("importo_pagato_totale"))
        bucket = invoice_bucket(item, today)
        if bucket is not None:
            open_count += 1
            if bucket == "upcoming":
                upcoming_count += 1
            elif bucket == "overdue":
                overdue_count += 1
            else:
                review_count += 1
        includable = issued is not None and amount is not None and status in BILLABLE_STATUSES
        if includable:
            yearly_totals[issued.year] = yearly_totals.get(issued.year, Decimal("0")) + amount
        else:
            excluded += 1
        history.append({
            "emissione": issued.isoformat() if issued else None,
            "scadenza": due.isoformat() if due else None,
            "importo": float(amount) if amount is not None else None,
            "importo_pagato_registrato": float(paid) if paid is not None else None,
            "stato": status,
            "compreso_nel_fatturato": includable,
        })
    history.sort(key=lambda row: row["emissione"] or "", reverse=True)
    annual_totals = {str(y): float(yearly_totals[y]) for y in sorted(yearly_totals)}
    # Home Assistant limits the size of entity state attributes. The complete
    # annual summary is retained, while per-invoice UI history is bounded.
    history_limit = 60
    return {
        "count": len(invoices),
        "open": open_count,
        "upcoming": upcoming_count,
        "overdue": overdue_count,
        "review": review_count,
        "year": year,
        "year_total": float(yearly_totals.get(year, Decimal("0"))),
        "year_totals": annual_totals,
        "excluded_count": excluded,
        "history": history[:history_limit],
        "history_truncated": len(history) > history_limit,
    }

def material_label(material: Any) -> str:
    """Readable SOL material label; never infer it from a container serial."""
    if isinstance(material, str) and material.strip():
        value = material.strip()
        lower = value.casefold()
        if "secco" in lower:
            return "Secco"
        if "vegetale" in lower:
            return "Vegetale"
        if "umido" in lower:
            return "Umido"
        if "carta" in lower:
            return "Carta"
        if "vetro" in lower or "plastica" in lower or "lattine" in lower:
            return "VPL"
        return value
    return "Contenitore"


def _whole_nonnegative(value: Any) -> int | None:
    """Accept integer-like SOL values without silently truncating fractions."""
    if isinstance(value, bool):
        return None
    text = str(value).strip()
    return int(text) if text.isdecimal() else None


def secco_minimum_120l(
    components: Any,
    capacity_liters: Any,
    emptyings_year: Any,
    *,
    is_domestic: bool,
    secco_container_count: int = 1,
) -> dict[str, Any]:
    """Estimate Contarina's annual Secco minimum for one domestic 120 L bin.

    The number of family members returned by SOL may be current rather than
    the value on 31 December of the previous year used for invoicing.
    No minimum is inferred for other container sizes or contract categories.
    """
    if not is_domestic or secco_container_count != 1:
        return {}
    members = _whole_nonnegative(components)
    liters = _whole_nonnegative(capacity_liters)
    actual = _whole_nonnegative(emptyings_year)
    if members is None or members < 1 or liters != 120 or actual is None:
        return {}
    minimum = members + 1
    return {
        "minimo_annuo_stimato": minimum,
        "svuotamenti_prima_eccedenza": max(0, minimum - actual),
        "svuotamenti_oltre_minimo": max(0, actual - minimum),
        "componenti_calcolo": members,
        "criterio_minimo": "Contarina: utenza domestica, bidone Secco 120 L, componenti + 1",
        "verifica_componenti_31_12_precedente": True,
    }
