# BDEW Admin WebUI

Eine FastAPI-basierte Web-Administration für die BDEW VNB Digitaler Datenbank.

## Dateien-Struktur

```
admin_api.py                     # Haupt-Admin API (FastAPI Backend)
templates/admin_dashboard.html   # HTML Template für das Dashboard
static/js/admin_dashboard.js     # JavaScript für AlpineJS Dashboard
archive/                         # Archivierte alte Admin-Versionen
├── admin_api_alpine.py         # Alte AlpineJS Version (inline HTML)
├── admin_api_fixed.py          # Fixed Version ohne AlpineJS
├── admin_simple.py             # Einfache Debug-Version
└── admin_api.py                # Ursprüngliche API Version
```

## Features

- **Dashboard** - Statistiken über Unternehmen, BDEW-Codes und Marktfunktionen
- **Unternehmen-Verwaltung** - Liste aller Unternehmen mit Code-Anzahl
- **BDEW-Codes** - Übersicht aller registrierten BDEW-Codes
- **Marktfunktionen** - Verwaltung der Marktfunktionen
- **Company Details Modal** - Detailansicht für einzelne Unternehmen
- **Quote-Trimming** - Automatisches Entfernen von Anführungszeichen aus Firmennamen

## Technologie

- **Backend**: FastAPI mit PostgreSQL
- **Frontend**: TailwindCSS + AlpineJS
- **Templates**: Jinja2 Templates
- **Database**: PostgreSQL (vnb_digitaler)

## Verwendung

```bash
# Admin-Interface starten
uv run uvicorn admin_api:app --reload --host 0.0.0.0 --port 8000

# Dashboard aufrufen
open http://localhost:8000
```

## API Endpoints

- `GET /` - Admin Dashboard (HTML)
- `GET /api/dashboard/stats` - Dashboard Statistiken
- `GET /api/companies` - Liste aller Unternehmen
- `GET /api/companies/{company_name}` - Unternehmensdetails
- `GET /api/bdew-codes` - Alle BDEW-Codes
- `GET /api/market-functions` - Alle Marktfunktionen

## Cleanup History

Die alten Admin-Dateien wurden ins `archive/` Verzeichnis verschoben:

1. **admin_api_alpine.py** - Ursprüngliche AlpineJS Version mit inline HTML
2. **admin_api_fixed.py** - Fixed Version ohne AlpineJS
3. **admin_simple.py** - Einfache Debug-Version
4. **admin_api.py (alt)** - Ursprüngliche API mit Templates-Support

Die aktuelle Version (`admin_api.py`) kombiniert die besten Features aller vorherigen Versionen mit sauberer Trennung von Backend und Frontend.
