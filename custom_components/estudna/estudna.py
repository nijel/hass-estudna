"""
CML - How to get value of water level for you eSTUDNA device

2022-05-17 v1-01
a) Project foundation
"""

from datetime import datetime
from typing import Dict, Optional

import jwt
import requests

# ----------------------------------------------------------------------------
# --- Code
# ----------------------------------------------------------------------------


class ThingsBoard:
    """
    CML ThinksBoard wrapper.
    """

    def __init__(self):
        self.server = "https://cml.seapraha.cz"
        self.userToken = None
        self.refreshToken = None
        self.customerId = None

    def http_request(
        self,
        method: str,
        url: str,
        header: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, str]] = None,
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

    def http_post(self, url: str, data: Dict[str, str], check_token: bool = True):
        return self.http_request("post", url, data=data, check_token=check_token)

    def http_get(
        self,
        url: str,
        params: Optional[Dict[str, str]] = None,
        check_token: bool = True,
    ):
        header = {"X-Authorization": f"Bearer {self.userToken}"}
        return self.http_request(
            "get", url, header=header, params=params, check_token=check_token
        )

    def login(self, username: str, password: str):
        """Login"""
        # Get access and refresh tokens
        url = "/api/auth/login"
        response = self.http_post(
            url, data={"username": username, "password": password}, check_token=False
        )
        self.userToken = response["token"]
        self.refreshToken = response["refreshToken"]

        # Get customer ID
        url = "/api/auth/user"
        response = self.http_get(url)
        self.customerId = response["customerId"]["id"]

    def refresh_token(self):
        """Refresh JWT token"""
        url = "/api/auth/token"
        response = self.http_post(
            url, data={"refreshToken": self.refreshToken}, check_token=False
        )
        self.userToken = response["token"]
        self.refreshToken = response["refreshToken"]

    @property
    def token_expired(self):
        """Check JWT token expiry"""
        this_jwt = jwt.decode(self.userToken, options={"verify_signature": False})
        expiry_time = datetime.fromtimestamp(this_jwt["exp"])
        return expiry_time <= datetime.now()

    def get_devices(self):
        """List devices"""
        url = f"/api/customer/{self.customerId}/devices"
        params = {"pageSize": 100, "page": 0}
        response = self.http_get(url, params=params)
        if response["totalElements"] < 1:
            raise Exception("No device has not been found!")

        return response["data"]

    def get_device_values(self, device_id: str, keys: str):
        """Get current values"""
        url = f"/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries"
        params = {"keys": keys}
        response = self.http_get(url, params=params)

        return response

    def get_estudna_level(self, device_id: str):
        values = self.get_device_values(device_id, "ain1")
        return values["ain1"][0]["value"]
