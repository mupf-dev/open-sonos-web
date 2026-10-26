# Sonos Web

Schlanke Weboberfläche für Sonos – helles Design in Weiß, dunkles Design in Schwarz (folgt automatisch dem System, umschaltbar über das Symbol oben links).
Steuert die Lautsprecher direkt im lokalen Netz über die UPnP-Schnittstelle (Bibliothek [SoCo](https://github.com/SoCo/SoCo)), ohne Sonos-Cloud und ohne Konto.

## Funktionen

| Bereich | Was geht |
|---|---|
| **Jetzt läuft** | Cover, Titel, Fortschritt mit Spulen, Play/Pause, Vor/Zurück, Zufall, Wiederholen (alle/einer), Crossfade, Sleep-Timer, Umschalten auf TV bzw. Line-In, Gruppen- und Einzellautstärke, Stummschalten |
| **Warteschlange** | Anzeigen, Titel anspielen, entfernen, per Drag & Drop umsortieren, leeren, als Sonos-Playlist speichern |
| **Bühne** | Alternative „Jetzt läuft“-Ansicht: großes Cover, Hintergrund in den Cover-Farben, Bedienelemente blenden sich aus, Vollbild; dazu zeitgenau mitlaufender Songtext (LRCLIB), Interpreten-Infos (Wikipedia), „Als Nächstes“ und Musikvideo-Suche bei YouTube |
| **Musikdienste** | Spotify & Co. durchsuchen (Startseite mit sortierbaren Zeilen, Suche, eigene Bibliothek) – einmalige Verknüpfung unter *Räume › Musikdienste* |
| **Favoriten** | Sonos-Favoriten (Radio, Spotify-Playlists usw.) abspielen, einreihen |
| **Playlists** | Sonos-Playlists öffnen, abspielen, einreihen, umbenennen, löschen, Titel hinzufügen |
| **Bibliothek** | Musikbibliothek (NAS/Freigaben) nach Interpreten, Alben, Titeln, Genres, Komponisten, importierten Playlists und Ordnern durchsuchen; Suche; Neuindizierung |
| **Wecker** | Anlegen, bearbeiten, löschen, aktivieren – Uhrzeit, Raum, Wiederholung (inkl. einzelner Tage), Musik aus Favoriten, Lautstärke, Dauer, Wiedergabemodus |
| **Räume** | Gruppen bilden/auflösen, alle verbinden/trennen; je Lautsprecher: Bässe, Höhen, Balance, Loudness, Nachtmodus, Sprachverbesserung, Subwoofer, Surround, Trueplay (je nach Modell), Name, Statusleuchte, Tastensperre, Geräteinfos |

Tastatur: Leertaste = Play/Pause, ↑/↓ = Lautstärke, Shift + ←/→ = Titel zurück/vor.

Nicht enthalten: Musikvideos direkt in der Oberfläche (dafür bräuchte es einen YouTube-API-Schlüssel, und das Video würde parallel zu Sonos Ton abspielen) – die Bühne öffnet stattdessen die YouTube-Suche. Ordner von Diensten, die hier nicht verbunden sind, lassen sich nur in der Sonos-App öffnen.

## Starten

```bash
./run.sh            # http://localhost:8080
./run.sh --demo     # Demo-Modus mit simulierten Räumen, ohne echte Lautsprecher
./run.sh --port 9000
```

Beim ersten Start wird automatisch eine virtuelle Umgebung (`.venv`) angelegt.

### Docker (z. B. auf Raspberry Pi oder NAS)

```bash
docker compose up -d --build   # http://<host>:8080
```

`network_mode: host` ist nötig, damit die automatische Erkennung funktioniert.

## Lautsprecher finden

Die Erkennung nutzt SSDP-Multicast und klappt nur, wenn der Server **im selben Netz** wie die Lautsprecher läuft.
Falls nichts gefunden wird, zeigt die Oberfläche einen Verbindungsdialog: Dort die IP **eines** Lautsprechers eintragen
(Sonos-App › Einstellungen › System › Über mein System) – alle anderen Räume werden darüber gefunden.
Alternativ per Umgebungsvariable `SONOS_HOSTS=192.168.178.40` oder über die Netzwerksuche im Dialog.

**WSL2-Hinweis:** Im Standard-NAT-Modus sieht WSL keine Multicast-Pakete aus dem Heimnetz. Entweder die IP eintragen
(Unicast funktioniert) oder in `%UserProfile%\.wslconfig` den gespiegelten Modus aktivieren und WSL neu starten:

```ini
[wsl2]
networkingMode=mirrored
```

Um die Oberfläche von Handy/Tablet zu nutzen, den Server auf einem Gerät im Heimnetz betreiben (Docker-Variante) oder unter WSL den gespiegelten Modus verwenden.

## Aufbau

```
app/main.py            REST-API (FastAPI), Doku unter /api/docs
app/sonos_service.py   Steuerung über SoCo
app/demo_service.py    Simuliertes System für den Demo-Modus
static/                Oberfläche (HTML/CSS/JS, kein Build-Schritt)
data/config.json       gespeicherte Lautsprecher-IPs (wird automatisch angelegt)
```

Externe Dienste: Für Songtexte und Interpreten-Infos (nur in der Bühnen-Ansicht) werden Interpret, Titel, Album und Dauer an lrclib.net bzw. wikipedia.org gesendet; fehlende Playlist-Cover werden über den verbundenen Musikdienst gesucht.

Sicherheit: Es gibt keine Anmeldung – wer die Seite im Netz erreicht, kann die Lautsprecher steuern (wie mit der Sonos-App auch). Nicht ins Internet freigeben.
