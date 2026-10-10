# Tempur Smartbase für Home Assistant

[![Validate](https://github.com/Basti486PB/ha-tempur-smartbase/actions/workflows/validate.yml/badge.svg)](https://github.com/Basti486PB/ha-tempur-smartbase/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)

*[English version below](#english)*

Inoffizielle Home-Assistant-Integration für verstellbare Tempur-Untergestelle (z. B. **TEMPUR-Ergo Smart Base**), die mit **Sleeptracker AI** verbunden sind. Die Integration nutzt dieselbe Cloud wie die Sleeptracker-App. Du meldest dich mit deinem App-Konto an, zusätzliche Hardware, Bluetooth oder MQTT brauchst du nicht.

> **Haftungsausschluss:** Dies ist ein privates Community-Projekt. Es steht in keiner Verbindung zu Tempur Sealy International oder Fullpower Technologies (Sleeptracker) und wird von diesen weder unterstützt noch geprüft. „Tempur“, „TEMPUR-Ergo“ und „Sleeptracker“ sind Marken ihrer jeweiligen Inhaber und werden hier nur verwendet, um die kompatiblen Geräte zu benennen. Die Cloud-Schnittstelle ist nicht öffentlich dokumentiert und kann sich jederzeit ändern. Nutzung auf eigene Verantwortung.

## Voraussetzungen

- Home Assistant 2024.11 oder neuer
- Ein Tempur-Untergestell mit Sleeptracker-AI-Modul, eingerichtet in der Sleeptracker-AI-App und mit dem WLAN verbunden
- E-Mail und Passwort deines Sleeptracker-AI-Kontos

**Getestet** mit einer Tempur-Smartbase mit Sleeptracker AI in Deutschland. Die Auswahl *Beautyrest* und *Serta* ist für Betten dieser Marken mit Sleeptracker vorgesehen, aber bisher ungetestet. Rückmeldungen dazu sind willkommen.

## Funktionen

Pro Bett wird ein Gerät angelegt. Es erscheinen nur die Entitäten, die dein Untergestell laut Cloud unterstützt.

| Typ | Entitäten |
| --- | --- |
| Button | Positionen *flach*, *Zero G*, *TV*, *Favorit*, *Anti-Schnarch*; Massage-Stufen (Kopf, Fuß, beide), Massagemuster, Massagetimer |
| Button (Konfiguration, standardmäßig deaktiviert) | Aktuelle Position als *Zero G*, *TV*, *Favorit* oder *Anti-Schnarch* speichern |
| Cover | Motoren Kopfteil, Fußteil, Kopfneigung, Lordosenstütze (Öffnen = hoch, Schließen = runter, Stopp) |
| Sensor | Winkel Kopf- und Fußteil, Massagestärke, Massagemuster, Massage-Restzeit, WLAN-Signal (Diagnose, standardmäßig deaktiviert) |
| Sensor (falls vorhanden) | Raumtemperatur, Luftfeuchtigkeit, CO2, VOC des Sleeptracker-Moduls |
| Switch | Unterbettbeleuchtung, Schnarchhilfe Neigung, Schnarchhilfe Vibration |

Der Zustand wird einmal pro Minute aus der Cloud abgefragt und nach jedem Befehl sofort aktualisiert.

### Zwei Betten oder zwei Seiten

Die Cloud schickt Befehle immer an die Seite bzw. das Bett, das zum angemeldeten Konto gehört. Habt ihr zwei Untergestelle oder ein geteiltes Bett mit zwei Konten, richtet die Integration einfach für jedes Konto einmal ein (*Einstellungen → Geräte & Dienste → Tempur Smartbase → Eintrag hinzufügen*).

## Installation

### Über HACS (empfohlen)

1. In Home Assistant **HACS** öffnen.
2. Oben rechts auf die drei Punkte, dann **Benutzerdefinierte Repositories**.
3. `https://github.com/Basti486PB/ha-tempur-smartbase` eintragen, Typ **Integration**, hinzufügen.
4. Nach **Tempur Smartbase** suchen, **Herunterladen** und Home Assistant neu starten.

### Manuell

1. Den Ordner `custom_components/tempur_smartbase` aus diesem Repository nach `config/custom_components/` deiner Home-Assistant-Installation kopieren.
2. Home Assistant neu starten.

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen** und nach **Tempur Smartbase** suchen.
2. E-Mail und Passwort deines Sleeptracker-AI-Kontos eingeben. Bei *App / Marke* **Tempur (Sleeptracker AI)** auswählen.
3. Das Bett erscheint als Gerät mit allen unterstützten Entitäten.

Ändert sich dein Passwort, fragt Home Assistant automatisch nach dem neuen.

## Datenschutz

Zugangsdaten werden nur in deiner Home-Assistant-Installation gespeichert (wie bei jeder anderen Cloud-Integration) und ausschließlich an die Sleeptracker-Server geschickt (`auth.tsi.sleeptracker.com`, `app.tsi.sleeptracker.com`). Es gibt keine weiteren Server und keine Telemetrie.

## Beispiel-Automation

```yaml
automation:
  - alias: "Bett um 23 Uhr flach stellen"
    triggers:
      - trigger: time
        at: "23:00:00"
    actions:
      - action: button.press
        target:
          entity_id: button.mein_bett_position_flach
```

Die Entitäts-ID hängt vom Namen deines Betts in der App und von der Sprache deiner Home-Assistant-Installation ab. Du findest sie unter **Einstellungen → Geräte & Dienste → Tempur Smartbase**.

## Fehlersuche

Ausführliche Protokolle aktivierst du in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.tempur_smartbase: debug
```

Probleme und Wünsche bitte als [Issue](https://github.com/Basti486PB/ha-tempur-smartbase/issues) melden, mit Modell des Untergestells, Home-Assistant-Version und dem Protokollauszug. Bitte vorher E-Mail-Adressen und Seriennummern aus dem Protokoll entfernen.

## Entwicklung

```bash
pip install -r requirements_test.txt
pytest
```

## Danksagung und Lizenz

Die Endpunkte und Befehlscodes der Sleeptracker-Cloud stammen aus dem Projekt [richardhopton/smartbed-mqtt](https://github.com/richardhopton/smartbed-mqtt) (MIT-Lizenz). Diese Integration ist eine eigenständige Python-Implementierung und steht ebenfalls unter der [MIT-Lizenz](LICENSE).

---

<a id="english"></a>

## English

Unofficial Home Assistant integration for Tempur adjustable bases (e.g. **TEMPUR-Ergo Smart Base**) paired with **Sleeptracker AI**. It uses the same cloud as the Sleeptracker app: sign in with your app account, no extra hardware, Bluetooth or MQTT needed.

> **Disclaimer:** Community project, not affiliated with, endorsed or reviewed by Tempur Sealy International or Fullpower Technologies (Sleeptracker). Trademarks belong to their owners and are only used to identify compatible devices. The cloud API is undocumented and may change at any time. Use at your own risk.

**Requirements:** Home Assistant 2024.11+, a Tempur base with a Sleeptracker AI module set up in the app, and your Sleeptracker AI login. Tested with a Tempur smart base in Germany; the *Beautyrest* and *Serta* options are untested.

**Installation:** HACS → three dots → *Custom repositories* → add `https://github.com/Basti486PB/ha-tempur-smartbase` as *Integration* → download → restart. Or copy `custom_components/tempur_smartbase` to `config/custom_components/` manually.

**Setup:** *Settings → Devices & services → Add integration → Tempur Smartbase*, enter your Sleeptracker AI email and password, keep *Tempur (Sleeptracker AI)* selected.

**Entities:** preset, program and massage buttons; covers for the head, foot, tilt and lumbar motors; sensors for head/foot angle, massage state, room climate (if the module has sensors) and WiFi signal; switches for the safety light and snore relief. Only features your base reports are created. State is polled every 60 seconds.

**Two beds or sides:** commands always go to the side that belongs to the signed-in account. Add the integration once per account.

**Privacy:** credentials are stored only in your Home Assistant and sent only to the Sleeptracker servers. No telemetry.

**Credits & license:** API details from [richardhopton/smartbed-mqtt](https://github.com/richardhopton/smartbed-mqtt) (MIT). This integration is an independent implementation under the [MIT license](LICENSE).
