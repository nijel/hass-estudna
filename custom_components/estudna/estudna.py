"""CML - How to get value of water level for you eSTUDNA device.

2022-05-17 v1-01
a) Project foundation
"""

import json
from datetime import datetime

import aiohttp
import jwt

# ----------------------------------------------------------------------------
# --- Code
# ----------------------------------------------------------------------------


class ThingsBoard:
    """CML ThinksBoard wrapper."""

    def __init__(
        self, device_type: str = "estudna", session: aiohttp.ClientSession | None = None
    ):
        """Initialize ThingsBoard with device type."""
        self.device_type = device_type
        if device_type == "estudna2":
            self.server = "https://cml5.seapraha.cz"
        else:
            self.server = "https://cml.seapraha.cz"
        self.userToken = None
        self.refreshToken = None
        self.customerId = None
        self.user_id = None
        self._session = session
        self._own_session = session is None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the aiohttp session if we own it."""
        if self._own_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def http_request(
        self,
        method: str,
        url: str,
        header: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        check_token: bool = True,
    ):
        if check_token and self.token_expired:
            await self.refresh_token()
        if header is None:
            header = {}

        header.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        session = await self._get_session()
        async with session.request(
            method, f"{self.server}{url}", headers=header, params=params, json=data
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def http_post(self, url: str, data: dict[str, str], check_token: bool = True):
        return await self.http_request("post", url, data=data, check_token=check_token)

    async def http_get(
        self,
        url: str,
        params: dict[str, str] | None = None,
        check_token: bool = True,
    ):
        header = {"X-Authorization": f"Bearer {self.userToken}"}
        return await self.http_request(
            "get", url, header=header, params=params, check_token=check_token
        )

    async def login(self, username: str, password: str):
        """Login."""
        # Get access and refresh tokens
        if self.device_type == "estudna2":
            url = "/apiv2/auth/login"
        else:
            url = "/api/auth/login"

        response = await self.http_post(
            url, data={"username": username, "password": password}, check_token=False
        )
        self.userToken = response["token"]
        self.refreshToken = response["refreshToken"]

        # Get customer ID or user ID depending on device type
        if self.device_type == "estudna2":
            self.user_id = response.get("user_id")
            if not self.user_id:
                raise ValueError("Login failed: missing user_id")
        else:
            url = "/api/auth/user"
            response = await self.http_get(url)
            self.customerId = response["customerId"]["id"]

    async def refresh_token(self):
        """Refresh JWT token."""
        if self.device_type == "estudna2":
            url = "/apiv2/auth/token"
        else:
            url = "/api/auth/token"

        response = await self.http_post(
            url, data={"refreshToken": self.refreshToken}, check_token=False
        )
        self.userToken = response["token"]
        self.refreshToken = response["refreshToken"]

    @property
    def token_expired(self):
        """Check JWT token expiry."""
        this_jwt = jwt.decode(self.userToken, options={"verify_signature": False})
        expiry_time = datetime.fromtimestamp(this_jwt["exp"])
        return expiry_time <= datetime.now()

    async def get_devices(self):
        """List devices."""
        if self.device_type == "estudna2":
            if not self.user_id:
                raise ValueError("No user_id. Please login first.")
            url = f"/apiv2/user/{self.user_id}/devices"
            response = await self.http_get(url)
            devices = (
                response if isinstance(response, list) else response.get("data", [])
            )
        else:
            url = f"/api/customer/{self.customerId}/devices"
            params = {"pageSize": 100, "page": 0}
            response = await self.http_get(url, params=params)
            devices = response.get("data", [])

        if not devices:
            raise Exception("No device has not been found!")  # noqa: TRY002

        return devices

    async def get_device_values(self, device_id: str, keys: str):
        """Get current values."""
        if self.device_type == "estudna2":
            url = f"/apiv2/device/{device_id}/latest"
            return await self.http_get(url)
        url = f"/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries"
        params = {"keys": keys}
        return await self.http_get(url, params=params)

    async def get_estudna_level(self, device_id: str):
        values = await self.get_device_values(device_id, "ain1")

        if self.device_type == "estudna2":
            # eSTUDNA2 uses a different format with JSON-encoded values
            if not values or "ain1" not in values:
                return None

            raw = values["ain1"]
            if isinstance(raw, list) and raw:
                val_str = raw[0].get("value")
                try:
                    val_json = json.loads(val_str)
                    return float(val_json.get("str"))
                except (ValueError, TypeError, json.JSONDecodeError):
                    return None
            return None
        # Original eSTUDNA format
        return values["ain1"][0]["value"]

    async def get_relay_state(self, device_id: str, relay: str):
        """Get relay state (OUT1 or OUT2)."""
        # State keys are lowercase: dout1, dout2
        state_key = "dout1" if relay == "OUT1" else "dout2"
        values = await self.get_device_values(device_id, state_key)

        if self.device_type == "estudna2":
            # eSTUDNA2 API returns telemetry data differently
            if (
                state_key in values
                and isinstance(values[state_key], list)
                and values[state_key]
            ):
                value_entry = values[state_key][0].get("value")
                if value_entry:
                    # Parse JSON-encoded value if needed
                    try:
                        val_json = json.loads(value_entry)
                        return val_json.get("str") in {"1", "true"}
                    except (ValueError, TypeError, json.JSONDecodeError):
                        # Fallback to direct string comparison
                        return value_entry in {"1", "true"}
            return False

        # Original eSTUDNA format
        if state_key in values and len(values[state_key]) > 0:
            # Values are string "1" (on) or "0" (off)
            return values[state_key][0]["value"] == "1"
        return False

    async def set_relay_state(self, device_id: str, relay: str, state: bool):
        """Set relay state (OUT1 or OUT2)."""
        method = "setDout1" if relay == "OUT1" else "setDout2"
        data = {"method": method, "params": state}
        header = {"X-Authorization": f"Bearer {self.userToken}"}

        if self.device_type == "estudna2":
            # eSTUDNA2 uses /device/{id}/rpc/twoway endpoint
            url = f"/apiv2/device/{device_id}/rpc/twoway"
        else:
            # Original eSTUDNA uses /api/rpc/twoway/{id} endpoint
            url = f"/api/rpc/twoway/{device_id}"

        return await self.http_request("post", url, header=header, data=data)
