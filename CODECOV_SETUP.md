# Codecov Setup Anleitung

## Problem

Die CI/CD Pipeline schlägt bei der Coverage-Upload fehl mit der Meldung:

```
Upload failed: {"message":"Token required because branch is protected"}
```

## Lösung

### 1. Codecov Account einrichten

1. Gehen Sie zu [https://codecov.io](https://codecov.io)
2. Loggen Sie sich mit Ihrem GitHub Account ein
3. Fügen Sie das Repository `the78mole/vnbdigitaler` hinzu

### 2. Repository Token abrufen

1. Wählen Sie das Repository in Codecov aus
2. Gehen Sie zu Settings → General
3. Kopieren Sie den "Repository Upload Token"

### 3. GitHub Secret hinzufügen

1. Gehen Sie zu GitHub: `https://github.com/the78mole/vnbdigitaler/settings/secrets/actions`
2. Klicken Sie auf "New repository secret"
3. Fügen Sie ein neues Secret hinzu:
   - **Name**: `CODECOV_TOKEN`
   - **Value**: Der Token aus Schritt 2

### 4. CI-Konfiguration (bereits erledigt)

Die CI-Konfiguration wurde bereits aktualisiert:

```yaml
- name: Upload coverage reports
  if: matrix.python-version == '3.11'
  uses: codecov/codecov-action@v5
  with:
    files: ./coverage.xml
    token: ${{ secrets.CODECOV_TOKEN }}
    fail_ci_if_error: false
```

## Nach der Einrichtung

Nach dem Hinzufügen des Tokens sollten zukünftige CI-Runs erfolgreich Coverage-Reports zu Codecov hochladen.

## Testen

Sie können die CI manuell ausführen oder einen neuen Commit pushen, um die Funktionalität zu testen.
