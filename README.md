# BOS-Map
Eine Interaktive Karte Deutschlands mit einem Datenverzeichnis aller Leitstellen mit API im Backend zum Datenabruf

Möglichkeiten der Anwendung.

- [ ] Interaktive Karte von deutschland
- [ ] Backend: Datenbank mit allen leitstellen nach Vorlage
- [ ] Klick auf Karte oder Adresssuche über eingabe zeigt zuständige leitstelle und deren Funkgruppen
- [ ] API mit möglichkeiten Abruf leitstelle über Koordinaten/3Word ausgabe der Leitstelle Anrufgruppe etc
- [ ] Einfaches & Flaches Hosting über Github oder simplen webserver

## Zielschema Datenbank
```json
{
  "type": "Feature",
  "properties": {
    "leitstellen_id": "DE-BY-ILS-MUE",
    "leitstellenname": "ILS München",
    "bundesland": "BY",
    "traeger": "ZRF München",
    "betreiber": "Berufsfeuerwehr München",
    "adresse": "Heßstraße 120, 80797 München",
    "quelltyp": "amtlich_wfs|amtlich_html|recht_abgeleitet|community",
    "funkgruppen": [
      {"name": "M_Fw", "rolle": "Feuerwehr", "quelle": "landeskonzept"},
      {"name": "M_RD", "rolle": "Rettungsdienst", "quelle": "landeskonzept"}
    ],
    "frequenzschema": "Digitalfunk BOS TETRA",
    "geometry_basis": "amtliche_grenze|verwaltungsgrenze_abgeleitet",
    "source_url": "https://...",
    "valid_from": "2026-05-11",
    "valid_to": null,
    "review_status": "verified"
  },
  "geometry": {
    "type": "MultiPolygon",
    "coordinates": []
  }
}
```
