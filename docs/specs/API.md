# 🔌 VNB Digitaler - API Documentation

> **📋 Projekt-Roadmap**: [ROADMAP.md](./ROADMAP.md) - Phasen und Meilensteine
> **⚙️ Technische Spezifikation**: [SPECIFICATION.md](./SPECIFICATION.md) - Architektur und Details
> **🧪 Testing**: [TESTING.md](./TESTING.md) - Tests und Code Quality
> **🚀 Deployment**: [DEPLOYMENT.md](./DEPLOYMENT.md) - Production Setup

## 📡 API-Architektur Übersicht

Das VNB Digitaler Projekt bietet drei Haupt-API-Interfaces:

```

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Admin API     │    │ Installer API   │    │  Public API     │
│   (Port 8081)   │    │   (Port 8080)   │    │  (Streamlit)    │
│                 │    │                 │    │                 │
│ • Data Explorer │    │ • OAuth Login   │    │ • Company Search│
│ • Validation    │    │ • Guest Entry   │    │ • Price Compare │
│ • Manual Edits  │    │ • TAB Documents │    │ • Territory Info│
│ • Quality Ctrl  │    │ • Data Pipelines│    │ • Data Export   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                   ┌─────────────────┐
                   │  Neon Database  │
                   │  (PostgreSQL)   │
                   └─────────────────┘

```

## 🔐 Admin API (Port 8081)

### Authentication

#### Admin Login

```http
POST /admin/auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin_password"  // pragma: allowlist secret
}

```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "username": "admin",
    "roles": ["admin"],
    "permissions": ["read", "write", "delete"]
  }
}
```

#### Token Validation

```http
GET /admin/auth/me
Authorization: Bearer {access_token}

```

**Response:**

```json
{
  "username": "admin",
  "is_active": true,
  "last_login": "2025-09-15T10:30:00Z",
  "permissions": ["read", "write", "delete"]
}
```

### Data Explorer

#### Table List

```http
GET /admin/tables
Authorization: Bearer {access_token}

```

**Response:**

```json
{
  "tables": [
    {
      "name": "grid_operators",
      "rows": 889,
      "updated": "2025-09-15T10:00:00Z",
      "description": "BDEW-registered grid operators",
      "size_mb": 12.5
    },
    {
      "name": "rollout_data",
      "rows": 234,
      "updated": "2025-09-15T09:30:00Z",
      "description": "BNetzA smart meter rollout data",
      "size_mb": 3.2
    },
    {
      "name": "price_sheets",
      "rows": 156,
      "updated": "2025-09-15T08:45:00Z",
      "description": "Extracted §14a price information",
      "size_mb": 8.7
    }
  ],
  "total_tables": 8,
  "total_size_mb": 45.3
}
```

#### Table Data

```http
GET /admin/tables/{table_name}?limit=100&offset=0&search={query}&sort={field}&order={asc|desc}
Authorization: Bearer {access_token}

```

**Example:**

```http
GET /admin/tables/grid_operators?limit=50&search=stadtwerke&sort=name&order=asc

```

**Response:**

```json
{
  "data": [
    {
      "id": "{grid-operator-uuid}",
      "code": "123456789012",
      "name": "Stadtwerke München GmbH",
      "city": "München",
      "postal_code": "80331",
      "status": "active",
      "roles": ["VNB", "EVU"],
      "updated_at": "2025-09-15T09:15:00Z"
    }
  ],
  "total": 889,
  "columns": [
    { "name": "id", "type": "uuid", "nullable": false },
    { "name": "code", "type": "string", "nullable": false },
    { "name": "name", "type": "string", "nullable": false },
    { "name": "city", "type": "string", "nullable": true },
    { "name": "postal_code", "type": "string", "nullable": true },
    { "name": "status", "type": "enum", "nullable": false },
    { "name": "roles", "type": "array", "nullable": false }
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 18,
    "has_next": true,
    "has_prev": false
  }
}
```

#### Data Quality Check

```http
GET /admin/data-quality/{table_name}
Authorization: Bearer {access_token}

```

**Response:**

```json
{
  "table": "grid_operators",
  "total_rows": 889,
  "quality_score": 0.92,
  "issues": {
    "duplicates": 3,
    "null_values": {
      "city": 12,
      "postal_code": 8,
      "phone": 45
    },
    "validation_errors": [
      {
        "row_id": "{other-uuid-1}",
        "field": "code",
        "error": "Invalid BDEW code format",
        "severity": "error"
      }
    ],
    "data_inconsistencies": [
      {
        "description": "Mismatched city and postal code",
        "affected_rows": 5,
        "severity": "warning"
      }
    ]
  },
  "recommendations": [
    "Update null postal codes using city information",
    "Validate BDEW codes against official registry",
    "Review duplicate entries for potential merging"
  ]
}
```

### Linkage Management

#### Linkage Overview

```http
GET /admin/linkages
Authorization: Bearer {access_token}

