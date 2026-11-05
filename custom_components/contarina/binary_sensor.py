"""Read-only collection and balance status sensors."""
from __future__ import annotations
from datetime import timedelta
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util
from .coordinator import ContarinaCoordinator
from .entity import ContarinaEntity

class ContarinaBinarySensor(ContarinaEntity, BinarySensorEntity):
    def __init__(self, coordinator: ContarinaCoordinator, ref: str, kind: str) -> None:
        super().__init__(coordinator, ref, kind, "Insoluti" if kind == "insoluti" else "Raccolta domani")
        self.kind = kind
        if kind == "insoluti":
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool | None:
        if not self.info:
            return None
        if self.kind == "insoluti":
            balance_ok = self.info.get("balance_ok")
            return not balance_ok if isinstance(balance_ok, bool) else None
        tomorrow = dt_util.now().date() + timedelta(days=1)
        return bool(self.info.get("calendar", {}).get(tomorrow))

    @property
    def extra_state_attributes(self):
        if self.kind != "raccolta_domani":
            return None
        tomorrow = dt_util.now().date() + timedelta(days=1)
        return {"rifiuti": list(self.info.get("calendar", {}).get(tomorrow, ()))}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator: ContarinaCoordinator = entry.runtime_data
    async_add_entities(
        ContarinaBinarySensor(coordinator, ref, kind)
        for ref in coordinator.data
        for kind in ("insoluti", "raccolta_domani")
    )
