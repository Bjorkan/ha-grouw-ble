<p align="left">
  <img src="custom_components/grouw_ble_mower/brand/logo.png" alt="Grouw logo" width="200"/>
</p>

# Grouw Mower til Home Assistant

[English](README.md) | [Svenska](README_sv.md)

Tilpasset Home Assistant-integration til lokal Bluetooth-styring af Grouw
robotplæneklippere, der bruger Daye Power-appen
(`com.dayepower.dayeappleaf`).

Integrationen bruger Home Assistants Bluetooth-manager til at finde enheder via
adresse. Den kører ikke sin egen scanner, så samme kodevej kan fungere med en
lokal Bluetooth-adapter eller en tilslutningsbar Home Assistant
Bluetooth-proxy. BLE-kommunikation og Daye/Grouw-protokolhåndtering leveres af
Python-biblioteket `pygrouw`:
[GitHub](https://github.com/Bjorkan/pyGrouw) |
[PyPI](https://pypi.org/project/pygrouw/).

## Nuværende status

Projektet retter sig i øjeblikket mod DYM-generationen af plæneklippere, som
ses i Daye Power-APK'en og i redigerede hardware-captures.

Bekræftede målsignaler:

- APK-version `2.0.1`, versionskode `117`.
- BLE-navne: `Robot Mower_DYM*`, `RobotMower_DYM*` og `Robot_Mower*`.
- Service UUID: `49535343-fe7d-4ae5-8fa9-9fafd205e455`.
- Kontrolkarakteristik: `49535343-1e4d-4bd9-ba61-23c647249616`.
- HCI-bekræftede DYM-payloads til status, start/genoptag, pause/stop, dock,
  PIN-skift, multi-area, plæneklipperindstillinger og arbejdstidsplan.

Behandles endnu ikke som understøttet:

- Grouw 18739/18740 CLEVR / `robotic-mower connect` /
  `Mower_XXXXXX`-enheder.
- Cloud- eller Wi-Fi-styring.
- Firmwareopdatering.

Detaljerede protokolnoter findes i companion-biblioteket:
[Bjorkan/pyGrouw reverse_engineered/index.md](https://github.com/Bjorkan/pyGrouw/blob/main/reverse_engineered/index.md).

## Funktioner

- Bluetooth-opdagelse og manuel opsætning via BLE-adresse.
- Kræver plæneklipperens 4-cifrede PIN-kode under opsætning.
- BLE-kommunikation via `pygrouw`, inklusive best-effort MTU-anmodning efter
  tilslutning, svarende til Daye-appens FlutterBluePlus-forbindelsesflow.
- Coordinator-baseret polling og entity-tilgængelighed.
- Plæneklipperkontroller til start/genoptag, pause/stop og dock.
- Entiteter for afkodede DYM-statusfelter:
  - plæneklipperaktivitet
  - batteri
  - rå tilstandskode
  - seneste svarkommando
  - docked status
- Entiteter for plæneklipperindstillinger (efter aflæsning med get-tjenesterne):
  - multi-area-procenter og afstande (Area 2, Area 3)
  - regnforsinkelse timer og minutter
  - ukendt indstillingsbyte
  - klip i regn, kantklipning, helix, LED
- Debugtjenesten `grouw_ble_mower.send_raw_json` til protokolvalidering.
- Tjenesten `grouw_ble_mower.change_pin` til at skifte plæneklipperens PIN-kode.
- Tjenesten `grouw_ble_mower.set_multi_area` til at konfigurere multi-area-klipning.
- Tjenesten `grouw_ble_mower.set_mower_settings` til at konfigurere regn, kantklipning, helix og regnforsinkelse.
- Tjenesten `grouw_ble_mower.set_work_times` til at konfigurere den ugentlige arbejdstidsplan.
- Tjenesterne `grouw_ble_mower.get_multi_area`, `get_mower_settings` og `get_work_times`
  til at læse indstillinger fra plæneklipperen og opdatere de tilsvarende sensorer.

Normal polling og styring bruger den HCI-bekræftede DYM-protokol. APK-afledte
BlueKey-kommandoer er kun tilgængelige som rå debug-prober, indtil
hardware-captures beviser deres præcise on-wire-adfærd for denne
plæneklippergeneration.

Indstillingslæsning og -skrivning kræver autentificering og udføres på
anmodning via tjenester. De er ikke en del af den normale polling-cyklus.

## Installation

### HACS

HACS skal allerede være installeret i Home Assistant.

Åbn dette repository i HACS:

[![Åbn din Home Assistant-instans og åbn dette repository i Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Bjorkan&repository=ha-grouw-ble&category=integration)

Installer integrationen i HACS, genstart Home Assistant, og tilføj derefter
integrationen:

[![Åbn din Home Assistant-instans og start opsætningen af denne integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=grouw_ble_mower)

```text
Indstillinger -> Enheder og tjenester -> Tilføj integration -> Grouw Mower
```

### Manuel

Kopiér custom component til Home Assistant:

```text
config/custom_components/grouw_ble_mower/
```

Genstart Home Assistant, og tilføj derefter integrationen fra siden Enheder og
tjenester.

Hold plæneklipperen vågen og tæt på en Bluetooth-adapter eller en
tilslutningsbar BLE-proxy under den første opsætning.

## Debuglogning

Tilføj dette under test:

```yaml
logger:
  default: info
  logs:
    custom_components.grouw_ble_mower: debug
    pygrouw: debug
    bleak_retry_connector: debug
```

Del ikke logs, før BLE-adresser, serienumre, PIN-koder og andre private
værdier er maskeret.

## Tjenester

### Rå BLE-validering

Brug kun den rå tjeneste, mens protokollen valideres:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    command: status
```

Indfangede payloads kan sendes direkte:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    raw_hex: "44594d00111111111111111100000000000000160601ff0a"
    expect_cmd: "0x80"
```

Sæt kun `authenticate: false`, når du bevidst tester forbindelsespreludiet
eller stille kommandoadfærd.

APK-formede BlueKey-prober er tilgængelige til research:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    bluekey: mower_settings
```

### Skift PIN-kode

```yaml
action: grouw_ble_mower.change_pin
data:
  new_pin: "4321"
  # old_pin er valgfrit; standard er den konfigurerede PIN-kode
```

### Multi-area-indstillinger

Læs multi-area-indstillinger:

```yaml
action: grouw_ble_mower.get_multi_area
```

Indstil multi-area-indstillinger:

```yaml
action: grouw_ble_mower.set_multi_area
data:
  area2_percentage: 5
  area2_distance: 12
  area3_percentage: 16
  area3_distance: 74
```

### Plæneklipperindstillinger

Læs plæneklipperindstillinger:

```yaml
action: grouw_ble_mower.get_mower_settings
```

Indstil plæneklipperindstillinger:

```yaml
action: grouw_ble_mower.set_mower_settings
data:
  mow_in_rain: true
  boundary_cut: false
  helix: true
  rain_delay_hours: 4
  rain_delay_minutes: 13
```

### Arbejdstidsplan

Læs arbejdstidsplan:

```yaml
action: grouw_ble_mower.get_work_times
```

Indstil arbejdstidsplan (7 dage, mandag til søndag):

```yaml
action: grouw_ble_mower.set_work_times
data:
  starts:
    - [18, 0]
    - [11, 13]
    - [11, 21]
    - [4, 7]
    - [18, 0]
    - [10, 1]
    - [17, 50]
  durations:
    - [1, 0]
    - [11, 9]
    - [10, 0]
    - [3, 0]
    - [4, 0]
    - [2, 0]
    - [6, 0]
```

### Målret en plæneklipper

Alle tjenester accepterer valgfrie felter `address` eller `entry_id` for at
målrette en specifik plæneklipper, når flere er konfigureret. Når kun én
plæneklipper er konfigureret, er felterne valgfrie.

Gem holdbare fund i companion-bibliotekets `reverse_engineered/`-mappe som
opsummeringer. Commit ikke APK'er, dekompileret output, rå captures eller logs
med private data.

## Valideringsprioriteter

1. Bekræft opdagelse via service UUID eller DYM local name.
2. Bekræft at statuspolling forbliver stille med uautentificerede
   DYM-statusanmodninger.
3. Bekræft at start/genoptag, pause/stop og dock udføres uden
   DYM-session/auth-preludiet og opdaterer status via den efterfølgende
   statuspolling.
4. Fang batteri-, docked- og tilstandsfelter på tværs af flere
   plæneklippertilstande, især forskellen mellem DYM-tilstand `0x00` og
   `0x01`.
5. Fang payloads for opladning, fejl, løft og tilt.
6. Behandl regn som en indstillingsfunktion, medmindre der fanges en
   BLE-statusbyte for det.