```

**Response:**

```json
{
  "summary": {
    "bdew_companies": 889,
    "bnetza_companies": 234,
    "total_matches": 234,
    "match_rate": 0.87
  },
  "linkage_types": {
    "exact_matches": {
      "count": 156,
      "percentage": 66.7,
      "confidence_avg": 1.0
    },
    "fuzzy_matches": {
      "count": 78,
      "percentage": 33.3,
      "confidence_avg": 0.85
    },
    "unmatched_bdew": 45,
    "unmatched_bnetza": 0
  },
  "quality_metrics": {
    "avg_confidence": 0.92,
    "manual_reviews_pending": 12,
    "disputed_matches": 3
  }
}
```

#### Manual Link Creation

```http
POST /admin/linkages
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "bdew_id": "{grid-operator-uuid}",
    "bnetza_id": "{bnetza-uuid}",
    "confidence": 0.95,
    "method": "manual",
    "reviewer": "admin",
    "notes": "Verified via company website and registration documents"
}

```

**Response:**

```json
{
  "linkage_id": "{linkage-uuid}",
  "status": "created",
  "confidence": 0.95,
  "created_at": "2025-09-15T11:30:00Z",
  "reviewer": "admin"
}
```

#### Bulk Review

```http
GET /admin/linkages/review?status=pending&limit=50&min_confidence=0.8
Authorization: Bearer {access_token}

```

**Response:**

```json
{
  "pending_reviews": [
    {
      "linkage_id": "{linkage-uuid-2}",
      "bdew": {
        "id": "{grid-operator-uuid}",
        "name": "Stadtwerke München GmbH",
        "city": "München",
        "code": "123456789012"
      },
      "bnetza": {
        "id": "{bnetza-uuid}",
        "name": "SWM Infrastruktur GmbH",
        "city": "München",
        "rollout_quota": 0.15
      },
      "confidence": 0.87,
      "similarity_factors": {
        "name_similarity": 0.82,
        "location_match": 1.0,
        "size_compatibility": 0.9
      },
      "suggested_action": "approve",
      "auto_generated": true,
      "created_at": "2025-09-15T09:45:00Z"
    }
  ],
  "pagination": {
    "total": 12,
    "current_page": 1,
    "per_page": 50
  }
}
```

### Document Storage (Cloudflare R2)

#### Upload PDF Document

```http
POST /admin/documents/upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file: {PDF file}
company_id: {grid-operator-uuid}
document_type: "price_sheet_14a"
effective_date: "2025-01-01"
source_url: "https://example-vnb.de/preisblatt.pdf"
extraction_method: "manual"
```

**Response:**

```json
{
  "document_id": "{document-uuid}",
  "r2_object_key": "documents/price-sheets/2025/09/123456789012_price_sheet_14a_2025-01-01.pdf",
  "r2_url": "https://r2.vnbdigitaler.de/documents/price-sheets/2025/09/123456789012_price_sheet_14a_2025-01-01.pdf",
  "document_hash": "sha256:a1b2c3d4e5f6...",
  "file_size_bytes": 2468013,
  "upload_status": "success",
  "uploaded_at": "2025-09-15T14:30:00Z",
  "traceability": {
    "original_filename": "preisblatt_2025_swm.pdf",
    "mime_type": "application/pdf",
    "uploaded_by": "admin",
    "source_verified": false
  }
}
```

#### Download PDF Document

```http
GET /admin/documents/{document_id}/download
Authorization: Bearer {access_token}
```

**Response:** Binary PDF content with appropriate headers:

```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Length: 2468013
Content-Disposition: attachment; filename="123456789012_price_sheet_14a_2025-01-01.pdf"
Cache-Control: private, max-age=3600
ETag: "a1b2c3d4e5f6..."
```

#### List Stored Documents

```http
GET /admin/documents?company_id={grid-operator-uuid}&type=price_sheet&limit=50&verified_only=false
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "documents": [
    {
      "document_id": "{document-uuid}",
      "company_name": "Stadtwerke München GmbH",
      "document_type": "price_sheet_14a",
      "effective_date": "2025-01-01",
      "file_size_bytes": 2468013,
      "uploaded_at": "2025-09-15T14:30:00Z",
      "verified": false,
      "verification_status": "pending_review",
      "r2_url": "https://r2.vnbdigitaler.de/documents/price-sheets/2025/09/123456789012_price_sheet_14a_2025-01-01.pdf",
      "traceability": {
        "uploaded_by": "admin",
        "extraction_method": "manual",
        "source_url": "https://example-vnb.de/preisblatt.pdf",
        "integrity_verified": true
      }
    }
  ],
  "pagination": {
    "total": 156,
    "current_page": 1,
    "per_page": 50
  },
  "storage_stats": {
    "total_documents": 156,
    "total_size_mb": 384.7,
    "verified_documents": 142,
    "pending_verification": 14
  }
}
```

#### Verify Document

```http
POST /admin/documents/{document_id}/verify
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "verification_status": "verified",  // "verified" | "rejected" | "needs_review"
    "verified_by": "admin",
    "verification_notes": "Prices extracted and validated against VNB website",
    "extracted_data": {
        "base_price_ct_kwh": 28.5,
        "section_14a_reduction_percent": 12.5,
        "effective_from": "2025-01-01",
        "tariff_name": "Grundversorgung"
    }
}
```

**Response:**

```json
{
  "document_id": "{document-uuid}",
  "verification_status": "verified",
  "verified_by": "admin",
  "verified_at": "2025-09-15T15:45:00Z",
  "verification_notes": "Prices extracted and validated against VNB website",
  "data_quality_score": 0.95,
  "extracted_data": {
    "base_price_ct_kwh": 28.5,
    "section_14a_reduction_percent": 12.5,
    "effective_from": "2025-01-01",
    "tariff_name": "Grundversorgung"
  },
  "audit_trail": [
    {
      "timestamp": "2025-09-15T14:30:00Z",
      "action": "uploaded",
      "user": "admin"
    },
    {
      "timestamp": "2025-09-15T15:45:00Z",
      "action": "verified",
      "user": "admin"
    }
  ]
}
```

#### Document Integrity Check

```http
GET /admin/documents/{document_id}/integrity
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "document_id": "{document-uuid}",
  "integrity_status": "valid",
  "checks": {
    "hash_verification": {
      "status": "passed",
      "stored_hash": "sha256:a1b2c3d4e5f6...",
      "calculated_hash": "sha256:a1b2c3d4e5f6...",
      "match": true
    },
    "file_accessibility": {
      "status": "passed",
      "r2_accessible": true,
      "response_time_ms": 156
    },
    "metadata_consistency": {
      "status": "passed",
      "file_size_match": true,
      "mime_type_valid": true,
      "etag_match": true
    }
  },
  "last_checked": "2025-09-15T16:00:00Z"
}
```

#### Document Search

```http
GET /admin/documents/search?q=stadtwerke&type=price_sheet&date_from=2025-01-01&verified=true
Authorization: Bearer {access_token}
```

**Response:**

```json
{
  "results": [
    {
      "document_id": "{document-uuid}",
      "company_name": "Stadtwerke München GmbH",
      "document_type": "price_sheet_14a",
      "effective_date": "2025-01-01",
      "relevance_score": 0.92,
      "verification_status": "verified",
      "download_url": "/admin/documents/{document-uuid}/download",
      "preview_url": "/admin/documents/{document-uuid}/preview"
    }
  ],
  "search_metadata": {
    "query": "stadtwerke",
    "total_results": 15,
    "search_time_ms": 23,
    "filters_applied": ["type:price_sheet", "verified:true", "date_from:2025-01-01"]
  }
}
```

### Geographic Data

#### Geo Validation

```http
GET /admin/geo/validate
Authorization: Bearer {access_token}

