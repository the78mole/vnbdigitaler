# Notizenaus dem Entwicklungsverlauf

## Admin UI

- Letze Sync sollte die API ein Datum zurückliefern und Javascript dann die Umsetzung in
  human readable z.B. auf heute, vor einer Woche,... erledigen.
- Tabelle funktioniert grundsätzlich, aber die pagination hat noch Schluckauf:
  "Showing 0 to 0 of 0 entries (filtered from NaN total entries)"
- Browser-Console-Fehler:
  Access to XMLHttpRequest at '<http://cdn.datatables.net/plug-ins/1.13.7/i18n/de-DE.json>' from origin '<http://localhost:8000>' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.Understand this error
  jquery-3.7.1.min.js:2 XHR failed loading: GET "<http://cdn.datatables.net/plug-ins/1.13.7/i18n/de-DE.json>".
