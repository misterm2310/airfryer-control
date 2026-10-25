"""Tests für die Cloud-Verbindung mit nachgebauten Server-Antworten."""

from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.airfryer_control.core.api import (
    AirfryerApi,
    AirfryerAuthError,
    AirfryerDeviceOffline,
    AirfryerError,
    hash_password,
    is_air_fryer,
)

EU = "https://smartapi.vesync.eu"
US = "https://smartapi.vesync.com"
AUTH = "/globalPlatform/api/accountAuth/v1/authByPWDOrOTM"
TOKEN = "/user/api/accountManage/v1/loginByAuthorizeCode4Vesync"
DEVICES = "/cloud/v2/deviceManaged/devices"
BYPASS = "/cloud/v2/deviceManaged/bypassV2"


def api(hass: HomeAssistant, region: str = "eu") -> AirfryerApi:
    return AirfryerApi(
        async_get_clientsession(hass), "a@b.de", hash_password("pw"), region, "TERM"
    )


def ok_login(aioclient_mock, base: str = EU) -> None:
    aioclient_mock.post(
        base + AUTH, json={"code": 0, "result": {"authorizeCode": "c0de", "accountID": "42"}}
    )
    aioclient_mock.post(
        base + TOKEN,
        json={"code": 0, "result": {"token": "tok", "accountID": "42", "countryCode": "DE",
                                     "currentRegion": "EU"}},
    )


async def test_login_sends_md5_never_plaintext(hass, aioclient_mock) -> None:
    ok_login(aioclient_mock)
    client = api(hass)
    await client.login()
    assert client.logged_in
    body = aioclient_mock.mock_calls[0][2]
    assert body["password"] == hash_password("pw")
    assert "pw" != body["password"]
    assert body["email"] == "a@b.de"


async def test_login_wrong_password(hass, aioclient_mock) -> None:
    aioclient_mock.post(EU + AUTH, json={"code": -11201000, "msg": "password error"})
    with pytest.raises(AirfryerAuthError):
        await api(hass).login()


async def test_login_cross_region(hass, aioclient_mock) -> None:
    aioclient_mock.post(
        US + AUTH, json={"code": 0, "result": {"authorizeCode": "c0de", "accountID": "42"}}
    )
    aioclient_mock.post(
        US + TOKEN,
        json={"code": -11260022, "result": {"bizToken": "biz", "currentRegion": "EU",
                                            "countryCode": "DE"}},
    )
    aioclient_mock.post(
        EU + TOKEN,
        json={"code": 0, "result": {"token": "tok", "accountID": "42", "currentRegion": "EU"}},
    )
    client = api(hass, "us")
    await client.login()
    assert client.base_url == EU
    retry = aioclient_mock.mock_calls[2][2]
    assert retry["bizToken"] == "biz"
    assert retry["userCountryCode"] == "DE"


async def test_devices_and_status(hass, aioclient_mock) -> None:
    ok_login(aioclient_mock)
    aioclient_mock.post(
        EU + DEVICES,
        json={"code": 0, "result": {"list": [{"cid": "x", "deviceType": "CAF-TF101S"}]}},
    )
    aioclient_mock.post(
        EU + BYPASS,
        json={"code": 0, "result": {"code": 0, "result": {"cookStatus": "cooking"}}},
    )
    client = api(hass)
    devices = await client.get_devices()
    assert devices[0]["cid"] == "x"
    status = await client.bypass_v2(devices[0], "getAirfryerStatus")
    assert status == {"cookStatus": "cooking"}
    sent = aioclient_mock.mock_calls[-1][2]
    assert sent["payload"]["method"] == "getAirfryerStatus"
    assert sent["token"] == "tok"


async def test_device_offline(hass, aioclient_mock) -> None:
    ok_login(aioclient_mock)
    aioclient_mock.post(EU + BYPASS, json={"code": -11302030, "msg": "device timeout"})
    with pytest.raises(AirfryerDeviceOffline):
        await api(hass).bypass_v2({"cid": "x"}, "getAirfryerStatus")


async def test_device_rejects_command(hass, aioclient_mock) -> None:
    ok_login(aioclient_mock)
    aioclient_mock.post(EU + BYPASS, json={"code": 0, "result": {"code": 11000000}})
    with pytest.raises(AirfryerError) as err:
        await api(hass).bypass_v2({"cid": "x"}, "startMultiCook", {})
    assert err.value.code == 11000000


async def test_relogin_on_expired_token(hass, aioclient_mock) -> None:
    ok_login(aioclient_mock)
    client = api(hass)
    await client.login()
    aioclient_mock.clear_requests()
    ok_login(aioclient_mock)
    aioclient_mock.post(EU + BYPASS, json={"code": -11001000, "msg": "token expired"})
    with pytest.raises(AirfryerError):
        await client.bypass_v2({"cid": "x"}, "getAirfryerStatus")
    paths = [str(c[1]) for c in aioclient_mock.mock_calls]
    assert any(AUTH in p for p in paths), "Es wurde nicht neu angemeldet"


async def test_once_never_repeats_after_expired_token(hass, aioclient_mock) -> None:
    """retry=False: genau eine Anfrage, keine stille Wiederholung nach neuer Anmeldung."""
    ok_login(aioclient_mock)
    client = api(hass)
    await client.login()
    aioclient_mock.clear_requests()
    ok_login(aioclient_mock)
    aioclient_mock.post(EU + BYPASS, json={"code": -11001000, "msg": "token expired"})
    with pytest.raises(AirfryerAuthError):
        await client.bypass_v2({"cid": "x"}, "startMultiCook", {}, retry=False)
    paths = [str(c[1]) for c in aioclient_mock.mock_calls]
    assert sum(BYPASS in p for p in paths) == 1
    assert not any(AUTH in p for p in paths)
    assert not client.logged_in  # beim nächsten Versuch wird vorher neu angemeldet


def test_is_air_fryer() -> None:
    assert is_air_fryer({"deviceType": "CAF-TF101S-AEUR", "configModule": "WiFi_AirFryer"})
    assert is_air_fryer({"deviceType": "CS158-AF"})
    assert not is_air_fryer({"deviceType": "CAF-OV", "configModule": "WiFi_Oven_CS"})
    assert not is_air_fryer({"deviceType": "LAP-C601S", "configModule": "purifier"})
