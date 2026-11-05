"""Native read-only Home Assistant collection calendars."""
from __future__ import annotations
from datetime import date, datetime, timedelta
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util
from .coordinator import ContarinaCoordinator
from .entity import ContarinaEntity

def _event(day: date, labels: tuple[str, ...]) -> CalendarEvent:
    return CalendarEvent(start=day, end=day + timedelta(days=1), summary=f"Raccolta {', '.join(labels)}")

class ContarinaCalendar(ContarinaEntity, CalendarEntity):
    def __init__(self, coordinator: ContarinaCoordinator, ref: str) -> None:
        super().__init__(coordinator, ref, "calendar", "Raccolta rifiuti")

    @property
    def event(self) -> CalendarEvent | None:
        today = dt_util.now().date()
        future = [(day, labels) for day, labels in self.info.get("calendar", {}).items() if day >= today]
        if not future:
            return None
        day, labels = min(future)
        return _event(day, labels)

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime,
                               end_date: datetime) -> list[CalendarEvent]:
        dates = await self.coordinator.async_events_for_range(
            self.ref, start_date.date(), end_date.date(),
        )
        return [_event(day, labels) for day, labels in sorted(dates.items())
                if start_date.date() <= day < end_date.date()]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator: ContarinaCoordinator = entry.runtime_data
    async_add_entities(ContarinaCalendar(coordinator, ref) for ref in coordinator.data)
