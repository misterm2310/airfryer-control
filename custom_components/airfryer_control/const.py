"""Konstanten für Airfryer Control."""

from __future__ import annotations

DOMAIN = "airfryer_control"
MANUFACTURER = "Cosori"

# Einstellungen im Config-Eintrag
CONF_EMAIL = "email"
CONF_PASSWORD_HASH = "password_md5"  # nur der MD5-Wert, nie das Klartext-Passwort
CONF_REGION = "region"
CONF_TERMINAL_ID = "terminal_id"

# Optionen
OPT_INTERVAL = "intervall"
OPT_TIME_UNIT = "zeiteinheit"

DEFAULT_INTERVAL = 60  # Sekunden, wenn die Fritteuse nichts tut
FAST_INTERVAL = 15  # Sekunden, solange sie arbeitet
WAITING_INTERVAL = 5  # Sekunden, solange eine Zone auf „Start“ am Gerät wartet
MIN_INTERVAL = 30
MAX_INTERVAL = 600

TIME_UNIT_AUTO = "auto"
TIME_UNIT_SECONDS = "sekunden"
TIME_UNIT_MINUTES = "minuten"

REGIONS = ["eu", "us"]

# Ereignis, wenn ein Garvorgang fertig ist
EVENT_FINISHED = f"{DOMAIN}_fertig"

# Dienste
SERVICE_SEND_TEST = "senden_testen"
SERVICE_STOP = "garen_beenden"
SERVICE_RAW = "befehl_senden"
SERVICE_PROGRAM = "programm_senden"
SERVICE_MATCH = "match_senden"
SERVICE_SYNC = "sync_senden"
SERVICE_CAPABILITIES = "faehigkeiten"

# Zonen der TwinFry
ZONE_1 = 1
ZONE_2 = 2
ZONE_WHOLE = 3  # ganze Schublade ohne Trennwand

def zone_label(language: str | None, zone: int) -> str:
    """Name der Zone für Entitäten: „Zone 1“, „Zone 2“, „Grandzone“."""
    if zone == ZONE_WHOLE:
        return "Grandzone"
    return f"Zone {zone}"


# Garprogramme der TwinFry, so wie die Fritteuse sie selbst meldet (getPresetRecipe)
# Auswahl (klein geschrieben) → Name, den die App schickt
MODES = {
    "airfry": "AirFry",
    "roast": "Roast",
    "bake": "Bake",
    "grill": "Grill",
    "reheat": "Reheat",
    "dry": "Dry",
}

# Vorschlagswerte der Fritteuse je Programm: (Temperatur °C, Minuten)
MODE_DEFAULTS = {
    "airfry": (200, 20),
    "roast": (190, 30),
    "bake": (180, 6),
    "grill": (240, 5),
    "reheat": (70, 60),
    "dry": (55, 360),
}
DEFAULT_MODE = "airfry"

# Temperaturbereich je Programm (°C), von Marco aus der VeSync-App abgelesen.
MODE_TEMP_RANGE = {
    "airfry": (120, 205),
    "roast": (120, 205),
    "bake": (80, 205),
    "grill": (205, 240),
    "reheat": (40, 205),
    "dry": (34, 95),
}
# Garzeit je Programm (Minuten), von Marco aus der VeSync-App angegeben.
MODE_TIME_RANGE = {
    "airfry": (1, 60),
    "roast": (1, 240),
    "bake": (1, 240),
    "grill": (1, 30),
    "reheat": (1, 60),
    "dry": (1, 2880),
}
TIME_MIN_DEFAULT = 1
TIME_MAX_DEFAULT = 2880
TEMP_MIN_DEFAULT = 35
TEMP_MAX_DEFAULT = 240

# Code der Fritteuse: „Wert nicht erlaubt“ (Temperatur oder Zeit passt nicht zum Programm)
CODE_VALUE_NOT_ALLOWED = 11011000

# So lange zeigt der Schalter nach „Senden“ sofort An, bis die Fritteuse ihren Zustand meldet
SENT_OPTIMISTIC_SECONDS = 90

# Normalisierte Zustände (Schlüssel für die Übersetzungen)
STATE_OFF = "aus"
STATE_STANDBY = "bereit"
STATE_PREHEAT = "vorheizen"
STATE_PREHEATED = "vorgeheizt"
STATE_WAITING = "wartet_auf_start"
STATE_COOKING = "gart"
STATE_HOLD = "wartet_auf_sync"  # Sync: diese Zone wartet, bis die längere Zone dran ist
STATE_PAUSED = "pausiert"
STATE_DRAWER_OPEN = "schublade_offen"
STATE_FINISHED = "fertig"
STATE_KEEP_WARM = "warmhalten"
STATE_OFFLINE = "offline"
STATE_UNKNOWN = "unbekannt"

ALL_STATES = [
    STATE_OFF,
    STATE_STANDBY,
    STATE_PREHEAT,
    STATE_PREHEATED,
    STATE_WAITING,
    STATE_COOKING,
    STATE_HOLD,
    STATE_PAUSED,
    STATE_DRAWER_OPEN,
    STATE_FINISHED,
    STATE_KEEP_WARM,
    STATE_OFFLINE,
    STATE_UNKNOWN,
]

ACTIVE_STATES = {STATE_PREHEAT, STATE_COOKING, STATE_HOLD, STATE_PAUSED, STATE_DRAWER_OPEN}

# Diese Felder verraten Konto oder Gerät – sie werden überall geschwärzt
REDACT_KEYS = {
    "token",
    "accountID",
    "accountId",
    "accountid",
    "cid",
    "uuid",
    "macID",
    "mac",
    "email",
    "password",
    "password_md5",
    "terminal_id",
    "terminalId",
    "deviceImg",
    "imageUrl",
    "ssid",
    "ip",
    "wifiName",
}

# Karte, die die Integration selbst ins Dashboard bringt
STATIC_URL = "/airfryer_control_files"
CARD_FILENAME = "airfryer-control-card.js"
PANEL_URL_PATH = "airfryer-control"
PANEL_FILENAME = "airfryer-control-panel.js"
OPT_SIDEBAR = "sidebar"  # Eintrag in der Seitenleiste (Standard: aus)
