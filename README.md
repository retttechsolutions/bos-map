# BOS-Map

**Interaktive Karte aller integrierten Leitstellen (ILS) in Deutschland** – mit Zuständigkeitsgebieten, Funkgruppen-Verzeichnis und einer statischen API.

> Klick auf die Karte oder Adresssuche → zuständige ILS + Digitalfunk-Rufgruppen

---

## Inhalt

- [Worum geht es?](#worum-geht-es)
- [Features](#features)
- [Architektur](#architektur)
- [Datenpipeline](#datenpipeline)
- [API](#api)
- [Datenquellen & Lizenzen](#datenquellen--lizenzen)
- [Lokale Entwicklung](#lokale-entwicklung)
- [Mitmachen](#mitmachen)
- [Datenschema](#datenschema)
- [Roadmap](#roadmap)

---

## Worum geht es?

In Deutschland gibt es rund 250 **integrierte Leitstellen (ILS)**, die Notrufe für Feuerwehr, Rettungsdienst und teils Katastrophenschutz koordinieren. Jede Leitstelle ist für ein bestimmtes geografisches Gebiet zuständig und nutzt im Digitalfunk BOS (TETRA) festgelegte Rufgruppen.

Ein einziges offenes, amtliches Bundesregister mit Leitstellengrenzen + Stammdaten + Rufgruppen **existiert nicht**. BOS-Map schließt diese Lücke: Es aggregiert amtliche Geodienste der Länder, leitet fehlende Gebiete aus Verwaltungsgrenzen ab und stellt alles als offenen Datensatz sowie interaktive Karte bereit.

---

## Features

| Feature | Status |
|---|---|
| Interaktive Deutschlandkarte mit ILS-Zuständigkeitsgebieten | ✅ MVP |
| Klick auf Karte → zuständige ILS anzeigen | ✅ MVP |
| Adresssuche (Nominatim / OpenStreetMap) | ✅ MVP |
| Funkgruppen-Verzeichnis pro Leitstelle | 🔄 Phase 2 |
| Statische REST-API (GeoJSON, keine Serverabhängigkeit) | ✅ MVP |
| Alle 16 Bundesländer abgedeckt | 🔄 Phase 2 |
| Koordinaten-Lookup per URL (`?lat=48.1&lon=11.5`) | 🔄 Phase 2 |
| GitHub Pages Hosting (kostenlos, kein Server) | ✅ MVP |

---

## Architektur

BOS-Map ist vollständig **statisch** – kein Backend-Server, keine Datenbank zur Laufzeit. Alle schweren Berechnungen laufen zur Build-Zeit in der Datenpipeline.

```
┌──────────────────────────────────────────────────────┐
│              GitHub Actions (wöchentlich)             │
│   harvest → normalize → validate → build → publish   │
└──────────────────────────┬───────────────────────────┘
                           │ erzeugt
         ┌─────────────────┼──────────────────┐
         ▼                 ▼                  ▼
   data/raw/         data/processed/     docs/  (GitHub Pages)
   (Quelldaten)      ils.geojson         ├── index.html
                     ils-points.geojson  ├── data/
                     ils-index.json      │   ├── ils.geojson
                                         │   ├── ils-points.geojson
                                         │   └── ils-index.json
                                         └── api/v1/
                                             ├── index.json
                                             └── {id}.json
```

**Koordinatenabfrage** läuft vollständig im Browser:
1. Browser lädt `ils-index.json` (R-Tree-Spatial-Index, ~30 KB) einmalig
2. `rbush` filtert Kandidaten per Bounding-Box in O(log n)
3. `@turf/boolean-point-in-polygon` prüft den exakten Treffer
4. Antwortzeit: **< 1 ms** für 250 Features

```
Tech-Stack:
  Frontend  │ MapLibre GL JS · TypeScript · Vite · rbush · Turf.js
  Pipeline  │ Python 3.12 · geopandas · shapely · pyproj · owslib · httpx
  Hosting   │ GitHub Pages (statisch, kein Server)
  Basetiles │ OpenStreetMap
  Geocoding │ Nominatim (OSM)
```

---

## Datenpipeline

Die Pipeline läuft automatisch jeden Montag per GitHub Actions und kann auch manuell getriggert werden.

```
pipeline/
├── harvest/        Quelldaten herunterladen (WFS, OGC API, HTTP, Scraping)
├── normalize/      CRS → WGS84, Feldmapping, Geometrie-Fixing, Polygon-Ableitung
├── validate/       JSON-Schema, Topologie, Coverage-Check (> 90 % Deutschlands)
└── build/          Merge, Zentroide, Spatial-Index, statische API-Dateien
```

### Pipeline lokal ausführen

```bash
cd pipeline
pip install -e ".[dev]"

# Alles auf einmal:
make all

# Oder Schritt für Schritt:
make harvest-by      # Bayern WFS
make harvest-nrw     # NRW OGC API
make harvest-sn      # Sachsen
make harvest-bkg     # BKG VG250 Verwaltungsgrenzen
make normalize
make validate
make build
```

### Tests

```bash
cd pipeline
pytest tests/ -v
```

---

## API

Die „API" sind statische JSON-Dateien, die von GitHub Pages mit `Access-Control-Allow-Origin: *` ausgeliefert werden. Kein API-Key, kein Rate-Limit.

### Endpunkte

| Endpoint | Beschreibung |
|---|---|
| `GET /api/v1/index.json` | Liste aller ILS (ohne Geometrien, ~50 KB) |
| `GET /api/v1/{leitstellen_id}.json` | Vollständiges GeoJSON-Feature einer ILS |
| `GET /data/ils.geojson` | Alle ILS als FeatureCollection (mit Polygonen) |
| `GET /data/ils-points.geojson` | Nur Zentroide (leichtgewichtig) |
| `GET /data/ils-index.json` | Serialisierter Spatial-Index für Browser-PiP |

### Beispiel

```bash
# Alle ILS als kompakte Liste
curl https://retttechsolutions.github.io/bos-map/api/v1/index.json

# ILS München vollständig
curl https://retttechsolutions.github.io/bos-map/api/v1/DE-BY-ILS-MUE.json
```

### Koordinatenabfrage (client-seitig)

Der Lookup `Koordinate → zuständige ILS` läuft im Browser. Für eigene Server-Integrationen:

```python
import json, shapely.geometry

ils = json.load(open("data/processed/ils.geojson"))
punkt = shapely.geometry.Point(11.576, 48.137)  # München

for feat in ils["features"]:
    if feat["geometry"] and shapely.geometry.shape(feat["geometry"]).contains(punkt):
        print(feat["properties"]["leitstellenname"])
        break
# → ILS München
```

---

## Datenquellen & Lizenzen

| Quelle | Bundesland | Lizenz | Typ | Geometrie |
|---|---|---|---|---|
| Verwaltungsatlas StMI Bayern | BY | CC BY-SA 4.0 | amtlich_wfs | amtliche Grenze (ATKIS) |
| IT.NRW OGC API Features | NW | dl-de/by-2-0 | amtlich_ogcapi | abgeleitet aus VG250 |
| GDI Sachsen Verwaltungsatlas | SN | dl-de/by-2-0 | amtlich_wfs | amtliche Grenze |
| BKG VG250 | DE | dl-de/zero-2-0 | Basis für Ableitungen | Landkreisgrenzen |
| Wikipedia ILS-Liste | DE | CC BY-SA | community | – (nur Stammdaten) |

Alle Datenfelder enthalten Provenienzinformationen (`quelltyp`, `geometry_basis`, `source_url`, `valid_from`, `review_status`).

**Jedes Feature im Datensatz benennt seine Quelle explizit** – Nutzer können die Herkunft jeder Geometrie und jedes Attributwerts nachvollziehen.

> **Hinweis zu Funkgruppen:** Operative Digitalfunk-Rufgruppen werden ausschließlich aus öffentlich veröffentlichten Landeskonzepten (NRW, BW, SH) übernommen. Taktisch sensible Daten werden nicht erfasst.

---

## Lokale Entwicklung

### Voraussetzungen

- Python 3.12+
- Node.js 20+
- Git LFS (`git lfs install`)

### Setup

```bash
git clone https://github.com/RettTechSolutions/bos-map.git
cd bos-map
git lfs pull   # Rohdaten herunterladen (nach erstem Pipeline-Run)
```

### Frontend starten

```bash
cd frontend
npm ci
npm run dev
# → http://localhost:5173
```

> Beim ersten Start ohne Pipeline-Daten ist die Karte leer. Entweder die Pipeline lokal ausführen oder die Daten aus dem letzten CI-Run herunterladen.

### Frontend bauen

```bash
cd frontend
npm run build
# Output → docs/
```

---

## Mitmachen

Datenkorrekturen, neue Bundesländer und Funkgruppen-Ergänzungen sind willkommen.

**Fehler melden / Daten korrigieren:** [GitHub Issues](https://github.com/RettTechSolutions/bos-map/issues)

### Daten beisteuern

1. Fork erstellen
2. Korrektur in `data/processed/normalized/{bl}.geojson` vornehmen oder neuen Harvester unter `pipeline/harvest/` ergänzen
3. `cd pipeline && make validate` ausführen – alle Checks müssen grün sein
4. Pull Request erstellen

Jeder Dateneintrag muss das JSON-Schema in `data/schema/feature.schema.json` erfüllen. Bitte `review_status` entsprechend setzen:

| Wert | Bedeutung |
|---|---|
| `verified` | Direkt aus amtlichem Geodienst (WFS/OGC API) |
| `needs_review` | Aus Verwaltungsgrenzen abgeleitet oder manuell |
| `community` | Community-Quelle (z. B. Wikipedia), noch nicht amtlich bestätigt |

---

## Datenschema

Jede ILS wird als GeoJSON-Feature gespeichert:

```json
{
  "type": "Feature",
  "properties": {
    "leitstellen_id": "DE-BY-ILS-MUE",       // DE-{BL}-ILS-{KÜRZEL}
    "leitstellenname": "ILS München",
    "bundesland": "BY",                        // ISO 3166-2:DE (ohne DE-)
    "traeger": "ZRF München",
    "betreiber": "Berufsfeuerwehr München",
    "adresse": "Heßstraße 120, 80797 München",
    "telefon": null,
    "notruf": "112",
    "quelltyp": "amtlich_wfs",                 // Quellentyp
    "funkgruppen": [
      { "name": "M_Fw", "rolle": "Feuerwehr", "quelle": "landeskonzept", "kurzwahl": null },
      { "name": "M_RD", "rolle": "Rettungsdienst", "quelle": "landeskonzept", "kurzwahl": null }
    ],
    "frequenzschema": "Digitalfunk BOS TETRA",
    "geometry_basis": "amtliche_grenze",        // Wie die Geometrie entstand
    "source_url": "https://gdiserv.bayern.de/…",
    "source_crs": "EPSG:4326",
    "valid_from": "2026-05-11",
    "valid_to": null,
    "review_status": "verified",
    "bemerkung": null
  },
  "geometry": {
    "type": "MultiPolygon",                    // Immer MultiPolygon, EPSG:4326
    "coordinates": []
  }
}
```

Vollständiges JSON-Schema: [`data/schema/feature.schema.json`](data/schema/feature.schema.json)

---

## Roadmap

- [x] **Phase 1** – MVP: Bayern, NRW, Sachsen mit amtlichen Geodaten; Karte, Adresssuche, InfoPanel
- [ ] **Phase 2** – Alle 16 Bundesländer; Funkgruppen für NRW/BW/SH; Mobile-Optimierung
- [ ] **Phase 3** – Permalink-URLs (`?ils=DE-BY-ILS-MUE`), Changelog, nightly Pipeline-Diff, Community-Korrektur-Workflow

---

## Lizenz

Der **Quellcode** steht unter der [MIT-Lizenz](LICENSE).

Die **Geodaten** in `data/` unterliegen den Lizenzen der jeweiligen Quellen (CC BY-SA 4.0, dl-de/by-2-0, dl-de/zero-2-0) – siehe [Datenquellen & Lizenzen](#datenquellen--lizenzen). Eine Namensnennung der Originalquellen ist bei Weiternutzung erforderlich.
