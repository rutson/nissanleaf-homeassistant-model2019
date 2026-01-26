# Nissan Connect – Home Assistant Integration

## Overview

This custom Home Assistant integration allows you to retrieve **battery and charging status information from Nissan EVs** (such as Nissan Leaf and Ariya) via the **Nissan Connect cloud API**.

The integration is deliberately designed as a **cloud polling** integration:
- No direct connection to the vehicle
- No forced vehicle wake-ups
- Respects Nissan backend caching behavior

This makes the integration **stable, energy-efficient, and API-friendly**.

---

## Functionality

Per vehicle, the integration provides sensors such as:

- Battery state of charge (SOC)
- Remaining driving range (with and without HVAC)
- Charging status
- Plug / cable connection status
- Battery capacity
- Timestamp of the last Nissan backend update

Sensors are **always created**, even when data is temporarily unavailable.

---

## Architecture Overview

```
Home Assistant
│
├── config_flow.py
│   └── UI configuration and authentication
│
├── api.py
│   └── NissanConnectApi
│       ├── login()
│       ├── _get_access_token()
│       ├── get_vehicles()
│       └── get_battery_status()
│
├── __init__.py
│   └── Integration setup
│       └── DataUpdateCoordinator
│
└── sensor.py
    └── NissanBatterySensor (CoordinatorEntity)
```

---

## Files

### manifest.json

Defines the integration for Home Assistant.

Key properties:
- `iot_class: cloud_polling`
- `config_flow: true`
- No local hardware dependencies

---

### config_flow.py

Handles configuration via the Home Assistant UI.

Workflow:
1. User enters Nissan Connect username and password
2. Authentication is tested immediately
3. A config entry is created only on success

No sensors or vehicles are created at this stage.

---

### api.py – NissanConnectApi

Contains all communication with the Nissan backend.

#### Responsibilities
- OAuth authentication
- Access token management
- Vehicle discovery
- Battery status retrieval

#### Key methods

- `login()` – executes the full Nissan OAuth flow
- `get_vehicles()` – retrieves and stores vehicle metadata
- `get_battery_status(vin, can_generation, model)` – retrieves battery status

The API **never forces a vehicle wake-up** and only reads Nissan backend cache.

---

### __init__.py

Handles integration setup and periodic updates.

Responsibilities:
- Initialize `NissanConnectApi`
- Store vehicle list
- Set up `DataUpdateCoordinator`

Key design principle:
> Sensor creation is **not dependent on data availability**.

Polling interval:
- Default: every 15 minutes

---

### sensor.py

Defines all sensors per vehicle.

#### Sensor creation

- Sensors are created based on the vehicle list
- Not based on live battery data
- Ensures entity stability

#### Value handling

- Last known value is retained
- No new Nissan data → value remains unchanged
- New Nissan data → sensor updates

This prevents entity flapping and inconsistent dashboards.

---

## Class and Method Diagram

```
NissanConnectApi
├── login()
├── _get_auth_id()
├── _submit_credentials()
├── _get_access_token()
├── get_vehicles()
└── get_battery_status()

DataUpdateCoordinator
├── async_refresh()
└── _async_update_data()

NissanBatterySensor (CoordinatorEntity)
├── native_value
├── available
└── extra_state_attributes
```

---

## Polling and Cache Behavior

The Nissan backend returns cached data.

Example log entry:

```
Battery cache age: 307 s (status=0)
```

Meaning:
- Data is approximately 5 minutes old
- Nissan considers the data valid
- The vehicle is not contacted again

Home Assistant cannot and should not override this behavior.

---

## Limitations

- Driving the vehicle does not always trigger a backend update
- The Nissan mobile app may show live data without a backend refresh
- Home Assistant only sees backend-published data

These are Nissan Connect platform limitations, not integration bugs.

---

## Summary

This integration:
- follows Home Assistant best practices
- avoids unnecessary vehicle wake-ups
- provides stable entities
- is suitable for charging monitoring and energy management

Well-suited for long-term, reliable Home Assist