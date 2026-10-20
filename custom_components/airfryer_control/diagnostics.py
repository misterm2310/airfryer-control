"""„Diagnose herunterladen“ – ohne E-Mail, Passwort, Token und Gerätekennungen."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import AirfryerCoordinator
from .core.util import redact


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: AirfryerCoordinator = entry.runtime_data
    fryers = []
    for fryer in coordinator.fryers.values():
        state = fryer.state
        fryers.append(
            {
                "modell": fryer.model,
                "config_module": fryer.info.get("configModule"),
                "online": fryer.online,
                "mehrzonen": fryer.multizone,
                "letzter_fehler": fryer.last_error,
                "erkannt": {
                    "zustand": state.status,
                    "rohwert": state.status_raw,
                    "restzeit_s": state.remaining_s,
                    "zonen": {
                        str(z): {
                            "zustand": zs.status,
                            "rohwert": zs.status_raw,
                            "restzeit_s": zs.remaining_s,
                            "sollzeit_s": zs.set_time_s,
                            "solltemperatur": zs.set_temp,
                            "temperatur": zs.current_temp,
                            "programm": zs.mode,
                        }
                        for z, zs in state.zones.items()
                    },
                },
                "geraet_info": redact(fryer.info),
                "roh_status": redact(fryer.raw_status),
                "roh_mehrzonen": redact(fryer.raw_multi),
            }
        )
    return {
        "region": entry.data.get("region"),
        "optionen": dict(entry.options),
        "fritteusen": fryers,
    }
