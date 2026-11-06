"""Sliding JWT session management; no password or reCAPTCHA bypass."""
from __future__ import annotations
import asyncio
import time
from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .api import ContarinaApi, ContarinaAuthError
from .const import (
    CONF_ACCOUNT, CONF_TOKEN, KEEPALIVE_SKIP_IF_FRESHER_SECONDS, TOKEN_REFRESH_MARGIN_SECONDS,
)
from .models import ResponseShapeError, jwt_claims

class ContarinaSession:
    """Refresh JWT before expiry and immediately persist each replacement."""
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: ContarinaApi) -> None:
        self.hass = hass
        self.entry = entry
        self.api = api
        self._token = str(entry.data[CONF_TOKEN])
        self._lock = asyncio.Lock()

    @property
    def exp(self) -> int:
        try:
            return int(jwt_claims(self._token)["exp"])
        except (ResponseShapeError, ValueError, TypeError) as exc:
            raise ContarinaAuthError("SOL token is invalid") from exc

    async def ensure_valid(self, force: bool = False) -> str:
        """Return a usable token; refresh only when it is close to expiry (data calls)."""
        if not force and self.exp - int(time.time()) > TOKEN_REFRESH_MARGIN_SECONDS:
            return self._token
        async with self._lock:
            if not force and self.exp - int(time.time()) > TOKEN_REFRESH_MARGIN_SECONDS:
                return self._token
            return await self._refresh_locked()

    async def keepalive(self) -> str:
        """Unconditional periodic refresh: keeps remaining validity close to the full 55 min.

        SOL cannot renew an expired JWT (HTTP 401), so the downtime HA can survive
        equals the validity left at the moment it goes offline. Refreshing on every
        tick raises the worst case from ~25 min (margin-based) to ~45 min.
        """
        async with self._lock:
            if self.exp - int(time.time()) > KEEPALIVE_SKIP_IF_FRESHER_SECONDS:
                return self._token
            return await self._refresh_locked()

    async def _refresh_locked(self) -> str:
        if self.exp <= int(time.time()):
            raise ContarinaAuthError("SOL session expired; browser reauthentication required")
        new_token = await self.api.refresh(self._token)
        try:
            claims = jwt_claims(new_token)
        except ResponseShapeError as exc:
            raise ContarinaAuthError("SOL returned an invalid session") from exc
        if claims["exp"] <= int(time.time()):
            raise ContarinaAuthError("SOL returned an expired session")
        account = str(claims.get("crm_id") or claims.get("username") or "")
        if account != self.entry.data[CONF_ACCOUNT]:
            raise ContarinaAuthError("SOL account changed during refresh")
        self._token = new_token
        self.hass.config_entries.async_update_entry(
            self.entry, data={**self.entry.data, CONF_TOKEN: new_token},
        )
        return new_token

    async def call(self, method: str, *args: Any) -> Any:
        token = await self.ensure_valid()
        try:
            return await getattr(self.api, method)(*args, token=token)
        except ContarinaAuthError:
            token = await self.ensure_valid(force=True)
            return await getattr(self.api, method)(*args, token=token)
