# VNBdigitaler

Angelehnt an den Namen des Portals VNBdigital, bietet diese App eine deutlich einfachere Möglichkeit, an die Kundenrelevanten Daten der Netzbetreiber zu gelangen. Da weder diese, noch das besagte Portal einen API Zugriff bieten, basieren die Daten im wesentlichen noch auf der manuellen Recherche der Preisblätter.

Helft also alle mit und steuert Daten über GitHub Pull-Requests bei.

Dieser Service basiert auf der kostenlosen Version von Streamlit.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://movies-dataset-template.streamlit.app/)

### Auf dem eigenen Rechner ausführen

1. uv installieren (empfohlen)

   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. Dependencies installieren

   ```bash
   uv sync
   ```

3. App starten

   ```bash
   uv run streamlit run streamlit_app.py
   ```

#### Alternative mit pip

1. Python Virtual Environment erstellen

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # oder
   venv\Scripts\activate     # Windows
   ```

2. Dependencies installieren

   ```bash
   pip install -e ".[dev]"
   ```

3. App starten

   ```bash
   streamlit run streamlit_app.py
   ```

## Datenherkunft

Die Daten stammen von der Bundesnetzagentur und den Preisblättern der einzelnen Netzbetreiber:

  - [BNetzA iMSys Rollout Report](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/NetzzugangMesswesen/Mess-undZaehlwesen/iMSys/artikel.html).
  - [Netzbetreibernummern](https://bdew-codes.de/Codenumbers/ElectricityGridOperatorCodes/ElectricityGridCodeNumbers)

# Datenimport

## Verteilnetzbetreiber

Der Datenimport der Netzbetreibernummern erfolgt einfach über den Download des Excel-Files (siehe Netzbetreibernummern oben), Copy-Paste in eine Textdate (Tabulator-separiert) und dann ein ausführen des Helfer Skripts:

```bash
python tools/convert_vnbtsv_to_pgsql.py "tab-seperated-file" > tmp_out.pgsql
```

Den Text dann einfach als Statement in PostgreSQL ausführen (z.B. im SQL-Editor im Neon-Projekt). Sollten sich die Daten einer Verteilnetzbetreibernummer ändern, werden diese aktualisiert. Bei gleichen Betreibern für verschiedene Betreibernummern erfolgt eine Warnung bei der Konvertierung. Doppelte VNB-Nummern werden ignoriert und ebenfalls eine Warnung ausgegeben.

## Rollout-Quoten

Dies muss ich noch machen 😜
