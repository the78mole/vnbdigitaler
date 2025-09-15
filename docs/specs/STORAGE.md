# ☁️ VNB Digitaler - Object Storage & Document Management

> **⚙️ Technische Spezifikation**: [SPECIFICATION.md](./SPECIFICATION.md) - Architektur und API-Details
> **🚀 Deployment**: [DEPLOYMENT.md](./DEPLOYMENT.md) - Cloudflare R2 Setup
> **🧪 Testing**: [TESTING.md](./TESTING.md) - R2 Storage Tests

---

## ☁️ Object Storage Architecture

### Cloudflare R2 für PDF-Preisblätter

Das VNB Digitaler Projekt nutzt Cloudflare R2 als S3-kompatiblen Object Storage für die Speicherung von PDF-Dokumenten, Preisblättern und Backup-Dateien.

## 🔧 Cloudflare R2 Integration

```python
# Cloudflare R2 Integration für PDF-Preisblätter
class R2DocumentStorage:
    bucket_name: str = "vnbdigitaler"
    base_path: str = "documents/price-sheets/"

    # Document Organization
    # vnbdigitaler/
    #   └── documents/
    #       ├── price-sheets/
    #       │   ├── 2025/
    #       │   │   ├── 09/
    #       │   │   │   └── {company_code}_{document_type}_{date}.pdf
    #       │   └── archive/
    #       ├── tab-documents/
    #       └── forms/

    def store_price_sheet(self, company_code: str, pdf_content: bytes,
                         metadata: dict) -> str:
        """Store PDF with traceability metadata"""
        object_key = f"documents/price-sheets/{datetime.now().year}/" \
                    f"{datetime.now().month:02d}/" \
                    f"{company_code}_{metadata['type']}_{metadata['date']}.pdf"

        # Store with metadata for traceability
        return self.upload_with_metadata(object_key, pdf_content, metadata)

# S3-compatible client configuration
import boto3
r2_client = boto3.client(
    's3',
    endpoint_url='https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com',
    aws_access_key_id=CLOUDFLARE_R2_ACCESS_KEY,
    aws_secret_access_key=CLOUDFLARE_R2_SECRET_KEY,
    region_name='auto'
)
```

## 📁 Document Organization

### Ordnerstruktur

```
vnbdigitaler/
├── documents/
│   ├── price-sheets/
│   │   ├── 2025/
│   │   │   ├── 01/
│   │   │   ├── 02/
│   │   │   └── ...
│   │   └── archive/
│   ├── tab-documents/
│   │   ├── standard/
│   │   └── custom/
│   └── forms/
│       ├── application-forms/
│       └── registration-forms/
├── backups/
│   ├── database/
│   └── configurations/
└── temp/
    └── processing/
```

## 🏷️ Storage Classes

### R2 Storage Classes

- **Standard**: Für häufig abgerufene Dokumente (aktuelle Preisblätter)
- **Infrequent Access**: Für ältere Dokumente (Archive)
- **Glacier**: Für Langzeit-Backup (jährliche Archive)

## ⚙️ Client Configuration

### Umgebungsvariablen

```bash
# Cloudflare R2 Object Storage
CLOUDFLARE_R2_ACCESS_KEY=your-r2-access-key
CLOUDFLARE_R2_SECRET_KEY=your-r2-secret-key
CLOUDFLARE_R2_ACCOUNT_ID=your-cloudflare-account-id
CLOUDFLARE_R2_BUCKET_NAME=vnbdigitaler
CLOUDFLARE_R2_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
CLOUDFLARE_R2_PUBLIC_URL=https://r2.vnbdigitaler.de
```

### Client Initialization

```python
import boto3
from botocore.config import Config

# Initialize Cloudflare R2 client
config = Config(
    region_name='auto',
    retries={'max_attempts': 3, 'mode': 'adaptive'},
    max_pool_connections=50
)

r2_client = boto3.client(
    's3',
    endpoint_url=os.getenv('CLOUDFLARE_R2_ENDPOINT_URL'),
    aws_access_key_id=os.getenv('CLOUDFLARE_R2_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('CLOUDFLARE_R2_SECRET_KEY'),
    config=config
)
```

---

_Diese Dokumentation beschreibt die Object Storage-Architektur und Cloudflare R2-Integration für das VNB Digitaler Projekt._
