"""CML - How to get value of water level for you eSTUDNA device.

2022-05-17 v1-01
a) Project foundation
"""

import json
from datetime import datetime

import jwt
import requests

# ----------------------------------------------------------------------------
# --- Code
# ----------------------------------------------------------------------------


class ThingsBoard:
    """CML ThinksBoard wrapper."""

    def __init__(self, device_type: str = "estudna"):
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

    def http_request(
        self,
        method: str,
        url: str,
        header: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        check_token: bool = True,
    ):
        if check_token and self.token_expired:
            self.refresh_token()
        if header is None:
            header = {}

        header.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        response = requests.request(
            method, f"{self.server}{url}", headers=header, params=params, json=data
        )
        response.raise_for_status()
        return response.json()

    def http_post(self, url: str, data: dict[str, str], check_token: bool = True):
        return self.http_request("post", url, data=data, check_token=check_token)

    def http_get(
        self,
        url: str,
        params: dict[str, str] | None = None,
        check_token: bool = True,
    ):
        header = {"X-Authorization": f"Bearer {self.userToken}"}
        return self.http_request(
            "get", url, header=header, params=params, check_token=check_token
        )

    def login(self, username: str, password: str):
        """Login."""
        # Get access and refresh tokens
        if self.device_type == "estudna2":
            url = "/apiv2/auth/login"
        else:
            url = "/api/auth/login"

        response = self.http_post(
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
            response = self.http_get(url)
            self.customerId = response["customerId"]["id"]

    def refresh_token(self):
        """Refresh JWT token."""
        if self.device_type == "estudna2":
            url = "/apiv2/auth/token"
        else:
            url = "/api/auth/token"

        response = self.http_post(
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

    def get_devices(self):
        """List devices."""
        if self.device_type == "estudna2":
            if not self.user_id:
                raise ValueError("No user_id. Please login first.")
            url = f"/apiv2/user/{self.user_id}/devices"
            response = self.http_get(url)
            devices = (
                response if isinstance(response, list) else response.get("data", [])
            )
        else:
            url = f"/api/customer/{self.customerId}/devices"
            params = {"pageSize": 100, "page": 0}
            response = self.http_get(url, params=params)
            devices = response.get("data", [])

        if not devices:
            raise Exception("No device has not been found!")  # noqa: TRY002

        return devices

    def get_device_values(self, device_id: str, keys: str):
        """Get current values."""
        if self.device_type == "estudna2":
            url = f"/apiv2/device/{device_id}/latest"
            return self.http_get(url)
        url = f"/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries"
        params = {"keys": keys}
        return self.http_get(url, params=params)

    def get_estudna_level(self, device_id: str):
        values = self.get_device_values(device_id, "ain1")

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

    def get_relay_state(self, device_id: str, relay: str):
        """Get relay state (OUT1 or OUT2)."""
        # eSTUDNA2 doesn't support relays yet
        if self.device_type == "estudna2":
            return False

        # State keys are lowercase: dout1, dout2
        state_key = "dout1" if relay == "OUT1" else "dout2"
        values = self.get_device_values(device_id, state_key)
        if state_key in values and len(values[state_key]) > 0:
            # Values are string "1" (on) or "0" (off)
            return values[state_key][0]["value"] == "1"
        return False

    def set_relay_state(self, device_id: str, relay: str, state: bool):
        """Set relay state (OUT1 or OUT2)."""
        # eSTUDNA2 doesn't support relays yet
        if self.device_type == "estudna2":
            return None

        method = "setDout1" if relay == "OUT1" else "setDout2"
        data = {"method": method, "params": state}
        url = f"/api/rpc/twoway/{device_id}"
        header = {"X-Authorization": f"Bearer {self.userToken}"}
        return self.http_request("post", url, header=header, data=data)
