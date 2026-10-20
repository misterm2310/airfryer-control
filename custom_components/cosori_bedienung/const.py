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
SERVICE_START = "garen_starten"
SERVICE_STOP = "garen_beenden"
SERVICE_RAW = "befehl_senden"

# Zonen der TwinFry
ZONE_1 = 1
ZONE_2 = 2
ZONE_WHOLE = 3  # ganze Schublade ohne Trennwand

# Garprogramme, wie die App sie nennt
# Auswahl im Dienst (klein geschrieben) → Name, den die App schickt
MODES = {
    "airfry": "AirFry",
    "roast": "Roast",
    "bake": "Bake",
    "broil": "Broil",
    "reheat": "Reheat",
    "dehydrate": "Dehydrate",
    "preheat": "Preheat",
}

# Normalisierte Zustände (Schlüssel für die Übersetzungen)
STATE_OFF = "aus"
STATE_STANDBY = "bereit"
STATE_PREHEAT = "vorheizen"
STATE_PREHEATED = "vorgeheizt"
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
