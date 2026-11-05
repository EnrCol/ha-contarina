"""UI setup: user pastes one browser JWT; no password or automated login."""
from __future__ import annotations
import time
from datetime import date
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import ContarinaApi, ContarinaAuthError, ContarinaConnectionError
from .const import (
    CONF_ACCOUNT, CONF_BILL_HOURS, CONF_CONDOS, CONF_CONTRACTS, CONF_HORIZON,
    CONF_POLL_HOURS, CONF_TOKEN, DEFAULT_BILL_HOURS, DEFAULT_HORIZON,
    DEFAULT_POLL_HOURS, DOMAIN,
)
from .models import ResponseShapeError, is_active, jwt_claims

def _secret_selector():
    return selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))

class ContarinaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    def __init__(self) -> None:
        self._token: str | None = None
        self._account: str | None = None
        self._contracts: list[dict[str, Any]] = []

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

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            token = str(user_input[CONF_TOKEN]).strip()
            try:
                account, _ = await self._check_token(token)
                await self.async_set_unique_id(account)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data_updates={CONF_TOKEN: token},
                )
            except ContarinaAuthError:
                errors["base"] = "invalid_auth"
            except ContarinaConnectionError:
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): _secret_selector()}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> ContarinaOptionsFlow:
        return ContarinaOptionsFlow()

class ContarinaOptionsFlow(config_entries.OptionsFlow):
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
