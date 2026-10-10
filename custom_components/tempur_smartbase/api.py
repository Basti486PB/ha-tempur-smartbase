"""Async client for the Sleeptracker cloud API used by Tempur smart bases.

The endpoints and payloads follow the community reverse engineering in
richardhopton/smartbed-mqtt (MIT licensed).
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any

import aiohttp

from .const import BRAND_CONFIG, BRAND_TEMPUR, Command

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)
DEVICE_TYPES = [1, 2, 4, 6]

# Status 28 / INVALID_PRESET is returned for a plain status request on some
# bases and is harmless.
_IGNORED_STATUS = (28, "INVALID_PRESET")


class SleeptrackerError(Exception):
    """Generic API error."""


class SleeptrackerAuthError(SleeptrackerError):
    """Credentials were rejected."""


class SleeptrackerConnectionError(SleeptrackerError):
    """The cloud could not be reached."""


class SleeptrackerApi:
    """Minimal client for the Sleeptracker cloud."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
        brand: str = BRAND_TEMPUR,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        brand_config = BRAND_CONFIG.get(brand, BRAND_CONFIG[BRAND_TEMPUR])
        base_host = brand_config["base_host"]
        self._client_id = brand_config["client_id"]
        self._client_version = brand_config["client_version"]
        self._auth_url = f"https://auth.{base_host}/v1/app/user/session"
        fpcsiot = f"https://app.{base_host}/actrack-client/v2/fpcsiot"
        self._processor_url = f"{fpcsiot}/processor"
        self._settings_url = f"{fpcsiot}/settings"
        self._token: str | None = None
        self._token_expires: float = 0
        self._token_lock = asyncio.Lock()

    def _payload(self, context: str, **extra: Any) -> dict[str, Any]:
        return {
            "clientID": self._client_id,
            "clientVersion": self._client_version,
            "id": f"TEST_ANDROID_{context}",
            **extra,
        }

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "accept": "*/*",
            "content-type": "application/json",
            "accept-language": "en-US,en;q=0.9",
        }

    async def authenticate(self) -> None:
        """Log in and store a bearer token."""
        credentials = base64.b64encode(
            f"{self._email}:{self._password}".encode()
        ).decode()
        headers = {**self._headers(), "Authorization": f"Basic {credentials}"}
        try:
            async with self._session.post(
                self._auth_url,
                json=self._payload("getUserSession", scope="scope"),
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status in (401, 403):
                    raise SleeptrackerAuthError("Invalid credentials")
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except aiohttp.ClientResponseError as err:
            raise SleeptrackerError(f"Login failed: {err.status}") from err
        except (TimeoutError, aiohttp.ClientError) as err:
            raise SleeptrackerConnectionError(str(err)) from err

        token = data.get("token") if isinstance(data, dict) else None
        if not token:
            raise SleeptrackerAuthError("Login response did not contain a token")
        self._token = token
        self._token_expires = float(data.get("expirationTimeSecs") or 0)

    async def _ensure_token(self) -> str:
        async with self._token_lock:
            if self._token is None or time.time() + 60 >= self._token_expires:
                await self.authenticate()
            assert self._token is not None
            return self._token

    async def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(2):
            token = await self._ensure_token()
            headers = {**self._headers(), "Authorization": f"Bearer {token}"}
            try:
                async with self._session.post(
                    url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT
                ) as resp:
                    if resp.status == 401 and attempt == 0:
                        # Token was revoked early; log in again once.
                        self._token = None
                        continue
                    if resp.status in (401, 403):
                        raise SleeptrackerAuthError("Session rejected")
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
            except aiohttp.ClientResponseError as err:
                raise SleeptrackerError(f"{url} failed: {err.status}") from err
            except (TimeoutError, aiohttp.ClientError) as err:
                raise SleeptrackerConnectionError(str(err)) from err
            return data if isinstance(data, dict) else {}
        raise SleeptrackerAuthError("Session rejected")

    async def get_devices(self) -> list[dict[str, Any]]:
        """Return the active Sleeptracker processors on the account."""
        data = await self._post(
            f"{self._processor_url}/getByType",
            self._payload("cloudIoTDevicesGetByType", types=DEVICE_TYPES),
        )
        return [d for d in data.get("deviceList") or [] if d.get("active")]

    async def get_hello(self, processor_id: int) -> dict[str, Any]:
        """Return processor details, including motor capabilities and features."""
        data = await self._post(
            f"{self._processor_url}/command/hello",
            self._payload(
                "cloudIoTProcessorSimpleHello", sleeptrackerProcessorID=processor_id
            ),
        )
        hello = data.get("helloData")
        if not hello:
            raise SleeptrackerError(data.get("statusMessage") or "No hello data")
        return hello

    async def get_sensor_map(self, processor_id: int) -> list[dict[str, Any]]:
        """Return the sleep sensors (one per side) of a processor."""
        data = await self._post(
            f"{self._processor_url}/getSensorMap",
            self._payload(
                "cloudIoTDevicesGetSensorMap", sleeptrackerProcessorID=processor_id
            ),
        )
        return data.get("sensorMap") or []

    async def get_environment(self, processor_id: int) -> dict[str, float]:
        """Return the latest valid environment readings keyed by type."""
        data = await self._post(
            f"{self._processor_url}/latestEnvironmentSensorData",
            self._payload("environmentalData", sleeptrackerProcessorID=processor_id),
        )
        result: dict[str, float] = {}
        for key in ("degreesCelsius", "humidityPercentage", "co2Ppm", "vocPpb"):
            reading = data.get(key)
            if isinstance(reading, dict) and reading.get("status") == "valid":
                result[key] = round(float(reading["value"]), 1)
        return result

    async def get_snore_relief(self) -> dict[str, bool]:
        """Return the account's snore relief settings."""
        data = await self._post(f"{self._settings_url}/getSnoreRelief", {})
        return {
            "snoreReliefTilt": bool(data.get("snoreReliefTilt")),
            "snoreReliefVibration": bool(data.get("snoreReliefVibration")),
        }

    async def set_snore_relief(self, tilt: bool, vibration: bool) -> None:
        """Update the account's snore relief settings."""
        await self._post(
            f"{self._settings_url}/setSnoreRelief",
            self._payload(
                "setSnoreRelief",
                snoreReliefTilt=tilt,
                snoreReliefVibration=vibration,
            ),
        )

    async def send_command(
        self, command: Command, **extra: Any
    ) -> list[dict[str, Any]]:
        """Send a base command and return the status snapshots (one per side).

        The cloud applies the command to the side of the base that belongs to
        the logged-in account.
        """
        data = await self._post(
            f"{self._processor_url}/adjustableBaseControls",
            self._payload(
                "adjustableBaseControls", bedControlCommand=int(command), **extra
            ),
        )
        status_code = data.get("statusCode", 0)
        message = str(data.get("statusMessage") or "")
        if status_code not in (0, None) and not (
            command == Command.STATUS
            and status_code == _IGNORED_STATUS[0]
            and _IGNORED_STATUS[1] in message
        ):
            raise SleeptrackerError(
                f"Command {command.name} failed ({status_code}): {message}"
            )
        body = data.get("body") or {}
        return body.get("snapshots") or []
