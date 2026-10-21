"""Einrichtung über die Oberfläche (Geräte & Dienste → Integration hinzufügen)."""

from __future__ import annotations

import logging
import secrets
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .core.api import AirfryerApi, AirfryerAuthError, AirfryerError, hash_password, is_air_fryer
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD_HASH,
    CONF_REGION,
    CONF_TERMINAL_ID,
    DEFAULT_INTERVAL,
    DOMAIN,
    MAX_INTERVAL,
    MIN_INTERVAL,
    OPT_INTERVAL,
    OPT_SIDEBAR,
    OPT_TIME_UNIT,
    REGIONS,
    TIME_UNIT_AUTO,
    TIME_UNIT_MINUTES,
    TIME_UNIT_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

PASSWORD = "passwort"


def _user_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_EMAIL, default=defaults.get(CONF_EMAIL, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
            ),
            vol.Required(PASSWORD): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
            ),
            vol.Required(CONF_REGION, default=defaults.get(CONF_REGION, "eu")): SelectSelector(
                SelectSelectorConfig(
                    options=REGIONS,
                    mode=SelectSelectorMode.LIST,
                    translation_key="region",
                )
            ),
        }
    )


class AirfryerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtungs-Assistent."""

    VERSION = 1

    async def _check(
        self, email: str, password_md5: str, region: str, terminal_id: str
    ) -> tuple[dict[str, str], int]:
        """Anmelden und Fritteusen zählen. Gibt (Fehler, Anzahl) zurück."""
        api = AirfryerApi(
            async_get_clientsession(self.hass), email, password_md5, region, terminal_id
        )
        try:
            await api.login()
            devices = await api.get_devices()
        except AirfryerAuthError:
            return {"base": "anmeldung_falsch"}, 0
        except AirfryerError as err:
            _LOGGER.warning("Einrichtung: %s", err)
            return {"base": "keine_verbindung"}, 0
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unerwarteter Fehler bei der Einrichtung")
            return {"base": "unbekannt"}, 0
        count = sum(1 for d in devices if is_air_fryer(d))
        if count == 0:
            return {"base": "keine_fritteuse"}, 0
        return {}, count

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            await self.async_set_unique_id(email.lower())
            self._abort_if_unique_id_configured()
            password_md5 = hash_password(user_input[PASSWORD])
            terminal_id = secrets.token_hex(16).upper()
            errors, _count = await self._check(
                email, password_md5, user_input[CONF_REGION], terminal_id
            )
            if not errors:
                return self.async_create_entry(
                    title=email,
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD_HASH: password_md5,
                        CONF_REGION: user_input[CONF_REGION],
                        CONF_TERMINAL_ID: terminal_id,
                    },
                )
        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            password_md5 = hash_password(user_input[PASSWORD])
            errors, _count = await self._check(
                entry.data[CONF_EMAIL],
                password_md5,
                entry.data[CONF_REGION],
                entry.data[CONF_TERMINAL_ID],
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD_HASH: password_md5}
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            description_placeholders={"email": entry.data[CONF_EMAIL]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return AirfryerOptionsFlow()


class AirfryerOptionsFlow(OptionsFlow):
    """Konfigurieren: Abfrage-Takt und Zeiteinheit."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            user_input[OPT_INTERVAL] = int(user_input[OPT_INTERVAL])
            user_input[OPT_SIDEBAR] = bool(user_input.get(OPT_SIDEBAR, False))
            return self.async_create_entry(data=user_input)
        opts = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    OPT_INTERVAL, default=opts.get(OPT_INTERVAL, DEFAULT_INTERVAL)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_INTERVAL,
                        max=MAX_INTERVAL,
                        step=10,
                        unit_of_measurement="s",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    OPT_TIME_UNIT, default=opts.get(OPT_TIME_UNIT, TIME_UNIT_AUTO)
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[TIME_UNIT_AUTO, TIME_UNIT_SECONDS, TIME_UNIT_MINUTES],
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="zeiteinheit",
                    )
                ),
                vol.Optional(OPT_SIDEBAR, default=bool(opts.get(OPT_SIDEBAR, False))): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
