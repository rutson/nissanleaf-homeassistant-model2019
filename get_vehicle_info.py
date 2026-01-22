#!/usr/bin/env python3
"""
NissanConnect Vehicle Information Retrieval
Python implementation of the NissanConnect API authentication and vehicle data access.
For proper function add credentials where mentioned (Nissan login)cd
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any


class NissanConnectSession:
    """Session for interacting with NissanConnect/Kamereon API."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.username: Optional[str] = None
        self.password: Optional[str] = None
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
        self.debug_log: List[str] = []

    def _print(self, message: str) -> None:
        """Print debug messages if debug mode is enabled."""
        if self.debug:
            print(f"$ {message}")
            self.debug_log.append(f"$ {message}")

    def request_with_retry(self, endpoint: str, method: str = 'POST',
                          additional_headers: Optional[Dict[str, str]] = None,
                          params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make an API request with automatic retry on authentication failures."""
        response = self.request(endpoint, method, additional_headers, params)

        if response.get('status_code', 200) >= 400:
            self._print('Signing in and trying request again')
            self.login(self.username, self.password)
            response = self.request(endpoint, method, additional_headers, params)

        return response

    def request(self, endpoint: str, method: str = 'POST',
               additional_headers: Optional[Dict[str, str]] = None,
               params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a single API request."""
        self._print(f'Invoking NissanConnect/Kamereon API: {endpoint}')
        self._print(f'Params: {params}')

        headers = {}
        if self.bearer_token:
            headers['Authorization'] = f'Bearer {self.bearer_token}'

        if additional_headers:
            headers.update(additional_headers)

        self._print(f'Headers: {headers}')

        try:
            if method.upper() == 'GET':
                response = requests.get(endpoint, headers=headers)
            else:
                headers['Content-Type'] = 'application/json'
                response = requests.post(endpoint, headers=headers,
                                       data=json.dumps(params) if params else None)

            self._print(f'Status Code: {response.status_code}')

            # Try to parse JSON response
            try:
                json_data = response.json()
                self._print(f'Result: {json_data}')
            except json.JSONDecodeError:
                json_data = None
                self._print('JSON decoding failed!')

            return {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': json_data
            }

        except requests.RequestException as e:
            self._print(f'Request failed: {e}')
            raise

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate with NissanConnect and retrieve vehicle information."""
        self.username = username
        self.password = password
        self.bearer_token = None

        # Step 1: Get authId with anonymous credentials
        self._print('Step 1: Getting authId')
        response = self.request(
            endpoint=f"{self.settings['auth_base_url']}json/realms/root/realms/{self.settings['realm']}/authenticate",
            additional_headers={
                'Accept-Api-Version': self.api_version,
                'X-Username': 'anonymous',
                'X-Password': 'anonymous',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )

        auth_id = response['body']['authId']
        self._print(f'Got authId: {auth_id}')

        # Step 2: Submit username/password (with retry for 401 errors)
        retries = 10
        while retries > 0:
            self._print(f'Step 2: Authenticating (retries left: {retries})')
            response = self.request(
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
                            'input': [{'name': 'IDToken1', 'value': username}]
                        },
                        {
                            'type': 'PasswordCallback',
                            'output': [{'name': 'prompt', 'value': 'Password:'}],
                            'input': [{'name': 'IDToken2', 'value': password}]
                        }
                    ]
                }
            )

            if response['status_code'] != 401:
                break
            retries -= 1
            time.sleep(1)  # Brief pause before retry

        auth_cookie = response['body']['tokenId']
        self._print(f'Got auth cookie: {auth_cookie}')

        # Step 3: Get authorization code (this may throw an exception we parse)
        self._print('Step 3: Getting authorization code')
        code = ""
        try:
            response = self.request(
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
                method='GET'
            )
        except Exception as e:
            # Parse the code from the exception message (as done in Dart version)
            error_msg = str(e)
            if '=' in error_msg and '&' in error_msg:
                code = error_msg.split('=')[1].split('&')[0]
                self._print(f'Extracted code from error: {code}')

        if not code:
            raise Exception("Failed to obtain authorization code")

        # Step 4: Exchange code for access token
        self._print('Step 4: Exchanging code for access token')
        response = self.request(
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

        self.bearer_token = response['body']['access_token']
        self._print('Got access token')

        # Step 5: Get user information
        self._print('Step 5: Getting user information')
        response = self.request(
            endpoint=f"{self.settings['user_adapter_base_url']}v1/users/current",
            method='GET'
        )

        self.user_id = response['body']['userId']
        self._print(f'User ID: {self.user_id}')

        # Step 6: Get vehicles
        self._print('Step 6: Getting vehicles')
        response = self.request(
            endpoint=f"{self.settings['user_base_url']}v5/users/{self.user_id}/cars",
            method='GET'
        )

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
        self._print(f'Found {len(self.vehicles)} vehicles')

        return self.vehicle

    def get_battery_status(self, vin: str, can_generation: str, model_name: str) -> Dict[str, Any]:
        """Get battery status for a vehicle."""
        if model_name.lower() == 'ariya':
            endpoint = f"{self.settings['user_base_url']}v3/cars/{vin}/battery-status?canGen={can_generation}"
        else:
            endpoint = f"{self.settings['car_adapter_base_url']}v1/cars/{vin}/battery-status"

        response = self.request_with_retry(endpoint, method='GET')
        return response['body']


def main():
    """Main function to demonstrate vehicle information retrieval."""
    # Create session with debug enabled
    session = NissanConnectSession(debug=True)
    user=input("Username: ")
    passw=input("Password: ")
    try:
        # Login with provided credentials
        print("Authenticating with NissanConnect...")
        vehicle = session.login(
            username=user,
            password=passw
        )

        if not vehicle:
            print("No vehicles found!")
            return

        print(f"\nConnected to vehicle: {vehicle['nickname']}")
        print(f"Model: {vehicle['model_name']}")
        print(f"VIN: {vehicle['vin']}")
        print(f"CAN Generation: {vehicle['can_generation']}")

        # Get battery status
        print("\nRetrieving battery status...")
        try:
            battery_data = session.get_battery_status(
                vehicle['vin'],
                vehicle['can_generation'],
                vehicle['model_name']
            )
            print("Battery data retrieved successfully!")
            print(json.dumps(battery_data, indent=2))
        except Exception as e:
            print(f"Failed to get battery status: {e}")

        # Show all vehicles
        print(f"\nTotal vehicles: {len(session.vehicles)}")
        for i, veh in enumerate(session.vehicles, 1):
            print(f"{i}. {veh['nickname']} ({veh['model_name']}) - {veh['vin']}")

    except Exception as e:
        print(f"Error: {e}")
        if session.debug_log:
            print("\nDebug log:")
            for log_entry in session.debug_log[-10:]:  # Show last 10 entries
                print(log_entry)


if __name__ == "__main__":
    main()