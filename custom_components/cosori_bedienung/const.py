"""Konstanten für Cosori Bedienung."""

from __future__ import annotations

DOMAIN = "cosori_bedienung"
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

# Zonen der TwinFry
ZONE_1 = 1
ZONE_2 = 2
ZONE_WHOLE = 3  # ganze Schublade ohne Trennwand

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

# So lange zeigt der Schalter nach „Senden“ sofort An, bis die Fritteuse ihren Zustand meldet
SENT_OPTIMISTIC_SECONDS = 90

# Normalisierte Zustände (Schlüssel für die Übersetzungen)
STATE_OFF = "aus"
STATE_STANDBY = "bereit"
STATE_PREHEAT = "vorheizen"
STATE_PREHEATED = "vorgeheizt"
STATE_WAITING = "wartet_auf_start"
STATE_COOKING = "gart"
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
    STATE_PAUSED,
    STATE_DRAWER_OPEN,
    STATE_FINISHED,
    STATE_KEEP_WARM,
    STATE_OFFLINE,
    STATE_UNKNOWN,
]

ACTIVE_STATES = {STATE_PREHEAT, STATE_COOKING, STATE_PAUSED, STATE_DRAWER_OPEN}

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