```

**Response:**

```json
{
  "validation_summary": {
    "total_territories": 245,
    "valid_coordinates": 233,
    "invalid_coordinates": 12,
    "missing_postcodes": 8,
    "overlapping_territories": 3
  },
  "issues": [
    {
      "type": "invalid_coordinates",
      "company_id": "{grid-operator-uuid}",
      "company_name": "Stadtwerke Example",
      "coordinates": [0.0, 0.0],
      "severity": "error"
    },
    {
      "type": "missing_postcode",
      "company_id": "{bnetza-uuid}",
      "company_name": "Example Netz GmbH",
      "severity": "warning"
    }
  ],
  "coverage_analysis": {
    "germany_coverage": 0.94,
    "postcode_coverage": 0.87,
    "population_coverage": 0.96
  }
}
```

#### Coverage Map Data

```http
GET /admin/geo/coverage?zoom=8&bounds=48.0,11.0,49.0,12.0
Authorization: Bearer {access_token}

```

**Response:**

```json
{
  "bounds": {
    "south": 48.0,
    "west": 11.0,
    "north": 49.0,
    "east": 12.0
  },
  "grid_coverage": [
    {
      "company_id": "{grid-operator-uuid}",
      "name": "Stadtwerke München",
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [11.4, 48.0],
            [11.7, 48.0],
            [11.7, 48.3],
            [11.4, 48.3],
            [11.4, 48.0]
          ]
        ]
      },
      "properties": {
        "population_served": 150000,
        "territory_size_km2": 310.7,
        "customer_count": 45000
      }
    }
  ],
  "rollout_progress": [
    {
      "company_id": "{grid-operator-uuid}",
      "rollout_quota": 0.15,
      "installations_completed": 6750,
      "installations_target": 45000,
      "progress_percentage": 15.0
    }
  ]
}
```

### Data Control

#### Data Status

```http
GET /admin/status
Authorization: Bearer {access_token}

```

**Response:**

```json
{
  "system_status": {
    "status": "healthy",
    "last_update": "2025-09-15T08:00:00Z",
    "next_scheduled_update": "2025-09-16T02:00:00Z"
  },
  "data_sources": {
    "bdew": {
      "status": "ok",
      "records": 889,
      "last_sync": "2025-09-15T02:15:00Z",
      "sync_duration_seconds": 45,
      "errors": 0
    },
    "bnetza": {
      "status": "stale",
      "records": 234,
      "last_sync": "2025-09-13T02:30:00Z",
      "sync_duration_seconds": 23,
      "errors": 0,
      "warning": "Data is 2 days old"
    },
    "price_sheets": {
      "status": "partial",
      "records": 156,
      "last_sync": "2025-09-15T05:45:00Z",
      "sync_duration_seconds": 120,
      "errors": 3,
      "warning": "3 VNB websites failed to extract"
    }
  },
  "database": {
    "status": "healthy",
    "size_mb": 245.7,
    "connections_active": 5,
    "performance_score": 0.92
  }
}
```

#### Trigger Updates

```http
POST /admin/triggers/update-bdew
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "mode": "incremental",  // "incremental" | "full"
    "validate_data": true,
    "notify_on_completion": true
}

