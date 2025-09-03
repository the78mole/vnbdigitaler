#!/usr/bin/env python3
"""
vnbdigitaler CLI - BDEW Verteilnetzbetreiber-Datenmanagement.

Einfaches Kommandozeilentool für automatisierten Import und Verwaltung
von BDEW-Netzbetreiberdaten mit intelligenten Standardwerten.

Usage:
  vnbdigitaler bdew import [<file>] [--dry-run] [--verbose]
  vnbdigitaler bdew search <query> [--limit=<num>]
  vnbdigitaler bdew stats [--format=<fmt>]
  vnbdigitaler init [--db-url=<url>]
  vnbdigitaler --help
  vnbdigitaler --version

Commands:
  bdew import   Importiere BDEW-Daten (Web-Download oder lokale Datei)
                - Ohne Datei: Automatischer Download von BDEW-Website
                - Mit Datei: Import aus lokaler CSV/Excel-Datei
                - Führt komplette Pipeline aus: Download → Validate → Store → Log

  bdew search   Durchsuche importierte BDEW-Daten nach Netzbetreibern
  bdew stats    Zeige Statistiken über den aktuellen Datenbestand
  init          Initialisiere Datenbank und Konfiguration

Options:
  -h --help                 Zeige diese Hilfe
  --version                 Zeige Versionsnummer
  -v --verbose              Ausführliche Ausgabe mit Pipeline-Details
  --dry-run                 Zeige was passieren würde, ohne Änderungen
  --limit=<num>             Max. Suchergebnisse [default: 20]
  --format=<fmt>            Ausgabeformat: table, json [default: table]
  --db-url=<url>            Datenbank-URL [default: sqlite:///tmp/vnbdigitaler.db]

Examples:
  # BDEW-Daten automatisch von Website importieren
  vnbdigitaler bdew import

  # Lokale Datei importieren
  vnbdigitaler bdew import data/bdew_operators.csv

  # Import simulieren (nichts ändern)
  vnbdigitaler bdew import --dry-run --verbose

  # Nach Stadtwerken suchen
  vnbdigitaler bdew search "stadtwerke münchen"

  # Datenbestand-Statistiken anzeigen
  vnbdigitaler bdew stats

  # Datenbank initialisieren
  vnbdigitaler init

Pipeline-Schritte (bdew import):
  1. 📥 Download/Load  - Lade Daten von BDEW-Website oder Datei
  2. ✅ Validate       - Prüfe Datenqualität und Format
  3. 💾 Store          - Speichere in Datenbank (mit Deduplizierung)
  4. 📊 Log            - Erstelle Import-Protokoll

Defaults:
  - Cache: tmp/cache/bdew/
  - Database: tmp/vnbdigitaler.db (SQLite)
  - Logs: tmp/logs/
  - Alle Verzeichnisse werden automatisch erstellt
  - Web-Download verwendet offizielle BDEW-API mit Paginierung
  - Automatische Datenvalidierung und Qualitätsbewertung

Notes:
  - Bei erstem Aufruf wird automatisch die Datenbank initialisiert
  - Web-Import lädt aktuelle Daten direkt von bdew-codes.de
  - Dry-Run zeigt alle Pipeline-Schritte ohne Datenbank-Änderungen
  - Verbose-Modus zeigt detaillierte Fortschrittsinformationen
"""
