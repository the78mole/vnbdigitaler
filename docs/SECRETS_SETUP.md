# GitHub Secrets Setup Documentation

## Required Repository Secrets

Die folgenden Secrets müssen in GitHub Actions konfiguriert werden:
Repository Settings > Secrets and variables > Actions > Repository secrets

### Database Secrets
```
NEON_DATABASE_URL
Value: postgresql+asyncpg://user:password@host:5432/database
Description: Neon PostgreSQL database connection string
```

### AI Service Secrets
```
OPENROUTER_API_KEY
Value: or-xxx
Description: OpenRouter API key for AI model access
```

### Object Storage Secrets
```
CLOUDFLARE_R2_ACCESS_KEY
Value: xxx
Description: Cloudflare R2 access key

CLOUDFLARE_R2_SECRET_KEY
Value: xxx
Description: Cloudflare R2 secret key

CLOUDFLARE_R2_BUCKET_NAME
Value: vnb-documents
Description: Cloudflare R2 bucket name

CLOUDFLARE_R2_ENDPOINT
Value: https://xxx.r2.cloudflarestorage.com
Description: Cloudflare R2 endpoint URL
```

### Optional Monitoring Secrets
```
SENTRY_DSN
Value: https://xxx@sentry.io/xxx
Description: Sentry error tracking DSN (optional)

SLACK_WEBHOOK_URL
Value: https://hooks.slack.com/xxx
Description: Slack webhook for notifications (optional)
```

## Environment Variables für GitHub Actions

Diese werden automatisch in den Workflows gesetzt:
- `ENVIRONMENT=production`
- `LOG_LEVEL=INFO`

## Security Best Practices

1. **Niemals Secrets in Code committen**
2. **Regelmäßige Rotation der API Keys**
3. **Minimale Berechtigungen für Service Accounts**
4. **Monitoring von Secret-Zugriff**

## Setup Checklist

- [ ] Neon Database erstellt und Connection String hinzugefügt
- [ ] OpenRouter Account erstellt und API Key generiert
- [ ] Cloudflare R2 Bucket erstellt und Credentials konfiguriert
- [ ] Alle Secrets in GitHub Repository Settings eingefügt
- [ ] Secrets in Streamlit Cloud konfiguriert
- [ ] Lokale .env Datei erstellt (nicht committen!)

## Testing

Nach dem Setup kannst du die Konfiguration testen:

```bash
# Lokale Umgebung testen
uv run python -c "from src.config import get_settings; print(get_settings().environment)"

# GitHub Actions testen
# Workflow ausführen und Logs überprüfen
```
