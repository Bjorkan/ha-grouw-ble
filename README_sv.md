<p align="left">
  <img src="custom_components/grouw_ble_mower/brand/logo.png" alt="Grouw logo" width="200"/>
</p>

# Grouw Mower för Home Assistant

[English](README.md) | [Dansk](README_da.md)

Anpassad Home Assistant-integration för lokal Bluetooth-styrning av Grouw
robotgräsklippare som använder Daye Power-appen
(`com.dayepower.dayeappleaf`).

Integrationen använder Home Assistants Bluetooth-hanterare för att slå upp
enheter via adress. Den kör ingen egen scanner, så samma kodväg kan fungera
med en lokal Bluetooth-adapter eller en anslutningsbar Home Assistant
Bluetooth-proxy. BLE-kommunikation och Daye/Grouw-protokollhantering sköts av
Python-biblioteket `pygrouw`:
[GitHub](https://github.com/Bjorkan/pyGrouw) |
[PyPI](https://pypi.org/project/pygrouw/).

## Nuvarande status

Projektet riktar sig just nu mot DYM-generationen av klippare som syns i Daye
Power-APK:n och i redigerade hårdvarucaptures.

Bekräftade målsignaler:

- APK-version `2.0.1`, versionskod `117`.
- BLE-namn: `Robot Mower_DYM*`, `RobotMower_DYM*` och `Robot_Mower*`.
- Service UUID: `49535343-fe7d-4ae5-8fa9-9fafd205e455`.
- Kontrollkaraktäristik: `49535343-1e4d-4bd9-ba61-23c647249616`.
- HCI-bekräftade DYM-payloads för status, start/återuppta, paus/stopp och
  dockning.

Behandlas ännu inte som stödda:

- Grouw 18739/18740 CLEVR / `robotic-mower connect` /
  `Mower_XXXXXX`-enheter.
- Moln- eller Wi-Fi-styrning.
- Inställningsskrivningar för regn, kantklippning, ultraljud, helix, LED,
  multizon, scheman, PIN-byte eller firmwareuppdatering.

Detaljerade protokollanteckningar finns i companion-biblioteket:
[../pyGrouw/reverse_engineered/index.md](../pyGrouw/reverse_engineered/index.md).

## Funktioner

- Bluetooth-upptäckt och manuell konfiguration via BLE-adress.
- Kräver 4-siffrig PIN-kod för klipparen vid konfiguration.
- BLE-kommunikation via `pygrouw`, inklusive best-effort MTU-begäran efter
  anslutning, i linje med Daye-appens FlutterBluePlus-flöde.
- Coordinator-baserad polling och entity-tillgänglighet.
- Gräsklipparkontroller för start/återuppta, paus/stopp och dockning.
- Entiteter för avkodade DYM-statusfält:
  - gräsklipparaktivitet
  - batteri
  - rå lägeskod
  - senaste svarskommando
  - dockad status
- Debugtjänsten `grouw_ble_mower.send_raw_json` för protokollvalidering.

Normal polling och styrning använder det HCI-bekräftade DYM-protokollet.
APK-härledda BlueKey-kommandon finns endast som råa debugprober tills
hårdvarucaptures visar deras exakta beteende på kabeln för denna
klippargeneration.

## Installation

### HACS

HACS måste redan vara installerat i Home Assistant.

Öppna detta repository i HACS:

[![Öppna din Home Assistant-instans och öppna detta repository i Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Bjorkan&repository=ha-grouw-ble&category=integration)

Installera integrationen i HACS, starta om Home Assistant och lägg sedan till
integrationen:

[![Öppna din Home Assistant-instans och starta konfigurationen av denna integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=grouw_ble_mower)

```text
Inställningar -> Enheter och tjänster -> Lägg till integration -> Grouw Mower
```

### Manuellt

Kopiera custom component till Home Assistant:

```text
config/custom_components/grouw_ble_mower/
```

Starta om Home Assistant och lägg sedan till integrationen från sidan Enheter
och tjänster.

Håll klipparen vaken och nära en Bluetooth-adapter eller anslutningsbar
BLE-proxy under första konfigurationen.

## Debugloggning

Lägg till detta under testning:

```yaml
logger:
  default: info
  logs:
    custom_components.grouw_ble_mower: debug
    pygrouw: debug
    bleak_retry_connector: debug
```

Dela inte loggar förrän BLE-adresser, serienummer, PIN-koder och andra privata
värden har maskerats.

## Rå BLE-validering

Använd den råa tjänsten endast vid protokollvalidering:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    command: status
```

Infångade payloads kan skickas direkt:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    raw_hex: "44594d00111111111111111100000000000000160601ff0a"
    expect_cmd: "0x80"
```

Sätt `authenticate: false` endast när du medvetet testar anslutningspreludiet
eller tysta kommandon.

APK-formade BlueKey-prober finns för research:

```yaml
action: grouw_ble_mower.send_raw_json
data:
  payload:
    bluekey: mower_settings
```

Stödda namngivna BlueKey-prober är `query_info`, `set_time`, `query_pin`,
`work_time`, `mower_settings`, `multi_area` och `error_memory`. Generiska
prober kan använda `bluekey_sub_cmd` plus valfri `bluekey_data`.

Spara hållbara fynd i companion-bibliotekets `reverse_engineered/`-mapp som
sammanfattningar. Committa inte APK:er, dekompilerad output, råa captures eller
loggar med privat information.

## Valideringsprioriteringar

1. Bekräfta upptäckt via service UUID eller DYM-local name.
2. Bekräfta att statuspolling förblir tyst med oautentiserade
   DYM-statusförfrågningar.
3. Bekräfta att start/återuppta, paus/stopp och dockning körs utan
   DYM-session/auth-preludiet och uppdaterar status via uppföljande
   statuspolling.
4. Fånga batteri-, dockad- och lägesfält över fler klipparlägen, särskilt
   skillnaden mellan DYM-läge `0x00` och `0x01`.
5. Fånga payloads för laddning, fel, lyft och tilt.
6. Behandla regn som en inställningsfunktion tills en BLE-statusbyte har
   fångats för det.
