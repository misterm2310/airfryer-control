"""Verbindung zur VeSync-Cloud (die Cloud hinter der Cosori-/VeSync-App).

Für Doofe: Die Fritteuse redet nicht direkt mit Home Assistant, sondern nur mit
dem VeSync-Server. Diese Datei meldet sich dort mit deinem App-Konto an, fragt
den Zustand der Fritteuse ab und schickt Befehle hin – genau wie die App.

Der Ablauf der Anmeldung (zwei Schritte, plus „anderer Kontinent“-Sonderfall)
stammt aus dem offenen ioBroker-Adapter „vesync“ (MIT) und aus pyvesync.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

APP_VERSION = "5.7.80"
APP_BUILD = "693"
APP_VERSION_FULL = f"VeSync {APP_VERSION} build{APP_BUILD}"
APP_ID = "eldodkfj"
USER_AGENT = "okhttp/3.12.1"
PHONE_BRAND = "HomeAssistant"
PHONE_OS = "Android"

BASE_URL = {
    "EU": "https://smartapi.vesync.eu",
    "US": "https://smartapi.vesync.com",
}

TIMEOUT = aiohttp.ClientTimeout(total=20)

# Antwort-Codes der Cloud, die wir kennen
CODE_OK = 0
CODE_DEVICE_OFFLINE = -11300030
CODE_DEVICE_TIMEOUT = -11302030
CODE_APP_TOO_OLD = -11012022
# Codes, bei denen das Anmelde-Token abgelaufen ist (aus pyvesync bekannt)
AUTH_ERROR_CODES = {-11001000, -11003000, -11012002, 4001004, -11001001}


class AirfryerError(Exception):
    """Allgemeiner Fehler beim Reden mit der Cloud."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class AirfryerAuthError(AirfryerError):
    """E-Mail oder Passwort falsch bzw. Anmeldung abgelaufen."""


class AirfryerConnectionError(AirfryerError):
    """Server nicht erreichbar."""


class AirfryerDeviceOffline(AirfryerError):
    """Die Fritteuse ist gerade nicht online (Stecker raus, WLAN weg …)."""


def hash_password(password: str) -> str:
    """Die App schickt nie das Passwort selbst, sondern seinen MD5-Wert."""
    return hashlib.md5(password.encode("utf-8")).hexdigest()  # noqa: S324


def is_air_fryer(device: dict[str, Any]) -> bool:
    """Ist das Gerät aus der Geräteliste eine Heißluftfritteuse?

    Cosori-Fritteusen heißen in der Cloud „CA…“ (neuere, z. B. TwinFry) oder
    „CS…“ (ältere 3,7/5,8-Quart-Modelle). Backöfen haben auch „CA…“, aber
    „Oven“/„OVN“ im configModule – die lassen wir weg.
    """
    dev_type = str(device.get("deviceType") or "")
    module = str(device.get("configModule") or "")
    if "oven" in module.lower() or "ovn" in module.lower():
        return False
    if dev_type.startswith(("CA", "CS")):
        return True
    return "fryer" in module.lower() or "airfryer" in dev_type.lower()


