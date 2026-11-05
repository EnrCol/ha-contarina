"""Read-only sensors from Contarina SOL, with stable IDs and readable labels."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import ContarinaCoordinator
from .entity import ContarinaEntity
from .models import decimal_amount, display_date, invoice_status, latest_invoice, next_collection, material_label, secco_minimum_120l


class ContarinaSensor(ContarinaEntity, SensorEntity):
    def __init__(
        self,
        coordinator: ContarinaCoordinator,
        ref: str,
        key: str,
        name: str,
        extract: Callable[[dict[str, Any]], Any],
        *,
        device_class=None,
        state_class=None,
        unit=None,
        attributes=None,
    ) -> None:
        super().__init__(coordinator, ref, key, name)
        self._extract = extract
        self._attributes_fn = attributes
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        return self._extract(self.info) if self.info else None

    @property
    def extra_state_attributes(self):
        return self._attributes_fn(self.info) if self.info and self._attributes_fn else None


def _collection_text(data: dict[str, Any], offset: int) -> str:
    labels = data.get("calendar", {}).get(dt_util.now().date() + timedelta(days=offset), ())
    return ", ".join(labels) if labels else "Nessun rifiuto"


def _upcoming(data: dict[str, Any]):
    return next_collection(data.get("calendar", {}), dt_util.now().date())


def _upcoming_attributes(data: dict[str, Any]) -> dict[str, Any]:
    upcoming = _upcoming(data)
    return {
        "data_iso": upcoming[0].isoformat(),
        "rifiuti": list(upcoming[1]),
    } if upcoming else {}


def _last_invoice(data: dict[str, Any]):
    return latest_invoice(data.get("invoices", []))


def _last_invoice_amount(data: dict[str, Any]) -> float | None:
    item = _last_invoice(data)
    if item is None:
        return None
    value = decimal_amount(item.get("tot_totalefatt"))
    return float(value) if value is not None and value.is_finite() else None


def _invoice_attributes(data: dict[str, Any]) -> dict[str, Any]:
    item = _last_invoice(data)
    if not item:
        return {}
    return {
        "stato": invoice_status(item),
        "emissione": str(item.get("data_emissione") or "")[:10],
        "scadenza": str(item.get("scadenza") or "")[:10],
        "pdf_disponibile": item.get("file_esistente") == 1,
        "tipo_importo": "totale_fattura_non_residuo",
    }


def _invoice_summary(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("invoice_summary", {})


def _invoice_history_attributes(data: dict[str, Any]) -> dict[str, Any]:
    summary = _invoice_summary(data)
    return {
        "storico_fatture": summary.get("history", []),
        "totali_annuali_fatturati": summary.get("year_totals", {}),
        "documenti_esclusi_dai_totali": summary.get("excluded_count", 0),
        "storico_troncato": summary.get("history_truncated", False),
        "criterio": "anno_emissione_solo_stati_fattura_noti",
    }


def _annual_invoice_attributes(data: dict[str, Any]) -> dict[str, Any]:
    summary = _invoice_summary(data)
    return {
        "anno": summary.get("year"),
        "totali_annuali_fatturati": summary.get("year_totals", {}),
        "documenti_esclusi_dai_totali": summary.get("excluded_count", 0),
        "criterio": "fatturato_emesso_non_pagamenti",
    }


def _standard_sensors(coordinator: ContarinaCoordinator, ref: str) -> list[SensorEntity]:
    sensors = [
        ContarinaSensor(coordinator, ref, "rifiuti_oggi", "Rifiuti oggi",
                        lambda d: _collection_text(d, 0)),
        ContarinaSensor(coordinator, ref, "rifiuti_domani", "Rifiuti domani",
                        lambda d: _collection_text(d, 1)),
        # Keep the pre-existing unique ID; textual date format is deliberate.
        # The machine-readable ISO date remains available in data_iso.
        ContarinaSensor(coordinator, ref, "prossima_raccolta", "Prossima raccolta",
                        lambda d: display_date(_upcoming(d)[0]) if _upcoming(d) else None,
                        attributes=_upcoming_attributes),
        ContarinaSensor(coordinator, ref, "ultima_fattura", "Ultima fattura",
                        _last_invoice_amount, device_class=SensorDeviceClass.MONETARY,
                        unit="EUR", attributes=_invoice_attributes),
        ContarinaSensor(coordinator, ref, "fatture_totali", "Fatture disponibili",
                        lambda d: _invoice_summary(d).get("count"),
                        attributes=_invoice_history_attributes),
        # This sensor keeps its existing unique ID and explains its contents
        # rather than implying that an upcoming invoice is overdue.
        ContarinaSensor(coordinator, ref, "fatture_da_verificare", "Fatture da verificare",
                        lambda d: _invoice_summary(d).get("open"),
                        attributes=lambda d: {
                            "in_scadenza": _invoice_summary(d).get("upcoming"),
                            "scadute_da_verificare": _invoice_summary(d).get("overdue"),
                            "pagamenti_da_verificare": _invoice_summary(d).get("review"),
                        }),
        ContarinaSensor(coordinator, ref, "fatture_in_scadenza", "Fatture in scadenza",
                        lambda d: _invoice_summary(d).get("upcoming")),
        ContarinaSensor(coordinator, ref, "fatture_scadute", "Fatture scadute da verificare",
                        lambda d: _invoice_summary(d).get("overdue")),
        ContarinaSensor(coordinator, ref, "totale_fatturato_anno", "Totale fatturato anno",
                        lambda d: _invoice_summary(d).get("year_total"),
                        device_class=SensorDeviceClass.MONETARY, unit="EUR",
                        attributes=_annual_invoice_attributes),
        ContarinaSensor(coordinator, ref, "componenti", "Componenti nucleo",
                        lambda d: d.get("detail", {}).get("numero_componenti_c")),
    ]
    sensors[-1]._attr_entity_registry_enabled_default = False
    return sensors


def _container_attributes(data: dict[str, Any], code: str) -> dict[str, Any]:
    container = data.get("containers", {}).get(code, {})
    return {
        "codice_contenitore": code,
        "materiale": container.get("material"),
        "litri": container.get("liters"),
        "attivo": container.get("active"),
        "storico_dal": container.get("history_from"),
        "storico_completo": container.get("history_complete"),
    }


def _annual_emptying_attributes(data: dict[str, Any], code: str) -> dict[str, Any]:
    """Attach a conservative Secco minimum estimate to an existing bin entity."""
    details = _container_attributes(data, code)
    container = data.get("containers", {}).get(code, {})
    if not container.get("active") or material_label(container.get("material")) != "Secco":
        return details
    secco_bins = sum(
        material_label(value.get("material")) == "Secco"
        for value in data.get("containers", {}).values()
    )
    contract = data.get("contract", {})
    result = secco_minimum_120l(
        components=data.get("detail", {}).get("numero_componenti_c"),
        capacity_liters=container.get("liters"),
        emptyings_year=container.get("count_year"),
        is_domestic=str(contract.get("tipologia_utenza_c")) == "1",
        secco_container_count=secco_bins,
    )
    details.update(result)
    return details


def _last_emptying_attributes(data: dict[str, Any], code: str) -> dict[str, Any]:
    details = _container_attributes(data, code)
    last = data.get("containers", {}).get(code, {}).get("last_emptying")
    details["data_iso"] = last.isoformat() if last is not None else None
    return details


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: ContarinaCoordinator = entry.runtime_data
    entities: list[SensorEntity] = []
    for ref, data in coordinator.data.items():
        entities.extend(_standard_sensors(coordinator, ref))
        names_seen: dict[str, int] = {}
        for code, record in data.get("containers", {}).items():
            material = material_label(record.get("material"))
            names_seen[material] = names_seen.get(material, 0) + 1
            # Different physical bins with the same material need distinct
            # labels but must keep their existing stable unique IDs.
            label = material if names_seen[material] == 1 else f"{material} {names_seen[material]}"
            entities.append(ContarinaSensor(
                coordinator, ref, f"svuotamenti_{code}", f"Svuotamenti anno - {label}",
                lambda d, cid=code: d.get("containers", {}).get(cid, {}).get("count_year"),
                state_class=SensorStateClass.TOTAL_INCREASING,
                attributes=lambda d, cid=code: _annual_emptying_attributes(d, cid),
            ))
            entities.append(ContarinaSensor(
                coordinator, ref, f"ultimo_svuotamento_{code}", f"Ultimo svuotamento - {label}",
                lambda d, cid=code: display_date(
                    d.get("containers", {}).get(cid, {}).get("last_emptying"),
                ),
                attributes=lambda d, cid=code: _last_emptying_attributes(d, cid),
            ))
    async_add_entities(entities)
