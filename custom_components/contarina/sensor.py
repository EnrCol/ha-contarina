"""Sensors backed by authenticated Contarina SOL responses."""
from __future__ import annotations
from datetime import timedelta
from typing import Any, Callable
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util
from .coordinator import ContarinaCoordinator
from .entity import ContarinaEntity
from .models import decimal_amount, invoice_status, latest_invoice, next_collection

class ContarinaSensor(ContarinaEntity, SensorEntity):
    def __init__(self, coordinator: ContarinaCoordinator, ref: str, key: str, name: str,
                 extract: Callable[[dict[str, Any]], Any], *, device_class=None, state_class=None,
                 unit=None, attributes=None) -> None:
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

def _last_invoice(data: dict[str, Any]):
    return latest_invoice(data.get("invoices", []))

def _invoice_attributes(data: dict[str, Any]) -> dict[str, Any]:
    item = _last_invoice(data)
    if not item:
        return {}
    return {
        "stato": invoice_status(item),
        "emissione": str(item.get("data_emissione") or "")[:10],
        "scadenza": str(item.get("scadenza") or "")[:10],
        "pdf_disponibile": item.get("file_esistente") == 1,
    }

def _standard_sensors(coordinator: ContarinaCoordinator, ref: str) -> list[SensorEntity]:
    sensors = [
        ContarinaSensor(coordinator, ref, "rifiuti_oggi", "Rifiuti oggi", lambda d: _collection_text(d, 0)),
        ContarinaSensor(coordinator, ref, "rifiuti_domani", "Rifiuti domani", lambda d: _collection_text(d, 1)),
        ContarinaSensor(coordinator, ref, "prossima_raccolta", "Prossima raccolta",
                        lambda d: _upcoming(d)[0] if _upcoming(d) else None,
                        device_class=SensorDeviceClass.DATE,
                        attributes=lambda d: {"rifiuti": list(_upcoming(d)[1])} if _upcoming(d) else {}),
        ContarinaSensor(coordinator, ref, "ultima_fattura", "Ultima fattura",
                        lambda d: float(decimal_amount(_last_invoice(d).get("tot_totalefatt")))
                        if _last_invoice(d) and decimal_amount(_last_invoice(d).get("tot_totalefatt")) is not None else None,
                        device_class=SensorDeviceClass.MONETARY, unit="EUR",
                        attributes=_invoice_attributes),
        ContarinaSensor(coordinator, ref, "fatture_totali", "Fatture disponibili",
                        lambda d: len(d.get("invoices", []))),
        ContarinaSensor(coordinator, ref, "fatture_da_verificare", "Fatture aperte",
                        lambda d: sum(invoice_status(x) in ("unpaid", "partially_paid", "due")
                                      for x in d.get("invoices", []))),
        ContarinaSensor(coordinator, ref, "componenti", "Componenti nucleo",
                        lambda d: d.get("detail", {}).get("numero_componenti_c")),
    ]
    sensors[-1]._attr_entity_registry_enabled_default = False
    return sensors

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator: ContarinaCoordinator = entry.runtime_data
    entities: list[SensorEntity] = []
    for ref, data in coordinator.data.items():
        entities.extend(_standard_sensors(coordinator, ref))
        for code in data.get("containers", {}):
            entities.append(ContarinaSensor(
                coordinator, ref, f"svuotamenti_{code}", f"Svuotamenti anno {code}",
                lambda d, cid=code: d.get("containers", {}).get(cid, {}).get("count_year"),
                state_class=SensorStateClass.TOTAL_INCREASING,
                attributes=lambda d, cid=code: {
                    "materiale": d.get("containers", {}).get(cid, {}).get("material"),
                    "litri": d.get("containers", {}).get(cid, {}).get("liters"),
                    "attivo": d.get("containers", {}).get(cid, {}).get("active"),
                },
            ))
            entities.append(ContarinaSensor(
                coordinator, ref, f"ultimo_svuotamento_{code}", f"Ultimo svuotamento anno {code}",
                lambda d, cid=code: d.get("containers", {}).get(cid, {}).get("last_emptying"),
                device_class=SensorDeviceClass.DATE,
            ))
    async_add_entities(entities)