```

**Response:**

```json
{
  "job_id": "bdew-update-20250915-113000",
  "status": "started",
  "estimated_duration_minutes": 5,
  "started_at": "2025-09-15T11:30:00Z",
  "progress_url": "/admin/jobs/bdew-update-20250915-113000"
}
```

```http
POST /admin/triggers/update-bnetza
POST /admin/triggers/rebuild-cache
POST /admin/triggers/extract-prices

```

#### Data Approval

```http
POST /admin/approval/release
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "version": "2025.09.15",
    "approved_by": "admin",
    "notes": "Q4 2025 data verified and validated",
    "components": ["bdew", "bnetza", "prices"],
    "quality_threshold_met": true
}

```

**Response:**

```json
{
  "release_id": "release-2025-09-15-v1",
  "version": "2025.09.15",
  "status": "approved",
  "approved_at": "2025-09-15T12:00:00Z",
  "approved_by": "admin",
  "data_snapshot": {
    "bdew_records": 889,
    "bnetza_records": 234,
    "price_records": 156,
    "quality_score": 0.94
  },
  "public_release_scheduled": "2025-09-15T18:00:00Z"
}
```

## ⚡ Installer API (Port 8080)

### Authentication (OAuth2)

#### OAuth Login

```http
GET /auth/login?provider=google&redirect_uri=https://installer.vnbdigitaler.de/callback

```

Redirects to Google OAuth with state parameter for security.

#### OAuth Callback

```http
GET /auth/callback?code=4/0AY0e-g7...&state=xyz123

```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "1//04tQ...",
  "expires_in": 3600,
  "token_type": "Bearer",
  "user": {
    "id": "installer-123",
    "email": "installer@example.com",
    "name": "Max Mustermann",
    "company": "Elektro Mustermann GmbH",
    "verified": true,
    "roles": ["installer"],
    "permissions": ["create_installations", "view_documents"]
  }
}
```

#### Token Refresh

```http
POST /auth/refresh
Content-Type: application/json

{
    "refresh_token": "1//04tQ..."
}

```

### Company Search

#### Search Grid Operators

```http
GET /api/search/operators?q=stadtwerke&location=münchen&limit=10&offset=0
Authorization: Bearer {access_token}

```

**Response:**

```json
{
  "results": [
    {
      "id": "{grid-operator-uuid}",
      "code": "123456789012",
      "name": "Stadtwerke München GmbH",
      "short_name": "SWM",
      "city": "München",
      "postal_code": "80331",
      "state": "Bayern",
      "phone": "+49 89 2361-0",
      "email": "info@swm.de",
      "website": "https://www.swm.de",
      "roles": ["VNB", "EVU"],
      "service_area": {
        "postal_codes": ["80331", "80333", "80335"],
        "area_km2": 310.7,
        "customers": 45000
      },
      "rollout_info": {
        "quota": 0.15,
        "deadline": "2032-12-31",
        "progress": 0.15,
        "installations_completed": 6750
      },
      "contact": {
        "installer_service": "+49 89 2361-1234",
        "email_installations": "anschluss@swm.de",
        "office_hours": "Mo-Fr 8:00-17:00"
      },
      "distance_km": 2.3
    }
  ],
  "total": 5,
  "search_time_ms": 45,
  "location": {
    "query": "münchen",
    "coordinates": [48.1351, 11.582]
  }
}
```

#### Advanced Search

```http
POST /api/search/operators/advanced
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "filters": {
        "roles": ["VNB"],
        "postal_codes": ["80331", "10117"],
        "has_14a_tariff": true,
        "rollout_progress_min": 0.1
    },
    "location": {
        "coordinates": [48.1351, 11.5820],
        "radius_km": 50
    },
    "sort": {
        "field": "distance",
        "order": "asc"
    },
    "limit": 20
}

```

### Installation Management

#### Create Installation

```http
POST /api/installations
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "customer": {
        "name": "Hans Müller",
        "address": {
            "street": "Musterstraße 123",
            "postal_code": "80331",
            "city": "München",
            "country": "DE"
        },
        "email": "hans.mueller@example.com",
        "phone": "+49 89 1234567"
    },
    "installation": {
        "type": "wallbox",  // "wallbox" | "heat_pump" | "storage" | "pv_system"
        "subtype": "§14a_load_management",
        "power_kw": 11.0,
        "manufacturer": "ABL",
        "model": "eMH1 11kW",
        "planned_date": "2025-10-15",
        "special_requirements": "Existing electrical panel upgrade needed"
    },
    "grid_connection": {
        "grid_operator_id": "example-uuid-here",
        "meter_number": "DE000000000000000000",
        "connection_type": "three_phase",
        "existing_capacity_kw": 15.0
    },
    "installer": {
        "company": "Elektro Mustermann GmbH",
        "technician": "Max Mustermann",
        "license_number": "EI-2023-001234",
        "insurance_valid_until": "2025-12-31"
    }
}

```

**Response:**

