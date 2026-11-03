"""Modellprofile: welche Programme und Grenzen hat welche Fritteuse?

Für Doofe: Cosori verrät nicht, was ein Modell kann. Darum steht hier je
Modellfamilie, welche Programme es gibt, welche Temperaturen erlaubt sind und
welche Werte beim Programmwechsel vorgeschlagen werden.

- TwinFry (CAF-TF101S/TF102S): von Marco in der VeSync-App abgelesen (wie bisher).
- Turbo Tower Pro (CAF-DC111S): Angaben des Besitzers Bhomas86 (Issue #5),
  inklusive Gären (Proof, 30–45 °C in 1-°C-Schritten). Zeitgrenzen und Gären
  sind noch nicht über die Schnittstelle getestet.
- Alles andere: wie die TwinFry (geschätzt).
"""

from __future__ import annotations

from .const import MODE_DEFAULTS, MODE_TEMP_RANGE, MODE_TIME_RANGE, MODES, TEMP_MAX_DEFAULT, TEMP_MIN_DEFAULT, TIME_MAX_DEFAULT, TIME_MIN_DEFAULT

TWINFRY_PREFIXES = ("CAF-TF101S", "CAF-TF102S")
TURBO_TOWER_PREFIXES = ("CAF-DC111S",)

# Alle Programme, die irgendein Modell kennt (für die Dienst-Prüfung)
ALL_MODES = {**MODES, "proof": "Proof"}

# 🗼 Turbo Tower Pro Smart: eigene Grenzen je Programm (Angabe des Besitzers)
TURBO_TOWER = {
    "modes": {**MODES, "proof": "Proof"},
    "temp": {
        "airfry": (120, 230),
        "roast": (175, 230),
        "bake": (80, 205),
        "grill": (160, 230),
        "reheat": (40, 205),
        "dry": (35, 95),
        "proof": (30, 45),
    },
    "time": {**MODE_TIME_RANGE, "proof": (1, 720)},  # ⚠️ Gären-Zeit geschätzt (bis 12 h)
    "defaults": {**MODE_DEFAULTS, "grill": (230, 5), "proof": (35, 60)},
    "step": {"proof": 1},
}
TWINFRY = {
    "modes": dict(MODES),
    "temp": dict(MODE_TEMP_RANGE),
    "time": dict(MODE_TIME_RANGE),
    "defaults": dict(MODE_DEFAULTS),
    "step": {},
}
PROFILES = {"twinfry": TWINFRY, "turbotower": TURBO_TOWER}
TEMP_STEP_DEFAULT = 5


def model_family(model: str | None) -> str | None:
    """„twinfry“, „turbotower“ – oder None (unbekannt, dann gelten die TwinFry-Werte)."""
    m = str(model or "").upper()
    if m.startswith(TWINFRY_PREFIXES):
        return "twinfry"
    if m.startswith(TURBO_TOWER_PREFIXES):
        return "turbotower"
    return None


def profile(model: str | None) -> dict:
    """Das Profil eines Modells (unbekannt = TwinFry)."""
    return PROFILES.get(model_family(model) or "twinfry", TWINFRY)


def modes_for(model: str | None) -> dict[str, str]:
    """Programme dieses Modells: Auswahl → Name, den die App schickt."""
    return profile(model)["modes"]


def temp_limits(mode: str, model: str | None = None) -> tuple[int, int]:
    """Erlaubter Temperaturbereich (°C) für ein Programm an diesem Modell."""
    return profile(model)["temp"].get(mode, (TEMP_MIN_DEFAULT, TEMP_MAX_DEFAULT))


def time_limits(mode: str, model: str | None = None) -> tuple[int, int]:
    """Erlaubte Garzeit (Minuten) für ein Programm an diesem Modell."""
    return profile(model)["time"].get(mode, (TIME_MIN_DEFAULT, TIME_MAX_DEFAULT))


def temp_step(mode: str, model: str | None = None) -> int:
    """Schrittweite der Temperatur (Gären: 1 °C, sonst 5 °C)."""
    return profile(model)["step"].get(mode, TEMP_STEP_DEFAULT)


def mode_default(mode: str, model: str | None = None) -> tuple[int, int]:
    """Vorschlag (Temperatur °C, Minuten) beim Programmwechsel."""
    return profile(model)["defaults"].get(mode, MODE_DEFAULTS.get(mode, (180, 10)))
