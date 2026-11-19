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
OPT_SHAKE = "schuettel_erinnerung"  # ALT (bis 1.0.5-beta.3): Schüttel-Erinnerung an/aus – wird beim Start auf die Knöpfe pro Zone übertragen
OPT_NOTIFY = "melden_an"  # 📲 notify-Dienste ohne „notify.“ (z. B. mobile_app_marco) – leer = aus
OPT_NOTIFY_SHAKE = "melden_schuetteln"  # 📲 „↕️ Jetzt schütteln!“ auch aufs Handy (Standard: aus)
NOTIFY_MAX = 10  # höchstens so viele Handys
OPT_SHAKE_EVERY = "schuettel_takt"  # ALT (bis 1.0.5-beta.3): 0 = Halbzeit, sonst alle X Minuten – wird übertragen
SHAKE_EVERY_MAX = 30
# ↕️ Schütteln pro Zone (Knopf bei der Programm-Auswahl): None = aus, 0 = zur Halbzeit, X = alle X Minuten
SHAKE_HALF = 0
SHAKE_CHOICES = (None, 0, 3, 5, 8)  # was der Knopf in der Karte anbietet
OPT_FORGOT = "start_vergessen"  # ⏰ Hinweis, wenn eine Zone so viele Minuten auf Start wartet (0 = aus, Standard 10)
DEFAULT_FORGOT = 10
FORGOT_MAX = 60
OPT_NOTIFY_FORGOT = "melden_vergessen"  # 📲 „Vergessen zu starten?“ auch aufs Handy (Standard: an, nur mit Handys)

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
# Ereignis zur Halbzeit: „jetzt schütteln“ (nur wenn die Schüttel-Erinnerung an ist)
EVENT_SHAKE = f"{DOMAIN}_schuetteln"
SHAKE_MIN_SECONDS = 120  # bei ganz kurzen Garzeiten (unter 2 Minuten) lohnt Schütteln nicht
SHAKE_LAST_SECONDS = 60  # ↕️ in der letzten Minute wird nicht mehr erinnert (lohnt nicht mehr)
SHAKE_SHOW_SECONDS = 180  # ↕️ so lange steht „Jetzt schütteln!“ in Karte und Laufband (Schublade auf = sofort weg)
# Ereignis: Zone wartet schon lange auf Start am Gerät („Vergessen zu starten?“)
EVENT_FORGOT = f"{DOMAIN}_start_vergessen"
INHALT_MAX = 40  # 🏷️ „Was ist drin?“ – höchstens so viele Zeichen

# Dienste
SERVICE_SEND_TEST = "senden_testen"
SERVICE_STOP = "garen_beenden"
SERVICE_RAW = "befehl_senden"
SERVICE_PROGRAM = "programm_senden"
SERVICE_MATCH = "match_senden"
SERVICE_SYNC = "sync_senden"
SERVICE_CAPABILITIES = "faehigkeiten"
SERVICE_FAV_SAVE = "liebling_speichern"
SERVICE_FAV_DELETE = "liebling_loeschen"
SERVICE_ADD_TIME = "garzeit_plus"
SERVICE_CONTENT = "inhalt_setzen"
SERVICE_SHAKE = "schuetteln_setzen"

# ⭐ Lieblings-Programme und 🕘 zuletzt gesendet (pro Fritteuse)
MAX_FAVORITES = 12
MAX_RECENT = 5

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
OPT_MASCOT = "maskottchen"  # 🍟 Maskottchen in der Seitenleisten-Ansicht (Standard: aus)
