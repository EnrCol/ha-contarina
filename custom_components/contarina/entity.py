"""Shared entity device identity."""
from __future__ import annotations
from typing import Any
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceEntryType
from .const import DOMAIN
from .coordinator import ContarinaCoordinator

class ContarinaEntity(CoordinatorEntity[ContarinaCoordinator]):
    _attr_has_entity_name = True
    def __init__(self, coordinator: ContarinaCoordinator, ref: str, key: str, name: str) -> None:
        super().__init__(coordinator)
        self.ref = ref
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.data['account_id']}_{ref}_{key}"
        contract = coordinator.data[ref]["contract"]
        readable_name = contract.get("sol_contract_name") or contract.get("name") or "Utenza"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{coordinator.entry.data['account_id']}_{ref}")},
            "name": f"Contarina {readable_name}",
            "manufacturer": "Contarina",
            "model": "Utenza domestica" if str(contract.get("tipologia_utenza_c")) == "1" else "Utenza non domestica",
            "entry_type": DeviceEntryType.SERVICE,
        }

    @property
    def info(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get(self.ref, {})
