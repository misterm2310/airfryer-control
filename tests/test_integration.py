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

from custom_components.cosori_bedienung.api import (
    CosoriAuthError,
    CosoriDeviceOffline,
    CosoriError,
    hash_password,
)
from custom_components.cosori_bedienung.const import DOMAIN, EVENT_FINISHED
from custom_components.cosori_bedienung.diagnostics import (
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


class FakeApi:
    """Attrappe der VeSync-Cloud."""

    instances: list[FakeApi] = []
    login_error: Exception | None = None
    devices: list[dict[str, Any]] = [DEVICE, LAMP]
    status: dict[str, Any] = {"cookStatus": "cooking"}
    multi: dict[str, Any] = cooking_multi()
    offline = False

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
            raise CosoriDeviceOffline("offline", -11300030)
        if method == "getAirfryerStatus":
            return dict(FakeApi.status)
        if method == "getAirfryerMultiStatus":
            return dict(FakeApi.multi)
        if method == "kaputt":
            raise CosoriError("„kaputt“ abgelehnt", 11000000)
        return {"cid": CID, "ok": 1}

    async def bypass_v1_status(self, device):
        return {}


@pytest.fixture(autouse=True)
def fake_api():
    FakeApi.instances = []
    FakeApi.login_error = None
    FakeApi.devices = [DEVICE, LAMP]
    FakeApi.status = {"cookStatus": "cooking"}
    FakeApi.multi = cooking_multi()
    FakeApi.offline = False
    with (
        patch("custom_components.cosori_bedienung.CosoriApi", FakeApi),
        patch("custom_components.cosori_bedienung.config_flow.CosoriApi", FakeApi),
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
    fake_api.login_error = CosoriAuthError("nein")
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
    assert entry.options == {"intervall": 120, "zeiteinheit": "minuten"}


async def test_reauth_when_login_fails(hass: HomeAssistant, fake_api) -> None:
    fake_api.login_error = CosoriAuthError("abgelaufen")
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
    assert ("endCook", {}) in FakeApi.instances[-1].calls


async def test_start_service(hass: HomeAssistant) -> None:
    await setup(hass)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, CID)})
    await hass.services.async_call(
        DOMAIN,
        "garen_starten",
        {"geraet": device.id, "zone": "2", "temperatur": 180, "minuten": 10, "programm": "bake"},
        blocking=True,
    )
    method, data = [c for c in FakeApi.instances[-1].calls if c[0] == "startMultiCook"][0]
    assert data["workChamber"] == 2
    assert data["accountId"] == "konto-42"
    assert data["cookConfigs"] == [
        {"cookSetTime": 600, "cookTemp": 180, "mode": "Bake", "chamber": 2}
    ]


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
