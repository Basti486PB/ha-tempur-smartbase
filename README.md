# Tempur Smartbase für Home Assistant

Eigene Home-Assistant-Integration für Tempur-Smartbase-Betten (z. B. TEMPUR-Ergo Smart Base), die mit **Tempur Sleeptracker AI** verbunden sind. Die Integration spricht dieselbe Cloud an wie die Sleeptracker-App. Du meldest dich also einfach mit deinem App-Konto an, ein zusätzliches Gerät oder Bluetooth ist nicht nötig.

> Inoffizielles Projekt, nicht von Tempur oder Sleeptracker unterstützt. Die Cloud-Schnittstelle ist nicht öffentlich dokumentiert und kann sich jederzeit ändern.

## Was du bekommst

Pro Bett wird ein Gerät angelegt. Welche Entitäten erscheinen, hängt davon ab, was dein Untergestell laut Cloud unterstützt.

| Typ | Entitäten |
| --- | --- |
| Button | Positionen *flach*, *Zero G*, *TV*, *Favorit*, *Anti-Schnarch*; Massage-Stufen (Kopf, Fuß, beide), Massagemuster, Massagetimer |
| Button (Konfiguration, standardmäßig deaktiviert) | Aktuelle Position als *Zero G*, *TV*, *Favorit* oder *Anti-Schnarch* speichern |
| Cover | Motoren Kopfteil, Fußteil, Kopfneigung, Lordosenstütze (Öffnen = hoch, Schließen = runter, Stopp) |
| Sensor | Winkel Kopf- und Fußteil, Massagestärke, Massagemuster, Massage-Restzeit, WLAN-Signal (Diagnose) |
| Sensor (falls vorhanden) | Raumtemperatur, Luftfeuchtigkeit, CO2, VOC des Sleeptracker-Moduls |
| Switch | Unterbettbeleuchtung, Schnarchhilfe Neigung, Schnarchhilfe Vibration |

Der Zustand wird jede Minute aus der Cloud abgefragt und direkt nach jedem Befehl aktualisiert.

**Hinweis zu geteilten Betten:** Die Cloud schickt Befehle immer an die Seite des Untergestells, die zum angemeldeten Konto gehört. Wenn ihr zu zweit schlaft und beide Seiten steuern wollt, richte die Integration einfach ein zweites Mal mit dem Konto deines Partners ein.

## Installation

### Über HACS (empfohlen)

1. In Home Assistant **HACS** öffnen.
2. Oben rechts auf die drei Punkte, dann **Benutzerdefinierte Repositories**.
3. Repository `https://github.com/Basti486PB/ha-tempur-smartbase` eintragen, Typ **Integration**, hinzufügen.
4. Nach **Tempur Smartbase** suchen, herunterladen und Home Assistant neu starten.

### Manuell

1. Den Ordner `custom_components/tempur_smartbase` aus diesem Repository in den Ordner `config/custom_components/` deiner Home-Assistant-Installation kopieren.
2. Home Assistant neu starten.

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen** und nach **Tempur Smartbase** suchen.
2. E-Mail-Adresse und Passwort deines Sleeptracker-AI-Kontos eingeben. Bei *App / Marke* bleibt **Tempur (Sleeptracker AI)** ausgewählt.
3. Fertig: das Bett erscheint als Gerät mit allen unterstützten Entitäten.

Ändert sich dein Passwort, fragt Home Assistant automatisch nach dem neuen.

Die Zugangsdaten werden nur lokal in Home Assistant gespeichert und ausschließlich an die Sleeptracker-Cloud geschickt.

## Beispiel-Automation

```yaml
automation:
  - alias: "Bett flach um 23 Uhr"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: button.press
        target:
          entity_id: button.schlafzimmer_position_flach
```

Die genaue Entitäts-ID siehst du unter **Einstellungen → Geräte & Dienste → Tempur Smartbase**.

## Fehlersuche

Ausführliche Protokolle aktivierst du in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.tempur_smartbase: debug
```

## Entwicklung

```bash
pip install -r requirements_test.txt
pytest
```

## Danksagung

Die Endpunkte der Sleeptracker-Cloud stammen aus dem Projekt [richardhopton/smartbed-mqtt](https://github.com/richardhopton/smartbed-mqtt) (MIT-Lizenz), das die Schnittstelle der App analysiert hat.
