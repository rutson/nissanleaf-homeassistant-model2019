"""Async API client for Nissan Connect."""
import aiohttp
import json
import urllib.parse
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

_LOGGER = logging.getLogger(__name__)


class NissanConnectApi:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.bearer_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.vehicles: List[Dict[str, Any]] = []

        self.settings = {
            "client_id": "a-ncb-nc-android-prod",
            "client_secret": "6GKIax7fGT5yPHuNmWNVOc4q5POBw1WRSW39ubRA8WPBmQ7MOxhm75EsmKMKENem",
            "scope": "openid profile vehicles",
            "auth_base_url": "https://prod.eu2.auth.kamereon.org/kauth/",
            "realm": "a-ncb-prod",
            "redirect_uri": "org.kamereon.service.nci:/oauth2redirect",
            "car_adapter_base_url": "https://alliance-platform-caradapter-prod.apps.eu2.kamereon.io/car-adapter/",
            "user_adapter_base_url": "https://alliance-platform-usersadapter-prod.apps.eu2.kamereon.io/user-adapter/",
            "user_base_url": "https://nci-bff-web-prod.apps.eu2.kamereon.io/bff-web/",
        }

        self.api_version = "protocol=1.0,resource=2.1"

    async def _request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        method: str = "POST",
        additional_headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        allow_redirects: bool = True,
    ) -> Dict[str, Any]:

        headers = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        if additional_headers:
            headers.update(additional_headers)

        timeout = aiohttp.ClientTimeout(total=60)

        if method.upper() == "GET":
            async with session.get(
                endpoint,
                headers=headers,
                timeout=timeout,
                allow_redirects=allow_redirects,
            ) as response:
                try:
                    body = await response.json()
                except aiohttp.ContentTypeError:
                    body = None
                return {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "body": body,
                }

        content_type = headers.get("Content-Type", "application/json")
        if "application/x-www-form-urlencoded" in content_type and params:
            data = urllib.parse.urlencode(params)
        else:
            data = json.dumps(params) if params else None

        async with session.post(
            endpoint,
            headers=headers,
            data=data,
            timeout=timeout,
        ) as response:
            try:
                body = await response.json()
            except aiohttp.ContentTypeError:
                body = None
            return {
                "status_code": response.status,
                "headers": dict(response.headers),
                "body": body,
            }

    async def request_with_retry(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        method: str = "POST",
        additional_headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        allow_redirects: bool = True,
    ):
        response = await self._request(
            session, endpoint, method, additional_headers, params, allow_redirects
        )
        if response["status_code"] >= 400:
            await self.login()
            response = await self._request(
                session, endpoint, method, additional_headers, params, allow_redirects
            )
        return response

    async def login(self) -> None:
        _LOGGER.info("Nissan Connect login started")

        async with aiohttp.ClientSession() as session:

            # Step 1: request authId
            response = await self._request(
                session,
                f"{self.settings['auth_base_url']}json/realms/root/realms/{self.settings['realm']}/authenticate",
                additional_headers={
                    "Accept-Api-Version": self.api_version,
                    "X-Username": "anonymous",
                    "X-Password": "anonymous",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            auth_id = response["body"]["authId"]

            # Step 2: submit credentials
            response = await self._request(
                session,
                f"{self.settings['auth_base_url']}json/realms/root/realms/{self.settings['realm']}/authenticate",
                additional_headers={
                    "Accept-Api-Version": self.api_version,
                    "X-Username": "anonymous",
                    "X-Password": "anonymous",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                params={
                    "authId": auth_id,
                    "callbacks": [
                        {
                            "type": "NameCallback",
                            "input": [{"name": "IDToken1", "value": self.username}],
                        },
                        {
                            "type": "PasswordCallback",
                            "input": [{"name": "IDToken2", "value": self.password}],
                        },
                    ],
                },
            )
            auth_cookie = response["body"]["tokenId"]

            # Step 3: OAuth authorize (MUST NOT follow redirects)
            response = await self._request(
                session,
                f"{self.settings['auth_base_url']}oauth2/{self.settings['realm']}/authorize"
                f"?client_id={self.settings['client_id']}"
                f"&redirect_uri={self.settings['redirect_uri']}"
                f"&response_type=code"
                f"&scope={self.settings['scope']}",
                additional_headers={
                    "Cookie": f'kauthSession="{auth_cookie}"'
                },
                method="GET",
                allow_redirects=False,
            )

            location = response["headers"].get("Location")
            if not location or "code=" not in location:
                raise RuntimeError("OAuth redirect failed – no code returned")

            code = location.split("code=")[1].split("&")[0]

            # Step 4: exchange code for token
            response = await self._request(
                session,
                f"{self.settings['auth_base_url']}oauth2/{self.settings['realm']}/access_token",
                additional_headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                params={
                    "code": code,
                    "client_id": self.settings["client_id"],
                    "client_secret": self.settings["client_secret"],
                    "redirect_uri": self.settings["redirect_uri"],
                    "grant_type": "authorization_code",
                },
            )

            self.bearer_token = response["body"]["access_token"]

            # Step 5: get user
            response = await self._request(
                session,
                f"{self.settings['user_adapter_base_url']}v1/users/current",
                method="GET",
            )
            self.user_id = response["body"]["userId"]

            # Step 6: get vehicles
            response = await self._request(
                session,
                f"{self.settings['user_base_url']}v5/users/{self.user_id}/cars",
                method="GET",
            )

            self.vehicles = []
            for v in response["body"]["data"]:
                self.vehicles.append(
                    {
                        "vin": v["vin"],
                        "model_name": v["modelName"],
                        "nickname": v.get("nickname", v["modelName"]),
                        "can_generation": v["canGeneration"],
                    }
                )

            _LOGGER.info("Login successful, %d vehicle(s)", len(self.vehicles))

    async def get_battery_status(
        self, vin: str, can_generation: str, model_name: str
    ) -> Dict[str, Any]:

        async with aiohttp.ClientSession() as session:
            if model_name.lower() == "ariya":
                endpoint = (
                    f"{self.settings['user_base_url']}"
                    f"v3/cars/{vin}/battery-status?canGen={can_generation}"
                )
            else:
                endpoint = (
                    f"{self.settings['car_adapter_base_url']}"
                    f"v1/cars/{vin}/battery-status"
                )

            # Try to bypass upstream caching by requesting fresh data
            additional_headers = {
                "Accept": "application/json",
                "Cache-Control": "no-cache, no-store, max-age=0",
                "Pragma": "no-cache",
            }

            response = await self.request_with_retry(
                session, endpoint, method="GET", additional_headers=additional_headers
            )
            body = response.get("body", {})

            attrs = body.get("data", {}).get("attributes", {})
            last_update = attrs.get("lastUpdateTime")

            if last_update:
                ts = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - ts).total_seconds()
                _LOGGER.debug(
                    "Battery cache age for %s: %.0f s (status=%s)",
                    vin,
                    age,
                    attrs.get("chargeStatus"),
                )

            return body