```json
{
  "installation_id": "inst-2025-09-15-001",
  "status": "created",
  "created_at": "2025-09-15T12:30:00Z",
  "customer": {
    "name": "Hans Müller",
    "customer_id": "cust-2025-001"
  },
  "grid_operator": {
    "name": "Stadtwerke München GmbH",
    "contact": {
      "email": "anschluss@swm.de",
      "phone": "+49 89 2361-1234"
    }
  },
  "next_steps": [
    {
      "step": "grid_operator_notification",
      "description": "Netzbetreiber wurde automatisch benachrichtigt",
      "status": "completed",
      "completed_at": "2025-09-15T12:30:15Z"
    },
    {
      "step": "customer_confirmation",
      "description": "Kunde muss Installation bestätigen",
      "status": "pending",
      "due_date": "2025-09-17T23:59:59Z"
    },
    {
      "step": "grid_operator_approval",
      "description": "Netzbetreiber-Genehmigung erforderlich",
      "status": "waiting",
      "estimated_duration_days": 14
    }
  ],
  "documents": {
    "generated": [
      {
        "type": "installation_request",
        "name": "Anmeldung_Ladeeinrichtung_inst-2025-09-15-001.pdf",
        "download_url": "/api/installations/inst-2025-09-15-001/documents/installation_request"
      }
    ],
    "required_uploads": [
      {
        "type": "electrical_certificate",
        "description": "Elektrotechnische Bescheinigung",
        "due_date": "2025-09-22T23:59:59Z"
      }
    ]
  }
}
```

#### Installation Status

```http
GET /api/installations/{installation_id}
Authorization: Bearer {access_token}

```

**Response:**

```json
{
  "installation_id": "inst-2025-09-15-001",
  "status": "pending_approval",
  "created_at": "2025-09-15T12:30:00Z",
  "updated_at": "2025-09-17T14:20:00Z",
  "customer": {
    "name": "Hans Müller",
    "email": "hans.mueller@example.com"
  },
  "installation": {
    "type": "wallbox",
    "power_kw": 11.0,
    "planned_date": "2025-10-15",
    "actual_date": null
  },
  "grid_operator": {
    "name": "Stadtwerke München GmbH",
    "response_time_target_days": 14,
    "response_received": false
  },
  "timeline": [
    {
      "timestamp": "2025-09-15T12:30:00Z",
      "event": "installation_created",
      "description": "Installation request created",
      "actor": "installer"
    },
    {
      "timestamp": "2025-09-15T12:30:15Z",
      "event": "grid_operator_notified",
      "description": "Automatic notification sent to SWM",
      "actor": "system"
    },
    {
      "timestamp": "2025-09-17T14:20:00Z",
      "event": "customer_confirmed",
      "description": "Customer confirmed installation details",
      "actor": "customer"
    }
  ],
  "documents": {
    "uploaded": [
      {
        "type": "electrical_certificate",
        "filename": "Bescheinigung_Müller.pdf",
        "uploaded_at": "2025-09-17T14:20:00Z",
        "verified": true
      }
    ],
    "pending": [],
    "generated": [
      {
        "type": "installation_request",
        "filename": "Anmeldung_Ladeeinrichtung_inst-2025-09-15-001.pdf",
        "download_url": "/api/installations/inst-2025-09-15-001/documents/installation_request"
      }
    ]
  },
  "notifications": {
    "email_sent": true,
    "sms_sent": false,
    "last_notification": "2025-09-17T14:25:00Z"
  }
}
```

#### Bulk Installation Status

```http
GET /api/installations?installer_id=installer-123&status=pending_approval&limit=50
Authorization: Bearer {access_token}

```

### Document Management

#### TAB Documents

```http
GET /api/documents/tab?grid_operator_id={grid-operator-uuid}
Authorization: Bearer {access_token}

```

**Response:**

```json
{
  "grid_operator": {
    "name": "Stadtwerke München GmbH",
    "website": "https://www.swm.de"
  },
  "documents": [
    {
      "type": "tab",
      "title": "Technische Anschlussbedingungen Niederspannung",
      "version": "2024-01-15",
      "url": "https://www.swm.de/dam/.../TAB_NS_2024.pdf",
      "file_size_mb": 2.3,
      "last_updated": "2024-01-15T00:00:00Z",
      "language": "de",
      "cached": true,
      "r2_backup_url": "https://r2.vnbdigitaler.de/documents/tab-documents/123456789012/TAB_NS_2024.pdf",
      "download_url": "/api/documents/tab/550e8400.../tab_ns_2024.pdf",
      "integrity_verified": true,
      "document_hash": "sha256:b2c3d4e5f6..."
    },
    {
      "type": "installation_form",
      "title": "Anmeldung Ladeeinrichtung",
      "version": "2024-06-01",
      "url": "https://www.swm.de/forms/ladeeinrichtung.pdf",
      "file_size_mb": 0.8,
      "last_updated": "2024-06-01T00:00:00Z",
      "cached": true,
      "prefillable": true,
      "r2_backup_url": "https://r2.vnbdigitaler.de/documents/forms/123456789012/installation_form.pdf",
      "download_url": "/api/documents/forms/550e8400.../installation_form.pdf",
      "integrity_verified": true
    }
  ],
  "metadata": {
    "last_scraped": "2025-09-15T06:00:00Z",
    "documents_found": 12,
    "documents_accessible": 10,
    "scrape_success_rate": 0.83,
    "r2_backup_status": "up_to_date"
  }
}
```

