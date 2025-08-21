# VNBdigitaler WebUI

A comprehensive FastAPI-based web administration interface for managing German electricity grid operators (VNB) data.

## Features

### Dashboard

- Overview statistics showing total companies, verified companies, and rollout coverage
- Quick action buttons for common tasks
- Recent activity feed

### Company Management

- **List View**: Paginated table with all companies including filtering and search
- **Edit Interface**: Update company details including rollout information and manual verification
- **Map Visualization**: Interactive maps showing service areas using Leaflet.js and OpenStreetMap
- **Dropdown Search**: Quick company selection with live search functionality

### Technical Stack

- **Backend**: FastAPI with async/await support
- **Database**: SQLAlchemy with async PostgreSQL support
- **Frontend**: Bootstrap 5 for responsive design
- **Maps**: Leaflet.js for interactive GeoJSON visualization
- **Templates**: Jinja2 server-side rendering

## Installation & Setup

1. **Install Dependencies**:

   ```bash
   uv sync
   ```

2. **Configure Environment**:
   - Copy `.env.example` to `.env`
   - Set database connection string and other configuration

3. **Run the Application**:

   ```bash
   uv run python -m uvicorn webui.main:app --reload --host 0.0.0.0 --port 8080
   ```

4. **Access the WebUI**:
   - Open browser to: <http://localhost:8080>
   - Dashboard: <http://localhost:8080/>
   - Companies: <http://localhost:8080/companies/>
   - Company Search: <http://localhost:8080/companies/dropdown>

## API Endpoints

### Web Pages (HTML)

- `GET /` - Dashboard
- `GET /companies/` - Companies list with pagination and filters
- `GET /companies/edit/{id}` - Company edit form
- `GET /companies/map/{id}` - Company service area map
- `GET /companies/dropdown` - Company selection interface

### API Endpoints (JSON)

- `GET /health` - Health check
- `GET /companies/api/list` - Get companies list with pagination
- `GET /companies/api/{id}` - Get specific company details
- `PUT /companies/api/{id}` - Update company information
- `GET /companies/api/dropdown` - Search companies for dropdown
- `GET /companies/api/{id}/geojson` - Get company service area GeoJSON

## Directory Structure

```
webui/
├── main.py                    # FastAPI application entry point
├── routers/                   # API route handlers
│   ├── __init__.py
│   ├── dashboard.py          # Dashboard functionality
│   └── companies.py          # Company management API
├── templates/                # Jinja2 HTML templates
│   ├── base.html             # Base template with navigation
│   ├── dashboard.html        # Dashboard with statistics
│   ├── companies_list.html   # Companies table with pagination
│   ├── company_edit.html     # Company editing form
│   ├── company_map.html      # Interactive map visualization
│   └── company_dropdown.html # Company search/selection
└── static/                   # Static assets
    ├── css/
    │   └── style.css         # Custom CSS styles
    └── js/
        └── app.js            # JavaScript utilities
```

## Key Features

### Company Management Features

- **CRUD Operations**: Complete Create, Read, Update functionality for companies
- **Data Validation**: Pydantic models ensure data integrity
- **Async Database**: High-performance async database operations
- **Filtering & Search**: Advanced filtering by multiple criteria

### Map Visualization

- **Interactive Maps**: Leaflet.js integration for service area visualization
- **GeoJSON Support**: Native support for geographic data
- **Layer Controls**: Switch between different map layers
- **Export Functions**: Download service area data

### User Interface

- **Responsive Design**: Bootstrap 5 ensures mobile compatibility
- **Modern UX**: Clean, professional interface with smooth interactions
- **Accessibility**: ARIA labels and keyboard navigation support
- **Performance**: Optimized loading and client-side caching

### API Design

- **RESTful**: Standard REST API patterns
- **Async Support**: High-performance async/await throughout
- **Error Handling**: Comprehensive error responses
- **Documentation**: Auto-generated OpenAPI/Swagger docs at `/docs`

## Configuration

The WebUI uses the same configuration system as the main application:

- **Database**: Configured via `DATABASE_URL` environment variable
- **Settings**: Uses `src.config.get_settings()` for centralized configuration
- **Environment**: Supports development and production environments

## Development

### Adding New Features

1. Create new router in `webui/routers/`
2. Add HTML templates in `webui/templates/`
3. Include router in `webui/main.py`
4. Add necessary static assets

### Database Models

- Uses the same SQLAlchemy models from `src.models`
- Async session management via dependency injection
- Automatic transaction handling with rollback on errors

### Testing

Run the application locally and test all functionality:

- Dashboard statistics
- Company list pagination and filtering
- Company editing and updates
- Map visualization with GeoJSON data
- Dropdown search functionality

## Production Deployment

For production deployment:

1. **Environment Variables**:

   ```bash
   export DATABASE_URL="postgresql+asyncpg://user:pass@host:port/db"  # pragma: allowlist secret
   export ENVIRONMENT="production"
   ```

2. **ASGI Server**:

   ```bash
   uvicorn webui.main:app --host 0.0.0.0 --port 8080 --workers 4
   ```

3. **Reverse Proxy**: Configure nginx or similar for static file serving and SSL termination

4. **Process Management**: Use systemd, supervisor, or container orchestration

## License

Same license as the main VNBdigitaler project.
