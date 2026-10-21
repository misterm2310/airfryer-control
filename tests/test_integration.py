"""Tests mit einem echten (Test-)Home-Assistant und einer Attrappe der Cloud."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.airfryer_control.core.api import (
    AirfryerAuthError,
    AirfryerDeviceOffline,
    AirfryerError,
    hash_password,
)
from custom_components.airfryer_control.const import DOMAIN, EVENT_FINISHED
from custom_components.airfryer_control.diagnostics import (
    async_get_config_entry_diagnostics,
)

CID = "geheime-cid-123"
DEVICE = {
    "cid": CID,
    "uuid": "geheime-uuid",
    "deviceType": "CAF-TF101S-AEUR",
    "deviceName": "Fritteuse",
    "configModule": "WiFi_AirFryer_CAF-TF101S_EU",
    "deviceRegion": "EU",
}
LAMP = {"cid": "lampe", "deviceType": "ESL100", "deviceName": "Lampe", "configModule": "bulb"}


def cooking_multi(z1: int = 400, z2: int = 650) -> dict[str, Any]:
    return {
        "statusList": [
            {"chamber": 1, "cookStatus": "cooking", "cookLastTime": z1, "cookTemp": 200,
             "currentTemp": 190, "mode": "AirFry"},
            {"chamber": 2, "cookStatus": "cooking", "cookLastTime": z2, "cookTemp": 180,
             "mode": "Roast"},
        ],
        "totalTimeRemaining": max(z1, z2),
    }


def finished_multi() -> dict[str, Any]:
    return {
        "statusList": [
            {"chamber": 1, "cookStatus": "cookEnd", "cookLastTime": 0},
            {"chamber": 2, "cookStatus": "cookEnd", "cookLastTime": 0},
        ],
        "totalTimeRemaining": 0,
    }


def real_twinfry(status: str = "standby", remaining: int = 0, set_time: int = 0, temp: int = 0):
    """Echte Antwort von Marcos TwinFry (getAirfryerMultiStatus), 20.10.2026."""
    zone = {
        "cookStatus": status, "startTime": 0, "recipeType": 3, "recipeId": 14,
        "recipeName": "", "upc": "", "holdTime": 0, "cookSetTime": set_time,
        "cookTemp": temp, "mode": "AirFry", "currentRemainingTime": remaining,
        "totalTimeRemaining": remaining,
    }
    return {
        "statusList": [
            {**zone, "chamber": 1},
            {**zone, "chamber": 2, "cookStatus": "standby", "currentRemainingTime": 0,
             "cookSetTime": 0, "cookTemp": 0, "totalTimeRemaining": 0},
        ],
        "tempUnit": "c",
        "syncType": 0,
        "workChamber": 0,
    }


class FakeApi:
    """Attrappe der VeSync-Cloud."""

    instances: list[FakeApi] = []
    login_error: Exception | None = None
    devices: list[dict[str, Any]] = [DEVICE, LAMP]
    status: dict[str, Any] = {"cookStatus": "cooking"}
    multi: dict[str, Any] = cooking_multi()
    offline = False
    status_rejected = False
    reject: set[str] = set()
    reject_code = 11000000

    def __init__(self, session, email, password_md5, region, terminal_id, time_zone="x"):
        self.email = email
        self.password_md5 = password_md5
        self.region = region
        self.calls: list[tuple[str, dict[str, Any] | None]] = []
        FakeApi.instances.append(self)

    @property
    def account_id(self) -> str:
        return "konto-42"

    async def login(self) -> None:
        if FakeApi.login_error:
            raise FakeApi.login_error

    async def get_devices(self):
        return list(FakeApi.devices)

    async def bypass_v2(self, device, method, data=None):
        self.calls.append((method, data))
        if FakeApi.offline:
            raise AirfryerDeviceOffline("offline", -11300030)
        if method == "getAirfryerStatus":
            if FakeApi.status_rejected:
                raise AirfryerError("„getAirfryerStatus“ vom Gerät abgelehnt (Code 11030000)", 11030000)
            return dict(FakeApi.status)
        if method == "getAirfryerMultiStatus":
            return dict(FakeApi.multi)
        if method in FakeApi.reject:
            raise AirfryerError(
                f"„{method}“ vom Gerät abgelehnt (Code {FakeApi.reject_code})", FakeApi.reject_code
            )
        if method == "kaputt":
            raise AirfryerError("„kaputt“ abgelehnt", 11000000)
        return {"cid": CID, "ok": 1}

    async def bypass_v1_status(self, device):
        return {}


@pytest.fixture(autouse=True)
def fake_api():
    FakeApi.instances = []
    FakeApi.login_error = None
    FakeApi.reject = set()
    FakeApi.reject_code = 11000000
    FakeApi.devices = [DEVICE, LAMP]
    FakeApi.status = {"cookStatus": "cooking"}
    FakeApi.multi = cooking_multi()
    FakeApi.offline = False
    FakeApi.status_rejected = False
    with (
        patch("custom_components.airfryer_control.AirfryerApi", FakeApi),
        patch("custom_components.airfryer_control.config_flow.AirfryerApi", FakeApi),
    ):
        yield FakeApi


def make_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="marco@example.com",
        title="marco@example.com",
        data={
            "email": "marco@example.com",
            "password_md5": hash_password("geheim"),
            "region": "eu",
            "terminal_id": "ABC",
        },
    )


async def setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = make_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def eid(hass: HomeAssistant, platform: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{CID}_{key}")
    assert entity_id, f"{platform} {key} fehlt"
    return entity_id


# ---------------------------------------------------------------- Einrichtung
async def test_config_flow_stores_only_hash(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"email": " Marco@Example.com ", "passwort": "geheim", "region": "eu"},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    data = result["data"]
    assert data["email"] == "Marco@Example.com"
    assert data["password_md5"] == hash_password("geheim")
    assert "geheim" not in str(data)
    assert len(data["terminal_id"]) == 32


async def test_config_flow_wrong_password(hass: HomeAssistant, fake_api) -> None:
    fake_api.login_error = AirfryerAuthError("nein")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"email": "a@b.de", "passwort": "x", "region": "eu"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "anmeldung_falsch"}


async def test_config_flow_no_fryer(hass: HomeAssistant, fake_api) -> None:
    fake_api.devices = [LAMP]
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"email": "a@b.de", "passwort": "x", "region": "eu"}
    )
    assert result["errors"] == {"base": "keine_fritteuse"}


async def test_options_flow(hass: HomeAssistant) -> None:
    entry = await setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"intervall": 120, "zeiteinheit": "minuten"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"intervall": 120, "zeiteinheit": "minuten", "sidebar": False}


async def test_reauth_when_login_fails(hass: HomeAssistant, fake_api) -> None:
    fake_api.login_error = AirfryerAuthError("abgelaufen")
    entry = make_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is config_entries.ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert any(f["context"]["source"] == "reauth" for f in flows)


# --------------------------------------------------------------- Sensoren
async def test_sensors_while_cooking(hass: HomeAssistant) -> None:
    await setup(hass)
    assert hass.states.get(eid(hass, "sensor", "status")).state == "gart"
    assert hass.states.get(eid(hass, "sensor", "restzeit")).state == "11"  # 650 s → 11 min
    assert hass.states.get(eid(hass, "sensor", "zone1_restzeit")).state == "7"
    assert hass.states.get(eid(hass, "sensor", "zone2_programm")).state == "Roast"
    assert hass.states.get(eid(hass, "sensor", "zone1_temperatur")).state == "190"
    assert hass.states.get(eid(hass, "sensor", "fertig_um")).state not in ("unknown", "unavailable")
    assert hass.states.get(eid(hass, "binary_sensor", "gart")).state == "on"
    raw = hass.states.get(eid(hass, "sensor", "rohdaten"))
    assert CID not in str(raw.attributes)
    # Nur die Fritteuse wird ein Gerät, nicht die Lampe
    devices = dr.async_entries_for_config_entry(
        dr.async_get(hass), hass.config_entries.async_entries(DOMAIN)[0].entry_id
    )
    assert len(devices) == 1


async def test_finished_event(hass: HomeAssistant, fake_api) -> None:
    await setup(hass)
    events = async_capture_events(hass, EVENT_FINISHED)
    fake_api.status = {"cookStatus": "cookEnd"}
    fake_api.multi = finished_multi()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=20))
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, "sensor", "status")).state == "fertig"
    assert hass.states.get(eid(hass, "sensor", "restzeit")).state == "0"
    assert hass.states.get(eid(hass, "binary_sensor", "gart")).state == "off"
    zones = sorted(str(e.data["zone"]) for e in events)
    assert zones == ["1", "2", "alle"]
    assert events[0].data["geraet"] == "Fritteuse"


async def test_offline(hass: HomeAssistant, fake_api) -> None:
    await setup(hass)
    fake_api.offline = True
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=20))
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, "sensor", "status")).state == "offline"
    assert hass.states.get(eid(hass, "binary_sensor", "online")).state == "off"
    assert hass.states.get(eid(hass, "sensor", "restzeit")).state == "unknown"


# ---------------------------------------------------------- Knöpfe & Dienste
async def test_stop_button(hass: HomeAssistant) -> None:
    await setup(hass)
    await hass.services.async_call(
        "button", "press", {"entity_id": eid(hass, "button", "garen_beenden")}, blocking=True
    )
    calls = FakeApi.instances[-1].calls
    assert ("endCook", {"chamber": 1}) in calls and ("endCook", {"chamber": 2}) in calls


async def test_start_service_is_gone(hass: HomeAssistant) -> None:
    await setup(hass)
    assert not hass.services.has_service(DOMAIN, "garen_starten")


async def test_send_test_service_never_starts_by_itself(hass: HomeAssistant) -> None:
    FakeApi.reject = {"startMultiCook"}
    await setup(hass)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, CID)})
    res = await hass.services.async_call(
        DOMAIN,
        "senden_testen",
        {"geraet": device.id, "zone": 2, "temperatur": 180, "minuten": 10, "programm": "bake"},
        blocking=True,
        return_response=True,
    )
    assert res["ok"] is False
    assert [v["variante"] for v in res["versuche"]] == [
        "multi_app", "multi_app_celsius", "multi_app_zone0"
    ]
    sent = [c for c in FakeApi.instances[-1].calls if c[0] == "startMultiCook"]
    assert len(sent) == 3 and all(c[1]["readyStart"] is True for c in sent)
    assert "konto-42" not in str(res)


async def test_send_test_explicit_start_variant(hass: HomeAssistant) -> None:
    await setup(hass)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, CID)})
    res = await hass.services.async_call(
        DOMAIN, "senden_testen", {"geraet": device.id, "variante": "multi_app_startet"},
        blocking=True, return_response=True,
    )
    assert [v["variante"] for v in res["versuche"]] == ["multi_app_startet"]
    sent = [c for c in FakeApi.instances[-1].calls if c[0] == "startMultiCook"]
    assert sent[0][1]["readyStart"] is False  # startet wirklich – nur auf ausdrücklichen Wunsch


async def test_raw_service(hass: HomeAssistant) -> None:
    await setup(hass)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, CID)})
    res = await hass.services.async_call(
        DOMAIN,
        "befehl_senden",
        {"geraet": device.id, "methode": "getAirfryerStatus"},
        blocking=True,
        return_response=True,
    )
    assert res["ok"] is True
    res = await hass.services.async_call(
        DOMAIN,
        "befehl_senden",
        {"geraet": device.id, "methode": "kaputt"},
        blocking=True,
        return_response=True,
    )
    assert res["ok"] is False and res["code"] == 11000000


async def test_diagnostics_redacted(hass: HomeAssistant) -> None:
    entry = await setup(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    text = str(diag)
    assert CID not in text
    assert "geheime-uuid" not in text
    assert "marco@example.com" not in text
    assert diag["fritteusen"][0]["erkannt"]["zustand"] == "gart"


async def test_unload(hass: HomeAssistant) -> None:
    entry = await setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is config_entries.ConfigEntryState.NOT_LOADED


# ------------------------------------------------- Echte TwinFry (Beta 2)
async def test_twinfry_real_standby(hass: HomeAssistant, fake_api) -> None:
    """Normale Statusfrage abgelehnt, Mehrzonen-Frage klappt (wie bei Marco)."""
    fake_api.status_rejected = True
    fake_api.multi = real_twinfry()
    await setup(hass)
    assert hass.states.get(eid(hass, "sensor", "status")).state == "bereit"
    assert hass.states.get(eid(hass, "sensor", "zone1_status")).state == "bereit"
    assert hass.states.get(eid(hass, "sensor", "zone2_status")).state == "bereit"
    assert hass.states.get(eid(hass, "sensor", "restzeit")).state == "0"
    # Im Standby kein „AirFry“ anzeigen
    assert hass.states.get(eid(hass, "sensor", "zone1_programm")).state == "unknown"
    # TwinFry schickt keine gemessene Temperatur → kein Sensor dafür
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("sensor", DOMAIN, f"{CID}_zone1_temperatur") is None
    assert hass.states.get(eid(hass, "switch", "zone1_gart")).state == "off"
    assert hass.states.get(eid(hass, "number", "zone1_temperatur")).state == "200"
    assert hass.states.get(eid(hass, "select", "zone1_programm_waehlen")).state == "airfry"
    raw = hass.states.get(eid(hass, "sensor", "rohdaten")).attributes
    assert "getAirfryerStatus" in raw["abgelehnte_abfragen"]
    # Die abgelehnte Frage wird danach nicht mehr gestellt
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=120))
    await hass.async_block_till_done()
    asked = [c[0] for c in FakeApi.instances[-1].calls].count("getAirfryerStatus")
    assert asked == 1


async def test_twinfry_real_cooking(hass: HomeAssistant, fake_api) -> None:
    fake_api.status_rejected = True
    fake_api.multi = real_twinfry("cooking", remaining=754, set_time=900, temp=200)
    await setup(hass)
    assert hass.states.get(eid(hass, "sensor", "status")).state == "gart"
    assert hass.states.get(eid(hass, "sensor", "zone1_restzeit")).state == "13"
    assert hass.states.get(eid(hass, "sensor", "restzeit")).state == "13"
    assert hass.states.get(eid(hass, "sensor", "zone1_programm")).state == "AirFry"
    assert hass.states.get(eid(hass, "switch", "zone1_gart")).state == "on"
    assert hass.states.get(eid(hass, "switch", "zone2_gart")).state == "off"
    assert hass.states.get(eid(hass, "number", "zone1_temperatur")).state == "200"
    assert hass.states.get(eid(hass, "number", "zone1_garzeit")).state == "20"

    api = FakeApi.instances[-1]
    await hass.services.async_call(
        "number", "set_value",
        {"entity_id": eid(hass, "number", "zone1_temperatur"), "value": 180}, blocking=True,
    )
    assert ("setTimeOrTemp", {"cookSetTime": 900, "cookSetTemp": 180, "chamber": 1}) in api.calls
    await hass.services.async_call(
        "number", "set_value",
        {"entity_id": eid(hass, "number", "zone1_garzeit"), "value": 20}, blocking=True,
    )
    assert ("setTimeOrTemp", {"cookSetTime": 1200, "cookSetTemp": 200, "chamber": 1}) in api.calls

    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": eid(hass, "switch", "zone1_gart")}, blocking=True
    )
    assert ("endCook", {"chamber": 1}) in api.calls


async def test_switch_on_sends_plan_and_off_ends(hass: HomeAssistant, fake_api) -> None:
    fake_api.status_rejected = True
    fake_api.multi = real_twinfry()
    await setup(hass)
    api = FakeApi.instances[-1]
    await hass.services.async_call(
        "select", "select_option",
        {"entity_id": eid(hass, "select", "zone2_programm_waehlen"), "option": "grill"},
        blocking=True,
    )
    # Programmwechsel setzt die Vorschlagswerte der Fritteuse (Grill: 240 °C, 5 min)
    assert hass.states.get(eid(hass, "number", "zone2_temperatur")).state == "240"
    assert hass.states.get(eid(hass, "number", "zone2_garzeit")).state == "5"
    await hass.services.async_call(
        "number", "set_value",
        {"entity_id": eid(hass, "number", "zone2_temperatur"), "value": 220}, blocking=True,
    )
    assert not [c for c in api.calls if c[0] == "setTimeOrTemp"]  # steht still → nur merken
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": eid(hass, "switch", "zone2_gart")}, blocking=True
    )
    method, data = [c for c in api.calls if c[0] == "startMultiCook"][0]
    assert data["workChamber"] == 2 and data["accountId"] == "konto-42"
    assert data["readyStart"] is True
    assert data["cookConfigs"] == [
        {"cookSetTime": 300, "cookTemp": 220, "mode": "Grill", "chamber": 2,
         "recipeId": 14, "recipeName": "Grill", "recipeType": 3, "shakeTime": 0}
    ]
    assert hass.states.get(eid(hass, "switch", "zone2_gart")).state == "on"
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": eid(hass, "switch", "zone2_gart")}, blocking=True
    )
    assert ("endCook", {"chamber": 2}) in api.calls
    assert hass.states.get(eid(hass, "switch", "zone2_gart")).state == "off"


async def test_switch_on_all_rejected_shows_codes(hass: HomeAssistant, fake_api) -> None:
    from homeassistant.exceptions import HomeAssistantError

    fake_api.status_rejected = True
    fake_api.multi = real_twinfry()
    FakeApi.reject = {"startMultiCook"}
    await setup(hass)
    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": eid(hass, "switch", "zone1_gart")}, blocking=True
        )
    assert "11000000" in str(err.value)
    assert hass.states.get(eid(hass, "switch", "zone1_gart")).state == "off"


async def test_old_single_sensors_are_removed(hass: HomeAssistant, fake_api) -> None:
    """Nach dem Update von Beta 1 verschwinden die alten Ein-Kammer-Sensoren."""
    fake_api.status_rejected = True
    fake_api.multi = real_twinfry()
    entry = make_entry()
    entry.add_to_hass(hass)
    reg = er.async_get(hass)
    old = reg.async_get_or_create("sensor", DOMAIN, f"{CID}_programm", config_entry=entry)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert reg.async_get(old.entity_id) is None


async def test_nothing_removed_while_offline(hass: HomeAssistant, fake_api) -> None:
    fake_api.offline = True
    entry = make_entry()
    entry.add_to_hass(hass)
    reg = er.async_get(hass)
    old = reg.async_get_or_create("sensor", DOMAIN, f"{CID}_zone1_restzeit", config_entry=entry)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert reg.async_get(old.entity_id) is not None


async def test_ready_shows_waiting_and_switch_on(hass: HomeAssistant, fake_api) -> None:
    fake_api.status_rejected = True
    fake_api.multi = real_twinfry("ready", remaining=600, set_time=600, temp=180)
    await setup(hass)
    assert hass.states.get(eid(hass, "sensor", "zone1_status")).state == "wartet_auf_start"
    assert hass.states.get(eid(hass, "sensor", "zone2_status")).state == "bereit"
    assert hass.states.get(eid(hass, "sensor", "zone1_programm")).state == "AirFry"
    assert hass.states.get(eid(hass, "switch", "zone1_gart")).state == "on"
    assert hass.states.get(eid(hass, "switch", "zone2_gart")).state == "off"
    assert hass.states.get(eid(hass, "binary_sensor", "gart")).state == "off"


async def test_waiting_zone_is_polled_every_5_seconds(hass: HomeAssistant, fake_api) -> None:
    """Wartet eine Zone auf den Start, fragt die Integration besonders oft nach."""
    from datetime import timedelta

    fake_api.status_rejected = True
    fake_api.multi = real_twinfry("ready", remaining=600, set_time=600, temp=180)
    entry = await setup(hass)
    coordinator = entry.runtime_data
    assert coordinator.update_interval == timedelta(seconds=5)


async def test_stop_button_zone_without_program_is_not_an_error(hass: HomeAssistant) -> None:
    from custom_components.airfryer_control.core.api import AirfryerError as _E

    await setup(hass)
    api = FakeApi.instances[-1]
    orig = api.bypass_v2

    async def picky(device, method, data=None):
        if method == "endCook" and data == {"chamber": 2}:
            api.calls.append((method, data))
            raise _E("kein Programm", 11923000)
        return await orig(device, method, data)

    api.bypass_v2 = picky
    await hass.services.async_call(
        "button", "press", {"entity_id": eid(hass, "button", "garen_beenden")}, blocking=True
    )
    assert ("endCook", {"chamber": 1}) in api.calls and ("endCook", {"chamber": 2}) in api.calls


def whole_drawer(status: str = "ready") -> dict[str, Any]:
    """Echte Antwort der TwinFry ohne Trennwand (19:02, 20.10.2026)."""
    return {
        "statusList": [{
            "cookStatus": status, "startTime": 0, "recipeType": 3, "recipeId": 14,
            "recipeName": "Heißluft-Frittieren", "upc": "", "holdTime": 0,
            "cookSetTime": 1200, "cookTemp": 200, "mode": "AirFry",
            "currentRemainingTime": 1200, "totalTimeRemaining": 1200, "chamber": 3,
        }],
        "tempUnit": "c", "syncType": 0, "workChamber": 3,
    }


async def test_whole_drawer_has_own_entities(hass: HomeAssistant, fake_api) -> None:
    fake_api.status_rejected = True
    fake_api.multi = whole_drawer()
    await setup(hass)
    assert hass.states.get(eid(hass, "sensor", "zone3_status")).state == "wartet_auf_start"
    assert hass.states.get(eid(hass, "sensor", "zone3_restzeit")).state == "20"
    assert hass.states.get(eid(hass, "sensor", "zone3_programm")).state == "AirFry"
    assert hass.states.get(eid(hass, "sensor", "zone1_status")).state == "bereit"
    assert hass.states.get(eid(hass, "sensor", "zone2_status")).state == "bereit"
    assert hass.states.get(eid(hass, "switch", "zone3_gart")).state == "on"
    assert hass.states.get(eid(hass, "switch", "zone1_gart")).state == "off"
    state = hass.states.get(eid(hass, "switch", "zone3_gart"))
    assert "Grandzone" in state.attributes["friendly_name"]


async def test_whole_drawer_send_and_end(hass: HomeAssistant, fake_api) -> None:
    fake_api.status_rejected = True
    fake_api.multi = real_twinfry()
    await setup(hass)
    api = FakeApi.instances[-1]
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": eid(hass, "switch", "zone3_gart")}, blocking=True
    )
    _, data = [c for c in api.calls if c[0] == "startMultiCook"][0]
    assert data["workChamber"] == 3 and data["readyStart"] is True
    assert data["cookConfigs"][0]["chamber"] == 3
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": eid(hass, "switch", "zone3_gart")}, blocking=True
    )
    assert ("endCook", {"chamber": 3}) in api.calls


async def test_value_not_allowed_gives_friendly_message(hass: HomeAssistant, fake_api) -> None:
    from homeassistant.exceptions import HomeAssistantError

    fake_api.status_rejected = True
    fake_api.multi = real_twinfry()
    await setup(hass)
    FakeApi.reject_code = 11011000
    FakeApi.reject = {"startMultiCook"}
    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": eid(hass, "switch", "zone1_gart")}, blocking=True
        )
    assert "nimmt diese Werte" in str(err.value) or "does not accept" in str(err.value)


def test_program_temperature_limits() -> None:
    from custom_components.airfryer_control.const import MODE_DEFAULTS
    from custom_components.airfryer_control.senden import clamp_temp, temp_limits

    assert temp_limits("airfry") == (120, 205)
    assert temp_limits("grill") == (205, 240)
    assert clamp_temp("airfry", 100) == 120
    assert clamp_temp("bake", 300) == 205
    for mode, (temp, _) in MODE_DEFAULTS.items():
        low, high = temp_limits(mode)
        assert low <= temp <= high


async def test_frontend_cards_are_served_and_registered() -> None:
    """Die Karten-Datei existiert und ist als Dashboard-Ressource eingetragen."""
    from pathlib import Path

    from custom_components.airfryer_control import frontend
    from custom_components.airfryer_control.const import CARD_FILENAME

    www = Path(frontend.__file__).parent / "www"
    js = (www / CARD_FILENAME).read_text(encoding="utf-8")
    assert "customElements.define(\"airfryer-control-card\"" in js
    assert "customElements.define(\"airfryer-control-ticker\"" in js
    assert (www / "mister-m.webp").exists()
    assert frontend._version() != "0"


async def test_app_page_is_served(hass, hass_client_no_auth, fake_api) -> None:
    """Die Handy-App wird ohne Anmeldung ausgeliefert (sie enthält keine Daten)."""
    await setup(hass)
    client = await hass_client_no_auth()
    for path, kind in (("/airfryer_control/app/", "text/html"), ("/airfryer_control/app/manifest.webmanifest", "application/manifest+json"),
                       ("/airfryer_control/app/sw.js", "text/javascript"), ("/airfryer_control/app/icon-192.png", "image/png")):
        resp = await client.get(path)
        assert resp.status == 200, path
        assert kind in resp.headers["Content-Type"]
    html = await (await client.get("/airfryer_control/app/")).text()
    assert "__AC_VERSION__" not in html and "Airfryer Control" in html
    assert (await client.get("/airfryer_control/app/geheim.txt")).status == 404
    resp = await client.get("/airfryer_control/app", allow_redirects=False)
    assert resp.status == 302


async def test_sidebar_option_registers_and_removes_panel(hass: HomeAssistant, fake_api) -> None:
    """Die Seitenleiste ist standardmäßig aus und lässt sich per Option ein- und ausschalten."""
    from homeassistant.components import frontend

    from custom_components.airfryer_control.const import OPT_SIDEBAR, PANEL_URL_PATH

    entry = make_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL_PATH not in hass.data.get(frontend.DATA_PANELS, {})  # Standard: aus

    hass.config_entries.async_update_entry(entry, options={**entry.options, OPT_SIDEBAR: True})
    await hass.async_block_till_done()
    panel = hass.data[frontend.DATA_PANELS][PANEL_URL_PATH]
    assert panel.sidebar_title == "Fritteuse"
    assert panel.sidebar_icon == "mdi:toaster-oven"
    assert panel.require_admin is False

    hass.config_entries.async_update_entry(entry, options={**entry.options, OPT_SIDEBAR: False})
    await hass.async_block_till_done()
    assert PANEL_URL_PATH not in hass.data[frontend.DATA_PANELS]

    hass.config_entries.async_update_entry(entry, options={**entry.options, OPT_SIDEBAR: True})
    await hass.async_block_till_done()
    assert PANEL_URL_PATH in hass.data[frontend.DATA_PANELS]
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL_PATH not in hass.data[frontend.DATA_PANELS]


async def test_match_and_sync_services_only_prepare(hass: HomeAssistant) -> None:
    await setup(hass)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, CID)})
    for name, sync in (("match_senden", 1), ("sync_senden", 2)):
        await hass.services.async_call(DOMAIN, name, {"geraet": device.id}, blocking=True)
        sent = [c for c in FakeApi.instances[-1].calls if c[0] == "startMultiCook"][-1]
        assert sent[1]["syncType"] == sync and sent[1]["readyStart"] is True
        assert len(sent[1]["cookConfigs"]) == 2


async def test_zone_entities_appear_when_fryer_comes_online_later(hass: HomeAssistant) -> None:
    FakeApi.offline = True
    await setup(hass)
    assert not er.async_get(hass).async_get_entity_id("switch", DOMAIN, f"{CID}_zone1_gart")
    FakeApi.offline = False
    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert er.async_get(hass).async_get_entity_id("switch", DOMAIN, f"{CID}_zone1_gart")
    assert er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{CID}_zone2_status")


async def test_cooking_time_limits_follow_program(hass: HomeAssistant) -> None:
    await setup(hass)
    sel = eid(hass, "select", "zone1_programm_waehlen")
    tim = eid(hass, "number", "zone1_garzeit")
    for prog, high in (("airfry", 60), ("roast", 240), ("bake", 240), ("grill", 30), ("reheat", 60), ("dry", 2880)):
        await hass.services.async_call(
            "select", "select_option", {"entity_id": sel, "option": prog}, blocking=True
        )
        await hass.async_block_till_done()
        st = hass.states.get(tim)
        assert (st.attributes["min"], st.attributes["max"]) == (1, high), prog


async def test_dry_temperature_limits(hass: HomeAssistant) -> None:
    await setup(hass)
    await hass.services.async_call(
        "select", "select_option",
        {"entity_id": eid(hass, "select", "zone1_programm_waehlen"), "option": "dry"}, blocking=True,
    )
    await hass.async_block_till_done()
    st = hass.states.get(eid(hass, "number", "zone1_temperatur"))
    assert (st.attributes["min"], st.attributes["max"]) == (34, 95)
