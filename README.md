# Hausmonitor V3

Smartphone-optimierte FastAPI-PWA für langfristiges Nivellement-Monitoring mit SQLite, Fotos, Terrasse, Umweltkorrelationen, PDF-Bericht, CSV-Austausch und Plausibilitätsbewertung.

## Funktionen

- fünf Einzelablesungen für SW, SO, Anbau, Terrasse SW und Terrasse SO
- Mittelwert, Standardabweichung, Standardfehler, Spannweite
- Hausdifferenz `SO - SW` und Terrassendifferenz `TSO - TSW`
- Änderungen gegenüber der jeweils ersten vollständigen Kampagne
- kombinierter Standardfehler und Signal/Rausch-Bewertung
- Fotoaufnahme direkt über das Smartphone
- Umweltwerte: Luft- und Wandtemperaturen, Grundwasser, Niederschlag, Wetter und Lichtquelle
- Diagramme für Haus, Terrasse, Messrauschen, Grundwasser und Temperatur
- lineare Trend- und Korrelationsauswertung mit R²
- automatischer PDF-Bericht
- CSV-Export und CSV-Import von Kampagnenmetadaten
- PWA-App-Shell, Passwortschutz und Docker-Betrieb

## Installation auf Proxmox

### 1. Debian-LXC oder Debian-VM vorbereiten

Installiere Docker Engine und das Docker-Compose-Plugin nach den Vorgaben deiner Debian-Version. Kopiere anschließend den Ordner `hausmonitor-v3` auf den Container oder die VM.

### 2. Konfiguration anlegen

```bash
cd hausmonitor-v3
cp .env.example .env
openssl rand -hex 32
```

Trage die erzeugte Zeichenfolge als `SECRET_KEY` ein und ändere das Passwort:

```env
APP_PASSWORD=ein-langes-eigenes-passwort
SECRET_KEY=die-erzeugte-zufallszeichenfolge
COOKIE_SECURE=false
```

### 3. Starten

```bash
docker compose up -d --build
```

Im Heimnetz erreichst du die App unter `http://IP-DES-CONTAINERS:8000`.

### 4. Smartphone-PWA

Für die normale PWA-Installation benötigt der Browser HTTPS. Im reinen Heimnetz kann die Website ohne Installation über HTTP verwendet werden. Für PWA und externen Zugriff verwende einen Reverse Proxy mit TLS oder ein VPN.

Beispiel für Caddy:

```caddy
hausmonitor.example.de {
    reverse_proxy 192.168.1.50:8000
}
```

Bei HTTPS in `.env` setzen:

```env
COOKIE_SECURE=true
```

### 5. Update

```bash
docker compose down
docker compose up -d --build
```

Der persistente Ordner `data/` bleibt erhalten.

## Backup und Wiederherstellung

Datenbank und Fotos befinden sich unter `data/`. Backup:

```bash
./scripts/backup.sh
```

Alternativ den gesamten LXC über Proxmox sichern. Wiederherstellung: Container stoppen, gesicherten `data/`-Ordner zurückkopieren und Container starten.

## Lokale Entwicklung

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_PATH=./data/hausmonitor.db
export UPLOAD_DIR=./data/uploads
export APP_PASSWORD=
uvicorn app.main:app --reload
pytest -q
```

## Messlogik

Die Skalenwerte dürfen an SW und SO unterschiedliche absolute Nullpunkte haben. Die App bewertet die Differenz `SO - SW`. Die erste vollständige Hauskampagne definiert den Haus-Startwert; die erste vollständige Terrassenkampagne definiert separat den Terrassen-Startwert.

Die Bewertung `Signal klar` verwendet das Verhältnis der Änderung zum kombinierten Standardfehler innerhalb der Kampagne. Sie ersetzt nicht die langfristige Wiederholunsicherheit durch Geräteposition, Halterung, Beleuchtung, Temperatur und Bedienung.

## Interpretation der V3-Analysen

- Der Zeittrend wird in Millimeter pro Kampagne angegeben, nicht automatisch pro Jahr.
- Korrelationen benötigen mindestens drei passende Kampagnen.
- R² beschreibt nur die lineare Anpassung der vorhandenen Daten.
- Eine Korrelation mit Temperatur oder Grundwasser ist kein Nachweis einer Ursache.
- Prognosen und PDF-Angaben dienen dem Monitoring, nicht als statischer oder geotechnischer Nachweis.

## Sicherheit

- `.env` niemals veröffentlichen.
- Port 8000 nicht direkt ins Internet freigeben.
- Für externen Zugriff HTTPS oder VPN verwenden.
- Regelmäßige Backups von `data/` und der Proxmox-VM beziehungsweise des LXC erstellen.
