# Feature-Tracking

# Aktuelle TODO-Liste

# Nächste Verbesserungen

- [ ] Adresse des Unternehmens über Nominatim in GeoKoordinaten auflösen
- [ ] Map-Darstellung mit einem Fähnchen/Geolocation-Indicator versehen, der den Standort anzeigt
- [ ] Tooltip mit Unternehmensinformationen bei Mouseover auf dem Fähnchen anzeigen
- [ ] Tooltips der Features verbessern (aktuell ziemlich sinnlose Infos für den Nutzer)
- [ ] Tabellen sortierbar machen (Responsive Tables)

# Mittelfristige Verbesserungen

- [ ] Definieren, was in die Streamlit-App und was in die webui kommen soll
- [ ] Link zum Unternemen implementieren
- [ ] Preisblatt Netz des Unternehmens finden
- [ ] Relevante Preisinformationen für Verteilnetzbetreiber definieren
- [ ] Daten aus Preisblatt extrahieren und in Datenbank schreiben
- [ ] Charts für die Entwicklung der Preisinformationen erstellen
- [ ] Charts für die Entwicklung der Roll-Out-Quoten erstellen
- [ ] Timeline für die Quartalsabdeckung der variablen Netzentgelte darstellen

## Feature-Status Übersicht

<table>
<thead>
  <tr>
    <th>Feature</th>
    <th align="center">Admin-UI<br/>(webui)</th>
    <th align="center">User-UI<br/>(streamlit)</th>
    <th align="center">Actions<br/>(GitHub)</th>
    <th>Beschreibung</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td colspan="5"><strong>📊 Datenverwaltung</strong></td>
  </tr>
  <tr>
    <td>Unternehmensliste</td>
    <td align="center">✅</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>Liste aller VNB mit Details</td>
  </tr>
  <tr>
    <td>Unternehmensdetails</td>
    <td align="center">✅</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>Einzelansicht mit Karte und Daten</td>
  </tr>
  <tr>
    <td>Roll-Out-Datenverwaltung</td>
    <td align="center">✅</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td>BNetzA Roll-Out-Quoten verwalten</td>
  </tr>
  <tr>
    <td>CSV-Import</td>
    <td align="center">✅</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td>Roll-Out-Daten importieren</td>
  </tr>
  <tr>
    <td colspan="5"><strong>🗺️ Kartenfunktionen</strong></td>
  </tr>
  <tr>
    <td>Interaktive Karte</td>
    <td align="center">✅</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>Leaflet-basierte VNB-Karte</td>
  </tr>
  <tr>
    <td>Administrative Grenzen</td>
    <td align="center">✅</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>Länder/Bundesländer/Landkreise</td>
  </tr>
  <tr>
    <td>Service Areas</td>
    <td align="center">✅</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>VNB-Versorgungsgebiete</td>
  </tr>
  <tr>
    <td>Geolocation Marker</td>
    <td align="center">⏸️</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>Fähnchen für Unternehmensstandorte</td>
  </tr>
  <tr>
    <td colspan="5"><strong>📈 Datenanalyse</strong></td>
  </tr>
  <tr>
    <td>Roll-Out-Statistiken</td>
    <td align="center">⏸️</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>Quartalsvergleiche und Trends</td>
  </tr>
  <tr>
    <td>Preisdatenanalyse</td>
    <td align="center">⏸️</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>Netzentgelt-Entwicklung</td>
  </tr>
  <tr>
    <td>Charts/Visualisierung</td>
    <td align="center">⏸️</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>Interaktive Diagramme</td>
  </tr>
  <tr>
    <td colspan="5"><strong>📥 Datenbeschaffung</strong></td>
  </tr>
  <tr>
    <td>PDF-Preisblatt-Extraktion</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td align="center">⏸️</td>
    <td>Automatische Preisdatenextraktion</td>
  </tr>
  <tr>
    <td>Adressauflösung (Nominatim)</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td align="center">⏸️</td>
    <td>Geocoding für Unternehmensadressen</td>
  </tr>
  <tr>
    <td>BNetzA Roll-Out Download</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td align="center">⏸️</td>
    <td>Quartalsweise Datenaktualisierung</td>
  </tr>
  <tr>
    <td>BDEW Daten-Sync</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td align="center">⏸️</td>
    <td>VNB-Stammdaten aktualisieren</td>
  </tr>
  <tr>
    <td colspan="5"><strong>🎨 UI/UX Features</strong></td>
  </tr>
  <tr>
    <td>Responsive Design</td>
    <td align="center">✅</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>Mobile-optimierte Ansichten</td>
  </tr>
  <tr>
    <td>Sortierbare Tabellen</td>
    <td align="center">⏸️</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>Spalten-basierte Sortierung</td>
  </tr>
  <tr>
    <td>Erweiterte Filter</td>
    <td align="center">✅</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>Such- und Filterfunktionen</td>
  </tr>
  <tr>
    <td>Tooltips/Hilfetexte</td>
    <td align="center">⏸️</td>
    <td align="center">⏸️</td>
    <td align="center">❌</td>
    <td>Benutzerfreundliche Erklärungen</td>
  </tr>
  <tr>
    <td colspan="5"><strong>🤖 Automatisierung</strong></td>
  </tr>
  <tr>
    <td>Scheduled Data Updates</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td align="center">⏸️</td>
    <td>Regelmäßige Datenaktualisierung</td>
  </tr>
  <tr>
    <td>Data Validation</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td align="center">⏸️</td>
    <td>Automatische Datenqualitätsprüfung</td>
  </tr>
  <tr>
    <td>Backup & Archiving</td>
    <td align="center">❌</td>
    <td align="center">❌</td>
    <td align="center">⏸️</td>
    <td>Datensicherung und Archivierung</td>
  </tr>
</tbody>
</table>

### Legende

- ✅ **Implementiert**: Feature ist vollständig umgesetzt
- ⏸️ **Geplant**: Feature ist in Planung/Entwicklung
- ❌ **Nicht geplant**: Feature ist für diese UI nicht vorgesehen
