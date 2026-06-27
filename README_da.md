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
- HCI-bekræftede DYM-payloads til status, start/genoptag, pause/stop og dock.

Behandles endnu ikke som understøttet:

- Grouw 18739/18740 CLEVR / `robotic-mower connect` /
  `Mower_XXXXXX`-enheder.
- Cloud- eller Wi-Fi-styring.
- Indstillingsskrivninger for regn, kantklipning, ultralyd, helix, LED,
  multizone, tidsplaner, PIN-skift eller firmwareopdatering.

Detaljerede protokolnoter findes i companion-biblioteket:
[../pyGrouw/reverse_engineered/index.md](../pyGrouw/reverse_engineered/index.md).

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
- Debugtjenesten `grouw_ble_mower.send_raw_json` til protokolvalidering.

Normal polling og styring bruger den HCI-bekræftede DYM-protokol. APK-afledte
BlueKey-kommandoer er kun tilgængelige som rå debug-prober, indtil
hardware-captures beviser deres præcise on-wire-adfærd for denne
plæneklippergeneration.

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

## Rå BLE-validering

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

Understøttede navngivne BlueKey-prober er `query_info`, `set_time`,
`query_pin`, `work_time`, `mower_settings`, `multi_area` og `error_memory`.
Generiske prober kan bruge `bluekey_sub_cmd` plus valgfri `bluekey_data`.

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
