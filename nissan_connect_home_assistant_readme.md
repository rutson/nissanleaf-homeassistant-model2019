# Nissan Connect – Home Assistant integratie

## Overzicht

Deze custom Home Assistant integratie maakt het mogelijk om **accu- en laadstatusinformatie van Nissan EV’s** (zoals Nissan Leaf en Ariya) uit te lezen via de **Nissan Connect cloud API**.

De integratie is bewust ontworpen als **cloud polling** integratie:
- Geen directe verbinding met de auto
- Geen geforceerde wake-ups
- Respecteert Nissan backend caching

Hierdoor is de integratie **betrouwbaar, energiezuinig en API-vriendelijk**.

---

## Functionaliteit

De integratie levert per voertuig o.a. de volgende sensoren:

- Accupercentage (SOC)
- Actieradius (met en zonder HVAC)
- Laadstatus
- Stekkerstatus
- Accucapaciteit
- Laatste Nissan backend update

Sensoren bestaan **altijd**, ook als er tijdelijk geen data beschikbaar is.

---

## Architectuuroverzicht

```
Home Assistant
│
├── config_flow.py
│   └── UI-configuratie en authenticatie
│
├── api.py
│   └── NissanConnectApi
│       ├── login()
│       ├── _get_access_token()
│       ├── get_vehicles()
│       └── get_battery_status()
│
├── __init__.py
│   └── Integratie setup
│       └── DataUpdateCoordinator
│
└── sensor.py
    └── NissanBatterySensor (CoordinatorEntity)
```

---

## Bestanden

### manifest.json

Definieert de integratie voor Home Assistant.

Belangrijkste eigenschappen:
- `iot_class: cloud_polling`
- `config_flow: true`
- Geen lokale hardware afhankelijkheden

---

### config_flow.py

Verzorgt de configuratie via de Home Assistant UI.

Workflow:
1. Gebruiker voert Nissan Connect gebruikersnaam en wachtwoord in
2. Authenticatie wordt direct getest
3. Alleen bij succes wordt een config entry aangemaakt

Er worden hier **nog geen sensoren** of voertuigen aangemaakt.

---

### api.py – NissanConnectApi

Bevat alle communicatie met de Nissan backend.

#### Belangrijkste verantwoordelijkheden
- OAuth authenticatie
- Beheren van access tokens
- Ophalen van voertuigen
- Ophalen van batterijstatus

#### Belangrijke methodes

- `login()` – doorloopt volledige Nissan OAuth flow
- `get_vehicles()` – haalt voertuigen op en slaat ze lokaal op
- `get_battery_status(vin, can_generation, model)` – haalt batterijstatus op

De API **forceert nooit** een voertuig-wake-up en leest uitsluitend backend cache.

---

### __init__.py

Regelt de setup van de integratie en de periodieke updates.

Taken:
- Initialiseren van NissanConnectApi
- Opslaan van voertuiglijst
- Opzetten van DataUpdateCoordinator

Belangrijk ontwerpprincipe:
> Sensorcreatie is **niet afhankelijk van data beschikbaarheid**.

Polling-interval:
- Standaard: elke 15 minuten

---

### sensor.py

Definieert alle sensoren per voertuig.

#### Sensorcreatie

- Sensoren worden aangemaakt op basis van de voertuiglijst
- Niet op basis van actuele batterijdata
- Hierdoor blijven entiteiten stabiel

#### Waardelogica

- Laatste bekende waarde wordt onthouden
- Geen nieuwe Nissan data → waarde blijft gelijk
- Nieuwe Nissan data → sensor update

Dit voorkomt flapping en inconsistente dashboards.

---

## Klassen- en methodeschema

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

## Polling en cachegedrag

Nissan backend levert gecachte data.

Voorbeeld log:

```
Battery cache age: 307 s (status=0)
```

Betekenis:
- Data is ~5 minuten oud
- Nissan beschouwt deze data als geldig
- Auto is niet opnieuw benaderd

Home Assistant kan dit niet forceren en dat is bewust zo.

---

## Beperkingen

- Rijden met de auto triggert niet altijd een backend update
- Nissan app kan live data tonen zonder backend update
- Home Assistant ziet uitsluitend backend data

Dit is een beperking van Nissan Connect, niet van deze integratie.

---

## Samenvatting

Deze integratie:
- volgt Home Assistant best practices
- vermijdt onnodige voertuig-wake-ups
- levert stabiele sensoren
- is geschikt voor laadmonitoring en energiebeheer

Ideaal voor gebruik in automations rondom laden en energiebeheer.