#### Secure Document Access

```http
GET /api/documents/{document_id}/secure-download
Authorization: Bearer {access_token}
```

**Response:** Pre-signed URL for secure access to Cloudflare R2:

```json
{
  "document_id": "{document-uuid}",
  "secure_url": "https://r2.vnbdigitaler.de/documents/tab-documents/123456789012/TAB_NS_2024.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...",
  "expires_at": "2025-09-15T17:30:00Z",
  "valid_for_seconds": 3600,
  "download_instructions": {
    "method": "GET",
    "headers": {
      "User-Agent": "VNB-Digitaler-Client/1.0"
    }
  }
}
```

#### Upload Installation Document

```http
POST /api/installations/{installation_id}/documents
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file: {PDF/Image file}
document_type: "electrical_certificate"
description: "Elektrotechnische Bescheinigung für Ladeeinrichtung"
```

**Response:**

```json
{
  "document_id": "{uploaded-document-uuid}",
  "installation_id": "inst-2025-09-15-001",
  "document_type": "electrical_certificate",
  "filename": "Bescheinigung_Müller_2025-09-15.pdf",
  "file_size_bytes": 1234567,
  "uploaded_at": "2025-09-15T16:45:00Z",
  "r2_object_key": "documents/installations/2025/09/inst-2025-09-15-001/electrical_certificate.pdf",
  "document_hash": "sha256:c3d4e5f6...",
  "status": "uploaded",
  "processing": {
    "ocr_scheduled": true,
    "validation_pending": true,
    "estimated_processing_time_minutes": 5
  },
  "access": {
    "installer_viewable": true,
    "customer_viewable": false,
    "grid_operator_shareable": true
  }
}
```

#### Form Generation

```http
POST /api/documents/generate/installation-form
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "grid_operator_id": "{grid-operator-uuid}",
    "installation_data": {
        "customer": {
            "name": "Hans Müller",
            "address": "Musterstraße 123, 80331 München"
        },
        "installation": {
            "type": "wallbox",
            "power_kw": 11.0,
            "manufacturer": "ABL"
        }
    },
    "format": "pdf"  // "pdf" | "docx" | "xml"
}

```

### Reporting

#### Monthly Report

```http
GET /api/reports/monthly?year=2025&month=9&installer_id=installer-123
Authorization: Bearer {access_token}

```

**Response:**

```json
{
  "period": {
    "year": 2025,
    "month": 9,
    "month_name": "September"
  },
  "installer": {
    "company": "Elektro Mustermann GmbH",
    "installer_id": "installer-123"
  },
  "summary": {
    "total_installations": 23,
    "completed_installations": 18,
    "pending_installations": 5,
    "cancelled_installations": 0,
    "revenue_estimate_eur": 34500
  },
  "by_type": {
    "wallbox": {
      "count": 15,
      "avg_power_kw": 11.2,
      "completion_rate": 0.87
    },
    "heat_pump": {
      "count": 8,
      "avg_power_kw": 8.5,
      "completion_rate": 0.75
    }
  },
  "by_grid_operator": {
    "Stadtwerke München": {
      "installations": 8,
      "avg_approval_days": 12,
      "success_rate": 0.9
    },
    "Bayernwerk": {
      "installations": 10,
      "avg_approval_days": 16,
      "success_rate": 0.8
    }
  },
  "performance_metrics": {
    "avg_processing_time_days": 21,
    "customer_satisfaction": 4.7,
    "repeat_customer_rate": 0.35
  },
  "upcoming_deadlines": [
    {
      "installation_id": "inst-2025-09-20-003",
      "customer": "Schmidt",
      "deadline": "2025-10-05T23:59:59Z",
      "type": "grid_operator_response_due"
    }
  ]
}
```

## 🌐 Public API (Streamlit Integration)

### Company Data

#### Public Company Search

```python
# Available through Streamlit app internal API
# No authentication required - read-only access

import streamlit as st
import requests

def search_companies(query: str, limit: int = 10):
    """Search for companies in public database"""
    # Internal Streamlit API call
    response = requests.get(
        f"{INTERNAL_API_BASE}/companies/search",
        params={"q": query, "limit": limit, "public": True}
    )
    return response.json()

# Usage in Streamlit
companies = search_companies("stadtwerke münchen")

```

#### Company Details

```python
def get_company_details(company_id: str):
    """Get public company information"""
    response = requests.get(
        f"{INTERNAL_API_BASE}/companies/{company_id}/public"
    )
    return response.json()

# Example response structure:
{
    "id": "{grid-operator-uuid}",
    "name": "Stadtwerke München GmbH",
    "city": "München",
    "postal_code": "80331",
    "roles": ["VNB", "EVU"],
    "service_area": {
        "postal_codes": ["80331", "80333", "80335"],
        "population": 150000
    },
    "contact": {
        "website": "https://www.swm.de",
        "phone": "+49 89 2361-0",
        "email": "info@swm.de"
    },
    "rollout_info": {
        "quota": 0.15,
        "progress": 0.15,
        "last_updated": "2025-09-15T00:00:00Z"
    },
    "pricing": {
        "has_14a_tariff": true,
        "wallbox_reduction_percent": 12.5,
        "heat_pump_reduction_percent": 15.0,
        "last_updated": "2025-08-01T00:00:00Z"
    }
}

```

