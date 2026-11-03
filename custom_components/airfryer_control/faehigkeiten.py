"""Was weiß Airfryer Control über ein Modell – und wie sicher?

Für Doofe: Cosori verrät nicht, welche Programme und Grenzen ein Modell hat.
Die Werte für die TwinFry hat Marco aus der VeSync-App abgelesen, die für die
Turbo Tower Pro (CAF-DC111S) hat ihr Besitzer genannt (siehe modelle.py). Für
andere Modelle sind sie nur geschätzt. Diese Liste sagt darum ehrlich dazu,
was bestätigt ist und was nicht – damit andere Karten oder Integrationen
nichts Ungeprüftes als sicher anbieten.
"""

from __future__ import annotations

from typing import Any

from .coordinator import FryerData
from .core.parser import zones_for_device
from .modelle import TWINFRY_PREFIXES, mode_default, model_family, modes_for, temp_step
from .senden import temp_limits, time_limits

# Programme, bei denen „Senden“ an einer echten Fritteuse bestätigt ist (je Modellfamilie)
SEND_CONFIRMED = {"twinfry": {"airfry"}}

SOURCE_APP = "vesync_app"  # an diesem Modell in der App abgelesen
SOURCE_OWNER = "besitzer"  # vom Besitzer des Modells genannt, noch nicht über die Schnittstelle getestet
SOURCE_GUESS = "geschaetzt"  # von der TwinFry übernommen, nicht geprüft
SOURCE_BY_FAMILY = {"twinfry": SOURCE_APP, "turbotower": SOURCE_OWNER}
__all__ = ["TWINFRY_PREFIXES", "capabilities", "model_family", "outside_limits"]
SEND_OK = "bestaetigt"
SEND_UNCHECKED = "ungeprueft"


def capabilities(fryer: FryerData) -> dict[str, Any]:
    """Programme, Grenzen und Zonen eines Geräts – mit Angabe, wie sicher sie sind."""
    family = model_family(fryer.model)
    confirmed = SEND_CONFIRMED.get(family or "", set())
    programs: dict[str, Any] = {}
    for mode in modes_for(fryer.model):
        temp, minutes = mode_default(mode, fryer.model)
        programs[mode] = {
            "temperatur": list(temp_limits(mode, fryer.model)),
            "temperatur_schritt": temp_step(mode, fryer.model),
            "minuten": list(time_limits(mode, fryer.model)),
            "vorschlag": {"temperatur": temp, "minuten": minutes},
            "grenzen": SOURCE_BY_FAMILY.get(family or "", SOURCE_GUESS),
            "senden": SEND_OK if mode in confirmed else SEND_UNCHECKED,
        }
    zones = zones_for_device(fryer.state, fryer.multizone) or [1]
    return {
        "geraet": fryer.name,
        "modell": fryer.model,
        "modell_bekannt": family is not None,
        "modellfamilie": family,
        "zonen": zones,
        "programme": programs,
    }


def outside_limits(mode: str, temp: int, minutes: int, model: str | None = None) -> dict[str, Any] | None:
    """Liegen Temperatur oder Zeit außerhalb der Grenzen dieses Modells? Dann die Grenzen zurückgeben."""
    t_low, t_high = temp_limits(mode, model)
    m_low, m_high = time_limits(mode, model)
    if t_low <= temp <= t_high and m_low <= minutes <= m_high:
        return None
    return {"temperatur": [t_low, t_high], "minuten": [m_low, m_high]}
