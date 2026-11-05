"""Privacy-preserving diagnostics: only aggregate counts and booleans.

Neither the config entry nor the remote response object is serialized.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    return {
        "integration": "contarina",
        "prototype_version": "0.2.0b1",
        "selected_contract_count": len(entry.data.get("contracts", [])),
        "loaded_contract_count": len(data),
        "calendar_available_count": sum(bool(x.get("calendar_id")) for x in data.values()),
        "physical_container_count": sum(len(x.get("containers", {})) for x in data.values()),
        "last_update_success": coordinator.last_update_success,
        "authentication": "configured",
    }
