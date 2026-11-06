"""UI setup: browser JWT (pasted or delivered by the reconnect bookmarklet); no password or automated login."""
from __future__ import annotations
import re
import time
from datetime import date
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.components import http
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url
from .api import ContarinaApi, ContarinaAuthError, ContarinaConnectionError
from .const import (
    CONF_ACCOUNT, CONF_BILL_HOURS, CONF_CONDOS, CONF_CONTRACTS, CONF_HORIZON,
    CONF_POLL_HOURS, CONF_TOKEN, DEFAULT_BILL_HOURS, DEFAULT_HORIZON,
    DEFAULT_POLL_HOURS, DOMAIN,
)
from .models import ResponseShapeError, is_active, jwt_claims
from .pairing import START_PATH
from .reconnect import async_register_views, get_store

HEADER_FRONTEND_BASE = "HA-Frontend-Base"  # same source HA uses for OAuth2/Plex external steps


def _frontend_base(hass) -> str:
    """Absolute origin the user is browsing HA from (the frontend drops relative URLs)."""
    req = http.current_request.get()
    if req is not None:
        base = (req.headers.get(HEADER_FRONTEND_BASE) or "").rstrip("/")
        if re.fullmatch(r"https?://[^/?#@\s]+", base):
            return base
    return get_url(hass, allow_internal=True, allow_external=True, prefer_external=False).rstrip("/")


def _secret_selector():
    return selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))

class ContarinaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    def __init__(self) -> None:
        self._token: str | None = None
        self._account: str | None = None
        self._contracts: list[dict[str, Any]] = []
        self._target: config_entries.ConfigEntry | None = None
        self._success_reason = "reauth_successful"
        self._browser_error: str | None = None

    async def _check_token(self, token: str) -> tuple[str, list[dict[str, Any]]]:
        try:
            claims = jwt_claims(token)
        except ResponseShapeError as exc:
            raise ContarinaAuthError("Invalid JWT") from exc
        if claims["exp"] <= int(time.time()):
            raise ContarinaAuthError("JWT already expired")
        account = str(claims.get("crm_id") or claims.get("username") or "")
        if not account:
            raise ContarinaAuthError("No stable account identifier")
        api = ContarinaApi(async_get_clientsession(self.hass))
        contracts = await api.get_contracts(token)
        if not contracts:
            raise ContarinaConnectionError("SOL account has no contracts")
        return account, contracts

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            token = str(user_input[CONF_TOKEN]).strip()
            try:
                self._account, self._contracts = await self._check_token(token)
                self._token = token
                await self.async_set_unique_id(self._account)
                self._abort_if_unique_id_configured()
                return await self.async_step_contracts()
            except ContarinaAuthError:
                errors["base"] = "invalid_auth"
            except ContarinaConnectionError:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): _secret_selector()}),
            errors=errors,
        )

    async def async_step_contracts(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        refs = {str(x.get("reference_code")) for x in self._contracts if x.get("reference_code")}
        if user_input is not None:
            chosen = [str(x) for x in user_input[CONF_CONTRACTS]]
            if chosen and set(chosen) <= refs and self._token and self._account:
                return self.async_create_entry(
                    title="Contarina",
                    data={CONF_ACCOUNT: self._account, CONF_TOKEN: self._token, CONF_CONTRACTS: chosen},
                )
            errors["base"] = "invalid_contracts"
        options = []
        defaults = []
        for c in self._contracts:
            ref = str(c.get("reference_code") or "")
            if not ref:
                continue
            active = is_active(c, date.today())
            title = str(c.get("sol_contract_name") or c.get("name") or "Utenza")
            options.append(selector.SelectOptionDict(value=ref, label=f"{title} ({'attiva' if active else 'cessata'})"))
            if active:
                defaults.append(ref)
        return self.async_show_form(
            step_id="contracts",
            data_schema=vol.Schema({
                vol.Required(CONF_CONTRACTS, default=defaults): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options, multiple=True, mode=selector.SelectSelectorMode.DROPDOWN,
                    ),
                )
            }),
            errors=errors,
        )

    # ------------------------------------------------------------- reauth / reconnect
    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        self._target = self._get_reauth_entry()
        self._success_reason = "reauth_successful"
        return await self.async_step_reauth_confirm()

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """'Riconfigura' in the integration settings: reconnect at any time."""
        self._target = self._get_reconfigure_entry()
        self._success_reason = "reconfigure_successful"
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="reauth_confirm", menu_options=["reconnect_browser", "reconnect_paste"],
        )

    async def _validate_for_target(self, token: str) -> str | None:
        """Return an error key, or None if the token is valid for the configured account."""
        assert self._target is not None
        try:
            account, _ = await self._check_token(token)
        except ContarinaAuthError:
            return "invalid_auth"
        except ContarinaConnectionError:
            return "cannot_connect"
        if account != self._target.unique_id:
            return "wrong_account"
        return None

    async def async_step_reconnect_browser(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """External step: HA opens the start page; the receive view feeds the token back here."""
        assert self._target is not None
        store = get_store(self.hass)
        if user_input is None:
            try:
                base = _frontend_base(self.hass)
            except NoURLAvailableError:
                self._browser_error = "no_url"
                return await self.async_step_reconnect_paste()
            async_register_views(self.hass)
            state = store.create(self.flow_id, self._target.entry_id)
            return self.async_external_step(
                step_id="reconnect_browser",
                url=f"{base}{START_PATH}?flow_id={self.flow_id}&state={state}",
            )
        token = str(user_input.get(CONF_TOKEN, "")).strip()
        error = await self._validate_for_target(token)
        store.set_outcome(self.flow_id, error or "ok")
        if error:
            self._browser_error = error
            return self.async_external_step_done(next_step_id="reconnect_paste")
        # Persist now (no reload: reloading here would abort this very reauth flow).
        # The token is saved even if the HA dialog was closed; reload happens in the next step.
        self.hass.config_entries.async_update_entry(
            self._target, data={**self._target.data, CONF_TOKEN: token},
        )
        return self.async_external_step_done(next_step_id="reconnect_done")

    async def async_step_reconnect_done(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._target is not None
        return self.async_update_reload_and_abort(self._target, reason=self._success_reason)

    async def async_step_reconnect_paste(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._target is not None
        errors: dict[str, str] = {}
        if self._browser_error:
            errors["base"] = self._browser_error
            self._browser_error = None
        if user_input is not None:
            token = str(user_input[CONF_TOKEN]).strip()
            error = await self._validate_for_target(token)
            if error is None:
                return self.async_update_reload_and_abort(
                    self._target, data_updates={CONF_TOKEN: token}, reason=self._success_reason,
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reconnect_paste",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): _secret_selector()}),
            errors=errors,
        )

    @callback
    def async_remove(self) -> None:
        """Flow closed or finished: drop any pending one-time state."""
        get_store(self.hass).discard(self.flow_id)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> ContarinaOptionsFlow:
        return ContarinaOptionsFlow()

class ContarinaOptionsFlow(config_entries.OptionsFlowWithReload):
    """Options change -> automatic single reload (no update listener)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        current = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_HORIZON, default=current.get(CONF_HORIZON, DEFAULT_HORIZON)):
                    vol.All(vol.Coerce(int), vol.Range(min=7, max=366)),
                vol.Required(CONF_POLL_HOURS, default=current.get(CONF_POLL_HOURS, DEFAULT_POLL_HOURS)):
                    vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
                vol.Required(CONF_BILL_HOURS, default=current.get(CONF_BILL_HOURS, DEFAULT_BILL_HOURS)):
                    vol.All(vol.Coerce(int), vol.Range(min=6, max=48)),
                vol.Required(CONF_CONDOS, default=current.get(CONF_CONDOS, False)): bool,
            }),
        )
