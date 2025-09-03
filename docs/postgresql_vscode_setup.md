# PostgreSQL Extension Setup Guide

## 🔧 **Aktuelle Konfiguration**

Die PostgreSQL-Extensions für VS Code sind bereits konfiguriert:

### **Installierte Extensions:**

- ✅ **PostgreSQL** (`ckolkman.vscode-postgres`) - Bereits installiert
- ✅ **SQLTools** (`mtxr.sqltools`) - Bereits installiert
- ✅ **SQLTools PostgreSQL Driver** (`mtxr.sqltools-driver-pg`) - Installiert

### **Konfigurierte Verbindungen:**

- **Name**: "VNB Digitaler"
- **Host**: localhost:5432
- **Database**: vnbdigitaler
- **User**: postgres (ohne Passwort)

## 🚀 **Anleitung zur Verwendung**

### **Option 1: SQLTools (Empfohlen)**

1. **Öffne die SQLTools-Sidebar**:

   - Klicke auf das Datenbank-Symbol in der linken Seitenleiste
   - Oder: `Ctrl+Shift+P` → "SQLTools: Focus on Explorer"

2. **Verbinde zur Datenbank**:

   - Klicke auf "VNB Digitaler" in der Verbindungsliste
   - Die Verbindung sollte automatisch ohne Passwort erfolgen

3. **Browse die Datenbank**:

   - Erweitere "Tables" um die 4 BDEW-Tabellen zu sehen:
     - `bdew_companies`
     - `bdew_import_logs`
     - `bdew_validation_rules`
     - `bdew_data_history`

4. **Führe Queries aus**:
   - Öffne `sql/test_queries.sql`
   - Wähle eine Query aus und drücke `Ctrl+E` (oder `Cmd+E`)

### **Option 2: PostgreSQL Extension**

1. **Command Palette öffnen**: `Ctrl+Shift+P`
2. **Suche**: "PostgreSQL: Connect"
3. **Wähle**: "VNB Digitaler (Local)" aus der Liste

### **Option 3: Terminal (Fallback)**

```bash
# Direkte psql-Verbindung
psql -h localhost -U postgres -d vnbdigitaler

# Beispiel-Queries
\dt                           # Zeige Tabellen
SELECT count(*) FROM bdew_companies;
\q                           # Beenden
```

## 🔍 **Troubleshooting**

### **Problem: Extension zeigt keine Daten**

```bash
# 1. PostgreSQL-Status prüfen
pg_isready -h localhost -p 5432

# 2. Verbindung testen
psql -h localhost -U postgres -d vnbdigitaler -c "SELECT 1;"

# 3. Tabellen überprüfen
psql -h localhost -U postgres -d vnbdigitaler -c "\dt"
```

### **Problem: Verbindung fehlgeschlagen**

- Stelle sicher, dass PostgreSQL läuft
- Überprüfe, dass die vnbdigitaler-Datenbank existiert
- Restart VS Code und versuche erneut zu verbinden

### **Problem: Keine IntelliSense**

- Öffne eine .sql-Datei (z.B. `sql/test_queries.sql`)
- Stelle sicher, dass SQLTools verbunden ist
- IntelliSense sollte automatisch funktionieren

## ✅ **Verifikation**

Die Konfiguration ist korrekt, wenn du folgendes siehst:

1. **SQLTools-Sidebar**: "VNB Digitaler" mit grünem Verbindungs-Status
2. **Tabellen sichtbar**: 4 BDEW-Tabellen werden angezeigt
3. **Query-Execution**: Test-Queries in `sql/test_queries.sql` laufen erfolgreich
4. **IntelliSense**: Auto-Complete für Tabellen- und Spaltennamen

## 📊 **Test-Queries**

Verwende die vorkonfigurierten Queries in `sql/test_queries.sql`:

- Tabellen-Übersicht
- BDEW-Companies-Status
- Import-Log-Statistiken
- PostgreSQL-Extensions
- Datenbank-Informationen

**Status**: ✅ **Konfiguration abgeschlossen - Bereit zur Verwendung!**
