"""Periodic coordinator for all selected Contarina contracts."""
from __future__ import annotations
import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import ContarinaAuthError, ContarinaConnectionError
from .auth import ContarinaSession
from .const import (
    CONF_BILL_HOURS, CONF_CONDOS, CONF_CONTRACTS, CONF_HORIZON, CONF_POLL_HOURS,
    DEFAULT_BILL_HOURS, DEFAULT_HORIZON, DEFAULT_POLL_HOURS, DOMAIN,
)
from .models import (
    ResponseShapeError, calendar_dates, date_only, is_active, iso_end, iso_start,
    count_emptyings, last_emptying,
)

class ContarinaCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, session: ContarinaSession) -> None:
        super().__init__(
            hass, logger=logging.getLogger(__name__), name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(hours=int(entry.options.get(CONF_POLL_HOURS, DEFAULT_POLL_HOURS))),
        )
        self.entry = entry
        self.session = session
        self._billing_cache: dict[str, tuple[list[dict[str, Any]], bool]] = {}
        self._billing_at: datetime | None = None
        self._calendar_names: dict[str, str] = {}
        self._ecocalendars: list[dict[str, Any]] = []
        self._static_at: datetime | None = None

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            return await self._load()
        except ContarinaAuthError as exc:
            raise ConfigEntryAuthFailed("SOL browser authentication required") from exc
        except (ContarinaConnectionError, ResponseShapeError, ValueError, TypeError) as exc:
            raise UpdateFailed(f"Contarina response could not be loaded: {type(exc).__name__}") from exc

    async def _load(self) -> dict[str, dict[str, Any]]:
        now = datetime.now(timezone.utc)
        from homeassistant.util import dt as dt_util
        today = dt_util.now().date()
        horizon = max(7, min(int(self.entry.options.get(CONF_HORIZON, DEFAULT_HORIZON)), 366))
        include_condos = bool(self.entry.options.get(CONF_CONDOS, False))
        billing_interval = timedelta(hours=int(self.entry.options.get(CONF_BILL_HOURS, DEFAULT_BILL_HOURS)))
        need_billing = self._billing_at is None or now - self._billing_at >= billing_interval
        if self._static_at is None or now - self._static_at >= timedelta(hours=24):
            self._ecocalendars = await self.session.call("ecocalendars")
            waste_types = await self.session.call("waste_types")
            self._calendar_names = {
                str(x["codice_contarina"]): str(x.get("titolo") or x["codice_contarina"])
                for x in waste_types if x.get("codice_contarina")
            }
            self._static_at = now
        contracts = await self.session.call("get_contracts")
        by_ref = {str(c.get("reference_code")): c for c in contracts if c.get("reference_code")}
        selected = [str(x) for x in self.entry.data[CONF_CONTRACTS]]
        result: dict[str, dict[str, Any]] = {}
        for ref in selected:
            if ref not in by_ref:
                continue
            contract = by_ref[ref]
            detail, areas, equipment = await asyncio.gather(
                self.session.call("contract_detail", ref),
                self.session.call("areas", ref),
                self.session.call("equipment", ref),
            )
            region = next((z for z in areas if str(z.get("id_tipologia")) == "4"), None)
            ecocal = next((c for c in self._ecocalendars if region and
                            str(c.get("id_contarina")) == str(region.get("id"))), None)
            calendar_id = str(ecocal.get("id")) if ecocal else None
            collection = {}
            if calendar_id:
                rows = await self.session.call("collections", calendar_id, today, today + timedelta(days=horizon))
                collection = calendar_dates(rows, self._calendar_names)
            containers: dict[str, dict[str, Any]] = {}
            for item in equipment:
                if not include_condos and item.get("CONDOMINIALE"):
                    continue
                code = item.get("COD_CONTENITORE")
                if not code:
                    continue
                code = str(code)
                start = date_only(item.get("DATA_INIZIO")) or today
                end = date_only(item.get("DATA_FINE"))
                if end and end.year < today.year:
                    continue
                range_start = max(start, date(today.year, 1, 1))
                range_end = min(end or today, today)
                if range_end < range_start:
                    events = []
                else:
                    events = await self.session.call("emptyings", ref, code, iso_start(range_start), iso_end(range_end))
                service = item.get("tipo_servizio")
                service = service if isinstance(service, dict) else {}
                containers[code] = {
                    "material": service.get("materiale"), "liters": service.get("litri"),
                    "active": is_active(item, today),
                    "count_year": count_emptyings(events, today.year),
                    "last_emptying": last_emptying(events),
                }
            if need_billing or ref not in self._billing_cache:
                invoices, settled = await asyncio.gather(
                    self.session.call("accounting", ref),
                    self.session.call("check_balance", ref),
                )
                self._billing_cache[ref] = (invoices, settled)
            invoices, settled = self._billing_cache[ref]
            result[ref] = {
                "contract": contract,
                "detail": {"numero_componenti_c": detail.get("numero_componenti_c")},
                "calendar_id": calendar_id,
                "calendar": collection,
                "containers": containers,
                "invoices": invoices,
                "balance_ok": settled,
            }
        if need_billing:
            self._billing_at = now
        return result

    async def async_events_for_range(self, ref: str, start: date, end: date) -> dict[date, tuple[str, ...]]:
        data = self.data.get(ref) if self.data else None
        if not data or not data["calendar_id"]:
            return {}
        if end < start or (end - start).days > 370:
            return {}
        try:
            rows = await self.session.call("collections", data["calendar_id"], start, end)
        except ContarinaAuthError:
            self.entry.async_start_reauth(self.hass)
            return {}
        except (ContarinaConnectionError, ResponseShapeError):
            return {d: labels for d, labels in data.get("calendar", {}).items() if start <= d <= end}
        return calendar_dates(rows, self._calendar_names)
