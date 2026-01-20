"""Async API client for Nissan Connect."""
import aiohttp
import asyncio
import json
import time
import urllib.parse
import logging
from typing import Dict, List, Optional, Any

_logger = logging.getLogger(__name__)


class NissanConnectApi:
    """Async session for interacting with NissanConnect/Kamereon API."""

    def __init__(self, username: str, password: str, debug: bool = False):
        self.debug = debug
        self.username = username
        self.password = password
        self.bearer_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.vehicles: List[Dict[str, Any]] = []
        self.vehicle: Optional[Dict[str, Any]] = None

        # API Configuration for EU region
        self.settings = {
            'client_id': 'a-ncb-nc-android-prod',
            'client_secret': '6GKIax7fGT5yPHuNmWNVOc4q5POBw1WRSW39ubRA8WPBmQ7MOxhm75EsmKMKENem',
            'scope': 'openid profile vehicles',
            'auth_base_url': 'https://prod.eu2.auth.kamereon.org/kauth/',
            'realm': 'a-ncb-prod',
            'redirect_uri': 'org.kamereon.service.nci:/oauth2redirect',
            'car_adapter_base_url': 'https://alliance-platform-caradapter-prod.apps.eu2.kamereon.io/car-adapter/',
            'user_adapter_base_url': 'https://alliance-platform-usersadapter-prod.apps.eu2.kamereon.io/user-adapter/',
            'user_base_url': 'https://nci-bff-web-prod.apps.eu2.kamereon.io/bff-web/'
        }

        self.api_version = 'protocol=1.0,resource=2.1'

    async def _request(self, session: aiohttp.ClientSession, endpoint: str, method: str = 'POST',
                      additional_headers: Optional[Dict[str, str]] = None,
                      params: Optional[Dict[str, Any]] = None,
                      allow_redirects: bool = True) -> Dict[str, Any]:
        """Make a single API request."""
        headers = {}
        if self.bearer_token:
            headers['Authorization'] = f'Bearer {self.bearer_token}'

        if additional_headers:
            headers.update(additional_headers)

        try:
            timeout = aiohttp.ClientTimeout(total=60)  # 1 minute timeout
            if method.upper() == 'GET':
                async with session.get(endpoint, headers=headers, allow_redirects=allow_redirects, timeout=timeout) as response:
                    status_code = response.status
                    try:
                        json_data = await response.json()
                    except aiohttp.ContentTypeError:
                        json_data = None
                    return {
                        'status_code': status_code,
                        'headers': dict(response.headers),
                        'body': json_data
                    }
            else:
                content_type = headers.get('Content-Type', 'application/json')
                if 'application/x-www-form-urlencoded' in content_type and params:
                    data = urllib.parse.urlencode(params)
                else:
                    data = json.dumps(params) if params else None
                async with session.post(endpoint, headers=headers, data=data, timeout=timeout) as response:
                    status_code = response.status
                    try:
                        json_data = await response.json()
                    except aiohttp.ContentTypeError:
                        json_data = None
                    return {
                        'status_code': status_code,
                        'headers': dict(response.headers),
                        'body': json_data
                    }

        except aiohttp.ClientError as e:
            raise

    async def request_with_retry(self, session: aiohttp.ClientSession, endpoint: str, method: str = 'POST',
                                additional_headers: Optional[Dict[str, str]] = None,
                                params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make an API request with automatic retry on authentication failures."""
        response = await self._request(session, endpoint, method, additional_headers, params)

        if response.get('status_code', 200) >= 400:
            await self.login()
            response = await self._request(session, endpoint, method, additional_headers, params)

        return response

    async def login(self) -> None:
        """Authenticate with NissanConnect and retrieve vehicle information."""
        _logger.info("Starting Nissan Connect login")
        async with aiohttp.ClientSession() as session:
            # Step 1: Get authId with anonymous credentials
            _logger.info("Step 1: Getting authId")
            response = await self._request(
                session,
                endpoint=f"{self.settings['auth_base_url']}json/realms/root/realms/{self.settings['realm']}/authenticate",
                additional_headers={
                    'Accept-Api-Version': self.api_version,
                    'X-Username': 'anonymous',
                    'X-Password': 'anonymous',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            )
            _logger.info(f"Step 1 response status: {response['status_code']}")
            if response['body'] and 'authId' in response['body']:
                _logger.info("Step 1: Got authId")
            else:
                _logger.error(f"Step 1 failed: body keys: {list(response['body'].keys()) if response['body'] else 'None'}")

            auth_id = response['body']['authId']

            # Step 2: Submit username/password (with retry for 401 errors)
            _logger.info("Step 2: Authenticating with username/password")
            retries = 5
            while retries > 0:
                _logger.info(f"Step 2 attempt, retries left: {retries}")
                response = await self._request(
                    session,
                    endpoint=f"{self.settings['auth_base_url']}json/realms/root/realms/{self.settings['realm']}/authenticate",
                    additional_headers={
                        'Accept-Api-Version': self.api_version,
                        'X-Username': 'anonymous',
                        'X-Password': 'anonymous',
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    params={
                        'authId': auth_id,
                        'template': '',
                        'stage': 'LDAP1',
                        'header': 'Sign in',
                        'callbacks': [
                            {
                                'type': 'NameCallback',
                                'output': [{'name': 'prompt', 'value': 'User Name:'}],
                                'input': [{'name': 'IDToken1', 'value': self.username}]
                            },
                            {
                                'type': 'PasswordCallback',
                                'output': [{'name': 'prompt', 'value': 'Password:'}],
                                'input': [{'name': 'IDToken2', 'value': self.password}]
                            }
                        ]
                    }
                )
                _logger.info(f"Step 2 response status: {response['status_code']}")

                if response['status_code'] != 401:
                    _logger.info("Step 2: Authentication successful")
                    break
                retries -= 1
                _logger.info(f"Step 2: 401 received, retrying in 2 seconds")
                await asyncio.sleep(2)  # Brief pause before retry

            auth_cookie = response['body']['tokenId']
            _logger.info("Step 2: Got auth cookie")

            # Step 3: Get authorization code
            _logger.info("Step 3: Getting authorization code")
            response = await self._request(
                session,
                endpoint=f"{self.settings['auth_base_url']}oauth2/{self.settings['realm']}/authorize?"
                        f"client_id={self.settings['client_id']}&"
                        f"redirect_uri={self.settings['redirect_uri']}&"
                        f"response_type=code&"
                        f"scope={self.settings['scope']}&"
                        f"nonce=sdfdsfez&"
                        f"state=af0ifjsldkj",
                additional_headers={
                    'Cookie': f'i18next=en-UK; amlbcookie=05; kauthSession="{auth_cookie}"'
                },
                method='GET',
                allow_redirects=False
            )
            _logger.info(f"Step 3 response status: {response['status_code']}")
            code = ""
            if response['status_code'] == 302:
                location = response['headers'].get('Location', '')
                _logger.info(f"Step 3 location: {location}")
                if 'code=' in location:
                    code = location.split('code=')[1].split('&')[0]
                    _logger.info("Step 3: Got authorization code")
                else:
                    _logger.error("Step 3: No code in location")

            if not code:
                raise Exception("Failed to obtain authorization code")

            # Step 4: Exchange code for access token
            _logger.info("Step 4: Exchanging code for access token")
            response = await self._request(
                session,
                endpoint=f"{self.settings['auth_base_url']}oauth2/{self.settings['realm']}/access_token?"
                        f"code={code}&"
                        f"client_id={self.settings['client_id']}&"
                        f"client_secret={self.settings['client_secret']}&"
                        f"redirect_uri={self.settings['redirect_uri']}&"
                        f"grant_type=authorization_code",
                additional_headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            )
            _logger.info(f"Step 4 response status: {response['status_code']}")
            if response['body']:
                _logger.info(f"Step 4 body keys: {list(response['body'].keys()) if isinstance(response['body'], dict) else type(response['body'])}")
            else:
                _logger.error("Step 4: No response body")

            self.bearer_token = response['body']['access_token']
            _logger.info("Step 4: Got access token")

            # Step 5: Get user information
            _logger.info("Step 5: Getting user information")
            response = await self._request(
                session,
                endpoint=f"{self.settings['user_adapter_base_url']}v1/users/current",
                method='GET'
            )
            _logger.info(f"Step 5 response status: {response['status_code']}")

            self.user_id = response['body']['userId']
            _logger.info(f"Step 5: Got user ID: {self.user_id}")

            # Step 6: Get vehicles
            _logger.info("Step 6: Getting vehicles")
            response = await self._request(
                session,
                endpoint=f"{self.settings['user_base_url']}v5/users/{self.user_id}/cars",
                method='GET'
            )
            _logger.info(f"Step 6 response status: {response['status_code']}")
            if response['body'] and 'data' in response['body']:
                _logger.info(f"Step 6: Found {len(response['body']['data'])} vehicles")

            self.vehicles = []
            for vehicle_data in response['body']['data']:
                vehicle = {
                    'vin': vehicle_data['vin'],
                    'model_name': vehicle_data['modelName'],
                    'nickname': vehicle_data.get('nickname', f"{vehicle_data['modelName']} {len(self.vehicles) + 1}"),
                    'can_generation': vehicle_data['canGeneration'],
                    'services': vehicle_data.get('services', [])
                }
                self.vehicles.append(vehicle)

            self.vehicle = self.vehicles[0] if self.vehicles else None
            _logger.info(f"Login completed successfully with {len(self.vehicles)} vehicles")

    async def get_battery_status(self, vin: str, can_generation: str, model_name: str) -> Dict[str, Any]:
        """Get battery status for a vehicle."""
        _logger.info(f"Getting battery status for VIN: {vin}")
        async with aiohttp.ClientSession() as session:
            if model_name.lower() == 'ariya':
                endpoint = f"{self.settings['user_base_url']}v3/cars/{vin}/battery-status?canGen={can_generation}"
            else:
                endpoint = f"{self.settings['car_adapter_base_url']}v1/cars/{vin}/battery-status"

            _logger.info(f"Battery endpoint: {endpoint}")
            response = await self.request_with_retry(session, endpoint, method='GET')
            _logger.info(f"Battery response status: {response['status_code']}")
            return response['body']