class AirfryerApi:
    """Ein Konto bei VeSync."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password_md5: str,
        region: str,
        terminal_id: str,
        time_zone: str = "Europe/Berlin",
    ) -> None:
        self._session = session
        self._email = email
        self._password_md5 = password_md5
        region = (region or "EU").upper()
        self._region = region if region in BASE_URL else "EU"
        self._terminal_id = terminal_id
        self._time_zone = time_zone
        self._token: str | None = None
        self._account_id: str | None = None
        self._country_code: str = "DE" if self._region == "EU" else "US"
        self._current_region: str = self._region
        self._lang = "de"
        self._login_lock = asyncio.Lock()

    # ------------------------------------------------------------------ Hilfen
    @property
    def logged_in(self) -> bool:
        return bool(self._token)

    @property
    def account_id(self) -> str | None:
        return self._account_id

    @property
    def base_url(self) -> str:
        return BASE_URL.get(self._current_region, BASE_URL["EU"])

    def _trace(self) -> str:
        return str(int(time.time() * 1000))

    def _auth_body(self, method: str) -> dict[str, Any]:
        return {
            "acceptLanguage": self._lang,
            "accountID": "",
            "appVersion": APP_VERSION,
            "appID": APP_ID,
            "sourceAppID": APP_ID,
            "clientInfo": PHONE_BRAND,
            "clientType": "vesyncApp",
            "clientVersion": f"VeSync {APP_VERSION}",
            "debugMode": False,
            "method": method,
            "osInfo": PHONE_OS,
            "phoneBrand": PHONE_BRAND,
            "phoneOS": PHONE_OS,
            "terminalId": self._terminal_id,
            "timeZone": self._time_zone,
            "token": "",
            "traceId": self._trace(),
            "userCountryCode": self._region,
        }

    async def _post(
        self, url: str, body: dict[str, Any], headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Eine Anfrage schicken und die Antwort als dict zurückgeben."""
        hdrs = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
        if headers:
            hdrs.update(headers)
        try:
            async with self._session.post(
                url, json=body, headers=hdrs, timeout=TIMEOUT
            ) as resp:
                if resp.status == 401:
                    raise AirfryerAuthError("Anmeldung abgelaufen (HTTP 401)")
                if resp.status >= 400:
                    raise AirfryerConnectionError(f"Server antwortet mit HTTP {resp.status}")
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise AirfryerConnectionError(f"VeSync-Server nicht erreichbar: {err}") from err
        if not isinstance(data, dict):
            raise AirfryerConnectionError("Unerwartete Antwort vom Server")
        return data

    # ---------------------------------------------------------------- Anmelden
    async def login(self) -> None:
        """Anmelden wie die App (zwei Schritte)."""
        async with self._login_lock:
            await self._login()

    async def _login(self) -> None:
        start_url = BASE_URL[self._region]
        # Schritt 1: Mit E-Mail + Passwort-Hash einen Einmal-Code holen
        body = {
            **self._auth_body("authByPWDOrOTM"),
            "email": self._email,
            "password": self._password_md5,
            "authProtocolType": "generic",
        }
        res = await self._post(
            f"{start_url}/globalPlatform/api/accountAuth/v1/authByPWDOrOTM", body
        )
        code = res.get("code")
        result = res.get("result") or {}
        if code != CODE_OK or not result.get("authorizeCode"):
            if code == CODE_APP_TOO_OLD:
                raise AirfryerError(
                    "VeSync meldet „App-Version zu alt“ – bitte Update der Integration abwarten",
                    code,
                )
            raise AirfryerAuthError(
                f"Anmeldung abgelehnt: {res.get('msg')} (Code {code})", code
            )
        authorize_code = result["authorizeCode"]
        account_id = result.get("accountID", "")

        # Schritt 2: Einmal-Code gegen ein Token tauschen
        body = {
            **self._auth_body("loginByAuthorizeCode4Vesync"),
            "accountID": account_id,
            "authorizeCode": authorize_code,
        }
        res = await self._post(
            f"{start_url}/user/api/accountManage/v1/loginByAuthorizeCode4Vesync", body
        )
        result = res.get("result") or {}
        if res.get("code") != CODE_OK and result.get("bizToken"):
            # Konto liegt auf dem „anderen“ Server → mit bizToken dort nochmal
            region = result.get("currentRegion") or self._region
            country = result.get("countryCode") or self._country_code
            url = BASE_URL.get(region, start_url)
            body = {
                **self._auth_body("loginByAuthorizeCode4Vesync"),
                "accountID": account_id,
                "authorizeCode": authorize_code,
                "bizToken": result["bizToken"],
                "regionChange": "lastRegion",
                "userCountryCode": country,
            }
            res = await self._post(
                f"{url}/user/api/accountManage/v1/loginByAuthorizeCode4Vesync", body
            )
            result = res.get("result") or {}
        if res.get("code") != CODE_OK or not result.get("token"):
            raise AirfryerAuthError(
                f"Anmeldung fehlgeschlagen: {res.get('msg')} (Code {res.get('code')})",
                res.get("code"),
            )
        self._token = result["token"]
        self._account_id = result.get("accountID") or account_id
        self._country_code = result.get("countryCode") or self._country_code
        region = result.get("currentRegion")
        if region in BASE_URL:
            self._current_region = region
        elif self._country_code == "US":
            self._current_region = "US"
        self._lang = result.get("acceptLanguage") or self._lang
        _LOGGER.debug("Bei VeSync angemeldet (Region %s)", self._current_region)

    async def _ensure_login(self) -> None:
        if not self._token:
            await self.login()

    # ------------------------------------------------------------- Geräteliste
    async def get_devices(self) -> list[dict[str, Any]]:
        """Alle Geräte des Kontos."""
        await self._ensure_login()

        async def _do() -> dict[str, Any]:
            body = {
                "acceptLanguage": self._lang,
                "traceId": self._trace(),
                "accountID": self._account_id,
                "appVersion": APP_VERSION_FULL,
                "method": "devices",
                "pageNo": 1,
                "pageSize": 100,
                "phoneBrand": PHONE_BRAND,
                "phoneOS": PHONE_OS,
                "debugMode": False,
                "timeZone": self._time_zone,
                "token": self._token,
            }
            return await self._post(
                f"{self.base_url}/cloud/v2/deviceManaged/devices",
                body,
                headers={
                    "tk": self._token or "",
                    "accountid": self._account_id or "",
                    "tz": self._time_zone,
                },
            )

        res = await self._with_relogin(_do)
        if res.get("code") != CODE_OK:
            raise AirfryerError(
                f"Geräteliste nicht lesbar: {res.get('msg')} (Code {res.get('code')})",
                res.get("code"),
            )
        return list((res.get("result") or {}).get("list") or [])

    # ------------------------------------------------------------- bypassV2
    async def bypass_v2(
        self,
        device: dict[str, Any],
        method: str,
        data: dict[str, Any] | None = None,
        *,
        retry: bool = True,
    ) -> dict[str, Any]:
        """Einen Befehl an ein Gerät schicken (so macht es die App).

        Gibt das innere Ergebnis zurück. Wirft AirfryerDeviceOffline, wenn die
        Fritteuse nicht erreichbar ist, sonst AirfryerError mit Code.
        Mit ``retry=False`` geht die Anfrage höchstens einmal raus: Ist das
        Token abgelaufen, gibt es einen AirfryerAuthError (nichts gesendet),
        und beim nächsten Mal wird vorher neu angemeldet.
        """
        await self._ensure_login()

        async def _do() -> dict[str, Any]:
            body = {
                "acceptLanguage": self._lang,
                "accountID": self._account_id,
                "appVersion": APP_VERSION_FULL,
                "cid": device.get("cid"),
                "configModule": device.get("configModule") or "",
                "debugMode": False,
                "deviceRegion": device.get("deviceRegion") or self._current_region,
                "method": "bypassV2",
                "payload": {"data": data or {}, "method": method, "source": "APP"},
                "phoneBrand": PHONE_BRAND,
                "phoneOS": PHONE_OS,
                "timeZone": self._time_zone,
                "token": self._token,
                "traceId": self._trace(),
                "userCountryCode": self._country_code,
            }
            return await self._post(
                f"{self.base_url}/cloud/v2/deviceManaged/bypassV2", body
            )

        if retry:
            res = await self._with_relogin(_do)
        else:
            res = await self._once(_do)
        return self._unwrap(res, method)

    async def bypass_v1_status(self, device: dict[str, Any]) -> dict[str, Any]:
        """Ältere CS-Modelle (3,7/5,8 Quart) sprechen noch „bypass“ (v1)."""
        await self._ensure_login()

        async def _do() -> dict[str, Any]:
            body = {
                "acceptLanguage": self._lang,
                "accountID": self._account_id,
                "appVersion": APP_VERSION_FULL,
                "cid": device.get("cid"),
                "configModule": device.get("configModule") or "",
                "debugMode": False,
                "jsonCmd": {"getStatus": "status"},
                "method": "bypass",
                "phoneBrand": PHONE_BRAND,
                "phoneOS": PHONE_OS,
                "pid": "8t8op7pcvzlsbosm",
                "timeZone": self._time_zone,
                "token": self._token,
                "traceId": self._trace(),
                "userCountryCode": self._country_code,
                "uuid": device.get("uuid"),
            }
            return await self._post(f"{self.base_url}/cloud/v1/deviceManaged/bypass", body)

        res = await self._with_relogin(_do)
        return self._unwrap(res, "getStatus")

    @staticmethod
    def _unwrap(res: dict[str, Any], method: str) -> dict[str, Any]:
        code = res.get("code")
        if code in (CODE_DEVICE_OFFLINE, CODE_DEVICE_TIMEOUT):
            raise AirfryerDeviceOffline(
                f"Fritteuse antwortet nicht ({res.get('msg')})", code
            )
        if code != CODE_OK:
            raise AirfryerError(
                f"„{method}“ abgelehnt: {res.get('msg')} (Code {code})", code
            )
        result = res.get("result")
        if isinstance(result, dict):
            inner_code = result.get("code")
            if inner_code not in (None, 0):
                raise AirfryerError(
                    f"„{method}“ vom Gerät abgelehnt (Code {inner_code})", inner_code
                )
            inner = result.get("result")
            if isinstance(inner, dict):
                return inner
            return result
        return {}

    async def _once(self, func) -> dict[str, Any]:
        """Anfrage genau einmal schicken – auch nach abgelaufenem Token keine Wiederholung."""
        try:
            res = await func()
        except AirfryerAuthError:
            res = {"code": -11001000}
        if res.get("code") in AUTH_ERROR_CODES:
            self._token = None  # beim nächsten Versuch vorher neu anmelden
            raise AirfryerAuthError(
                "Anmeldung abgelaufen – nichts gesendet, bitte erneut versuchen",
                res.get("code"),
            )
        return res

    async def _with_relogin(self, func) -> dict[str, Any]:
        """Anfrage schicken; ist das Token abgelaufen, einmal neu anmelden."""
        try:
            res = await func()
        except AirfryerAuthError:
            res = {"code": -11001000}
        if res.get("code") in AUTH_ERROR_CODES:
            _LOGGER.debug("Token abgelaufen – melde neu an")
            self._token = None
            await self.login()
            res = await func()
        return res