### Price Comparison

```python
def get_price_comparison(postal_code: str, installation_type: str):
    """Get price comparison for postal code area"""
    response = requests.get(
        f"{INTERNAL_API_BASE}/prices/compare",
        params={
            "postal_code": postal_code,
            "type": installation_type,
            "include_alternatives": True
        }
    )
    return response.json()

# Example for wallbox comparison:
comparison = get_price_comparison("80331", "wallbox")

# Response structure:
{
    "postal_code": "80331",
    "installation_type": "wallbox",
    "primary_vnb": {
        "name": "Stadtwerke München GmbH",
        "base_price_ct_kwh": 28.5,
        "reduced_price_ct_kwh": 24.9,
        "reduction_percent": 12.6,
        "annual_savings_eur": 180
    },
    "alternatives": [],
    "market_average": {
        "base_price_ct_kwh": 29.2,
        "reduction_percent": 11.8,
        "annual_savings_eur": 165
    },
    "calculation_basis": {
        "annual_consumption_kwh": 3000,
        "usage_pattern": "primarily_night_charging"
    }
}

```

### Geographic Data API

```python
def get_territory_by_postal(postal_code: str):
    """Get VNB territory information by postal code"""
    response = requests.get(
        f"{INTERNAL_API_BASE}/territories/postal/{postal_code}"
    )
    return response.json()

def get_territory_geojson(bounds: dict = None):
    """Get GeoJSON data for map visualization"""
    params = {}
    if bounds:
        params.update(bounds)

    response = requests.get(
        f"{INTERNAL_API_BASE}/territories/geojson",
        params=params
    )
    return response.json()

```

## 📊 GraphQL Schema (Future Implementation)

### Schema Definition

```graphql
scalar DateTime
scalar JSON

type Company {
  id: ID!
  code: String!
  name: String!
  shortName: String
  city: String
  postalCode: String
  state: String
  country: String!

  # Contact Information
  website: String
  email: String
  phone: String

  # Business Information
  roles: [CompanyRole!]!
  status: CompanyStatus!
  registrationDate: DateTime

  # Geographic Data
  serviceAreas: [ServiceTerritory!]!
  coordinates: Coordinates

  # Smart Meter Rollout (VNB only)
  rolloutInfo: RolloutInfo

  # Pricing Information
  priceSheets(type: PriceSheetType): [PriceSheet!]!
  currentPricing: PricingInfo

  # Relationships
  parentCompany: Company
  subsidiaries: [Company!]!

  # Metadata
  createdAt: DateTime!
  updatedAt: DateTime!
  dataQuality: DataQualityScore!
}

type CompanyRole {
  type: RoleType!
  active: Boolean!
  validFrom: DateTime
  validUntil: DateTime
  details: JSON
}

enum RoleType {
  VNB # Verteilnetzbetreiber
  UNB # Übertragungsnetzbetreiber
  EVU # Energieversorgungsunternehmen
  MSB # Messstellenbetreiber
  LNG # Fernleitungsnetzbetreiber
  RLM # Regelleistungsmarkt
}

enum CompanyStatus {
  ACTIVE
  INACTIVE
  MERGED
  DISSOLVED
}

type ServiceTerritory {
  id: ID!
  name: String!
  postalCodes: [String!]!
  geometry: GeoJSON!
  population: Int
  areaKm2: Float
  customerCount: Int
}

type RolloutInfo {
  quota: Float! # 0.0 - 1.0
  deadline: DateTime!
  progress: Float! # 0.0 - 1.0
  installationsCompleted: Int!
  installationsTarget: Int!
  lastUpdated: DateTime!
}

type PriceSheet {
  id: ID!
  type: PriceSheetType!
  version: String!
  validFrom: DateTime!
  validUntil: DateTime
  url: String!
  extractedData: JSON
  lastExtracted: DateTime
}

enum PriceSheetType {
  NETWORK_CHARGES
  SECTION_14A
  METERING_CHARGES
  CONNECTION_CHARGES
}

type PricingInfo {
  basePrice: MonetaryAmount
  section14aReductions: [Section14aReduction!]!
  lastUpdated: DateTime!
}

type Section14aReduction {
  applicationType: ApplicationType!
  reductionPercent: Float!
  reductionAbsolute: MonetaryAmount
  conditions: [String!]!
}

enum ApplicationType {
  WALLBOX
  HEAT_PUMP
  ENERGY_STORAGE
  PV_SYSTEM
  NIGHT_STORAGE_HEATER
}

type MonetaryAmount {
  amount: Float!
  currency: String!
  unit: PriceUnit!
}

enum PriceUnit {
  CT_PER_KWH # Cent per kWh
  EUR_PER_YEAR # Euro per year
  EUR_PER_MONTH # Euro per month
  EUR_ONCE # One-time fee
}

type Coordinates {
  latitude: Float!
  longitude: Float!
}

type DataQualityScore {
  overall: Float! # 0.0 - 1.0
  completeness: Float!
  accuracy: Float!
  consistency: Float!
  timeliness: Float!
  lastAssessed: DateTime!
}

# Query Types
type Query {
  # Company Queries
  companies(filter: CompanyFilter, sort: CompanySort, pagination: Pagination): CompanyConnection!

  company(id: ID!): Company
  companyByCode(code: String!): Company

  # Search
  searchCompanies(
    query: String!
    location: LocationInput
    filters: CompanyFilter
    limit: Int = 10
  ): [Company!]!

  # Geographic Queries
  vnbByPostalCode(postalCode: String!): [Company!]!
  serviceTerritory(postalCode: String!): ServiceTerritory
  serviceTerritories(bounds: BoundsInput): [ServiceTerritory!]!

  # Price Comparison
  priceComparison(input: PriceComparisonInput!): PriceComparison!
  marketAnalysis(input: MarketAnalysisInput!): MarketAnalysis!

  # Statistics
  marketStatistics: MarketStatistics!
  rolloutProgress: RolloutProgress!
}

# Mutation Types (Admin/Installer only)
type Mutation {
  # Installer Operations
  registerInstaller(input: InstallerRegistrationInput!): InstallerResult!
  createInstallation(input: InstallationInput!): Installation!
  updateInstallation(id: ID!, input: InstallationUpdateInput!): Installation!

  # Admin Operations (restricted)
  createCompany(input: CompanyInput!): Company!
  updateCompany(id: ID!, input: CompanyUpdateInput!): Company!
  mergeCompanies(sourceId: ID!, targetId: ID!): Company!

  # Data Management
  triggerDataSync(source: DataSource!): SyncJob!
  approveDataRelease(input: DataReleaseInput!): DataRelease!
}

# Subscription Types (real-time updates)
type Subscription {
  # Installation Status Updates
  installationUpdates(installerId: ID!): Installation!

  # Data Pipeline Updates
  syncProgress(jobId: ID!): SyncProgress!

  # Market Data Updates
  priceUpdates(vnbIds: [ID!]!): PriceUpdate!
}

# Input Types
input CompanyFilter {
  roles: [RoleType!]
  status: [CompanyStatus!]
  hasSection14aTariff: Boolean
  rolloutProgressMin: Float
  rolloutProgressMax: Float
  serviceArea: LocationInput
}

input LocationInput {
  postalCode: String
  city: String
  coordinates: CoordinatesInput
  radiusKm: Float
}

input CoordinatesInput {
  latitude: Float!
  longitude: Float!
}

input PriceComparisonInput {
  postalCode: String!
  applicationType: ApplicationType!
  annualConsumptionKwh: Int
  installationPowerKw: Float
}

# Connection Types (GraphQL Relay)
type CompanyConnection {
  edges: [CompanyEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type CompanyEdge {
  node: Company!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}
```

