"""Modellprofile: welche Programme und Grenzen hat welche Fritteuse?

Für Doofe: Cosori verrät nicht, was ein Modell kann. Darum steht hier je
Modellfamilie, welche Programme es gibt, welche Temperaturen erlaubt sind und
welche Werte beim Programmwechsel vorgeschlagen werden.

- TwinFry (CAF-TF101S/TF102S): von Marco in der VeSync-App abgelesen (wie bisher).
- Turbo Tower Pro (CAF-DC111S): Angaben des Besitzers Bhomas86 (Issue #5),
  inklusive Gären (Proof, 30–45 °C in 1-°C-Schritten). Zeitgrenzen und Gären
  sind noch nicht über die Schnittstelle getestet.
- Dual Blaze CAF-P583S (ein Korb): Programme, Grenzen und Rezept-Nummern aus
  pyvesync (device_map.py, aus der VeSync-App gelesen). Sie versteht nicht
  `startMultiCook`, sondern `startCook` (siehe senden.py). Getestet von mexx111.
- Alles andere: wie die TwinFry (geschätzt).
"""

from __future__ import annotations

from .const import MODE_DEFAULTS, MODE_TEMP_RANGE, MODE_TIME_RANGE, MODES, TEMP_MAX_DEFAULT, TEMP_MIN_DEFAULT, TIME_MAX_DEFAULT, TIME_MIN_DEFAULT

TWINFRY_PREFIXES = ("CAF-TF101S", "CAF-TF102S")
TURBO_TOWER_PREFIXES = ("CAF-DC111S",)
DUAL_BLAZE_PREFIXES = ("CAF-P583S",)

# 🔢 Rezept-Nummer und -Name je Programm, so wie die VeSync-App sie schickt
# (Quelle: pyvesync device_map.py – vorher war außer Heißluft alles geraten)
RECIPES = {
    "airfry": (14, "Air Fry"),
    "roast": (13, "Roast"),
    "bake": (9, "Bake"),
    "grill": (20, "Grill"),
    "reheat": (16, "Reheat"),
    "dry": (21, "Dry"),
    "proof": (27, "Proof"),
    "broil": (17, "Broil"),
    "chicken": (2, "Chicken"),
    "steak": (1, "Steak"),
    "seafood": (3, "Seafood"),
    "veggies": (15, "Veggies"),
    "fries": (6, "French Fries"),
    "frozen": (5, "Frozen"),
}

# 🍗 Dual Blaze CAF-P583S: ein Korb, eigene Programme (Auswahl → Name, den die App schickt)
DUAL_BLAZE_MODES = {
    "airfry": "AirFry",
    "broil": "Broil",
    "roast": "Roast",
    "bake": "Bake",
    "chicken": "Chicken",
    "steak": "Steak",
    "seafood": "Seafood",
    "veggies": "Veggies",
    "fries": "French fries",  # so schreibt es die App (mit Leerzeichen, klein)
    "frozen": "Frozen",
    "reheat": "Reheat",
}

# Alle Programme, die irgendein Modell kennt (für die Dienst-Prüfung)
ALL_MODES = {**MODES, "proof": "Proof", **DUAL_BLAZE_MODES}

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
DUAL_BLAZE = {
    "modes": dict(DUAL_BLAZE_MODES),
    "temp": {
        "airfry": (80, 205),
        "broil": (175, 205),
        "roast": (80, 205),
        "bake": (120, 205),
        "chicken": (175, 205),
        "steak": (80, 205),
        "seafood": (160, 205),
        "veggies": (160, 205),
        "fries": (175, 205),
        "frozen": (175, 205),
        "reheat": (150, 205),
    },
    # ⚠️ Zeitgrenzen nennt pyvesync nicht – wie in der App bis 60 Minuten geschätzt
    "time": {mode: (1, 60) for mode in DUAL_BLAZE_MODES},
    "defaults": {
        "airfry": (180, 10),
        "broil": (205, 10),
        "roast": (205, 10),
        "bake": (160, 20),
        "chicken": (200, 20),
        "steak": (205, 8),
        "seafood": (190, 8),
        "veggies": (195, 6),
        "fries": (195, 20),
        "frozen": (200, 12),
        "reheat": (175, 5),
    },
    "step": {},
}
PROFILES = {"twinfry": TWINFRY, "turbotower": TURBO_TOWER, "dualblaze": DUAL_BLAZE}
TEMP_STEP_DEFAULT = 5


def model_family(model: str | None) -> str | None:
    """„twinfry“, „turbotower“, „dualblaze“ – oder None (unbekannt, dann gelten die TwinFry-Werte)."""
    m = str(model or "").upper()
    if m.startswith(DUAL_BLAZE_PREFIXES):
        return "dualblaze"
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


def recipe(mode: str) -> tuple[int, str]:
    """Rezept-Nummer und -Name für ein Programm (unbekannt = Heißluft-Nummer, Programm-Name)."""
    return RECIPES.get(mode, (14, ALL_MODES.get(mode, mode)))


def has_zones(model: str | None) -> bool:
    """Hat dieses Modell sicher mehrere Zonen? (TwinFry: ja, auch wenn sie beim Start schweigt)"""
    return model_family(model) == "twinfry"


def one_drawer(model: str | None) -> bool:
    """Eine Schublade für alle Zonen (TwinFry: Trennwand rein = Zone 1/2, raus = Grandzone).

    Beim Turbo Tower Pro sind es zwei echte Schubladen übereinander – dort nie.
    """
    return model_family(model) == "twinfry"


def single_basket(model: str | None) -> bool:
    """Ein-Korb-Modell mit eigenem Befehl „startCook“ (Dual Blaze CAF-P583S)."""
    return model_family(model) == "dualblaze"
