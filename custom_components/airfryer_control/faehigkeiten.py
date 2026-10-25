"""Was weiß Airfryer Control über ein Modell – und wie sicher?

Für Doofe: Cosori verrät nicht, welche Programme und Grenzen ein Modell hat.
Die Werte hier hat Marco an seiner TwinFry aus der VeSync-App abgelesen. Für
andere Modelle sind sie nur geschätzt. Diese Liste sagt darum ehrlich dazu,
was bestätigt ist und was nicht – damit andere Karten oder Integrationen
nichts Ungeprüftes als sicher anbieten.
"""

from __future__ import annotations

from typing import Any

from .const import MODE_DEFAULTS, MODES
from .coordinator import FryerData
from .core.parser import zones_for_device
from .senden import temp_limits, time_limits

# Modelle, an denen die Grenzen aus der VeSync-App abgelesen wurden
TWINFRY_PREFIXES = ("CAF-TF101S", "CAF-TF102S")
# Programme, bei denen „Senden“ an einer echten Fritteuse bestätigt ist (je Modellfamilie)
SEND_CONFIRMED = {"twinfry": {"airfry"}}

SOURCE_APP = "vesync_app"  # an diesem Modell in der App abgelesen
SOURCE_GUESS = "geschaetzt"  # von der TwinFry übernommen, nicht geprüft
SEND_OK = "bestaetigt"
SEND_UNCHECKED = "ungeprueft"


def model_family(model: str) -> str | None:
    """„twinfry“ für die Dual Blaze TwinFry, sonst None (unbekannt)."""
    if model.upper().startswith(TWINFRY_PREFIXES):
        return "twinfry"
    return None


def capabilities(fryer: FryerData) -> dict[str, Any]:
    """Programme, Grenzen und Zonen eines Geräts – mit Angabe, wie sicher sie sind."""
    family = model_family(fryer.model)
    confirmed = SEND_CONFIRMED.get(family or "", set())
    programs: dict[str, Any] = {}
    for mode in MODES:
        temp, minutes = MODE_DEFAULTS[mode]
        programs[mode] = {
            "temperatur": list(temp_limits(mode)),
            "minuten": list(time_limits(mode)),
            "vorschlag": {"temperatur": temp, "minuten": minutes},
            "grenzen": SOURCE_APP if family else SOURCE_GUESS,
            "senden": SEND_OK if mode in confirmed else SEND_UNCHECKED,
        }
    zones = zones_for_device(fryer.state, fryer.multizone) or [1]
    return {
        "geraet": fryer.name,
        "modell": fryer.model,
        "modell_bekannt": family is not None,
        "zonen": zones,
        "programme": programs,
    }


def outside_limits(mode: str, temp: int, minutes: int) -> dict[str, Any] | None:
    """Liegen Temperatur oder Zeit außerhalb der Grenzen? Dann die Grenzen zurückgeben."""
    t_low, t_high = temp_limits(mode)
    m_low, m_high = time_limits(mode)
    if t_low <= temp <= t_high and m_low <= minutes <= m_high:
        return None
    return {"temperatur": [t_low, t_high], "minuten": [m_low, m_high]}