### Example Queries

#### Complex Company Search

```graphql
query SearchVNBsWithPricing($location: LocationInput!, $applicationType: ApplicationType!) {
  searchCompanies(
    query: "stadtwerke"
    location: $location
    filters: { roles: [VNB], hasSection14aTariff: true }
  ) {
    id
    name
    city
    roles {
      type
      active
    }
    serviceAreas {
      postalCodes
      population
    }
    currentPricing {
      basePrice {
        amount
        currency
        unit
      }
      section14aReductions(applicationType: $applicationType) {
        reductionPercent
        conditions
      }
    }
    rolloutInfo {
      progress
      quota
      installationsCompleted
    }
    dataQuality {
      overall
      lastAssessed
    }
  }
}
```

#### Market Analysis Query

```graphql
query MarketAnalysis($bounds: BoundsInput!) {
  serviceTerritories(bounds: $bounds) {
    id
    name
    postalCodes
    geometry
    population
    vnb: companies(filter: { roles: [VNB] }) {
      name
      currentPricing {
        section14aReductions {
          applicationType
          reductionPercent
        }
      }
      rolloutInfo {
        progress
        quota
      }
    }
  }

  marketStatistics {
    totalVnbs
    averageSection14aReduction
    rolloutProgressAverage
    priceRanges {
      applicationType
      minReductionPercent
      maxReductionPercent
      avgReductionPercent
    }
  }
}
```

## 🔒 Authentication & Authorization

### JWT Token Structure

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "installer-123",
    "email": "installer@example.com",
    "roles": ["installer"],
    "permissions": ["read:companies", "create:installations", "read:documents"],
    "company": "Elektro Mustermann GmbH",
    "iat": 1726401000,
    "exp": 1726404600,
    "iss": "vnbdigitaler-api",
    "aud": ["installer-api", "admin-api"]
  }
}
```

### Permission System

| Role          | Permissions                                                                 |
| ------------- | --------------------------------------------------------------------------- |
| **Public**    | `read:companies:public`, `read:prices:public`, `read:territories`           |
| **Installer** | Public + `create:installations`, `read:documents`, `read:companies:details` |
| **Admin**     | All + `write:companies`, `delete:companies`, `admin:data-control`           |

---

_Diese API-Dokumentation wird kontinuierlich erweitert und aktualisiert, um alle Features und Endpoints vollständig abzudecken._
