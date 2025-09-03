# DevContainer Configuration

This directory contains the development container configuration for the VNBdigitaler project.

## Files

- `devcontainer.json` - Main DevContainer configuration
- `postCreateCommand.sh` - Script executed after container creation
- `updateContentCommand.sh` - Script executed when container content is updated

## Features

This DevContainer uses external features from [the78mole/devcontainer-features](https://github.com/the78mole/devcontainer-features):

### uv Python Package Manager

**Feature:** `ghcr.io/the78mole/devcontainer-features/uv:1`

Installs [uv](https://docs.astral.sh/uv/), the extremely fast Python package manager written in Rust.

**Configuration:**

```json
"ghcr.io/the78mole/devcontainer-features/uv:1": {
  "version": "latest"
}
```

### PostgreSQL Database

**Feature:** `ghcr.io/the78mole/devcontainer-features/postgresql:1`

Installs and configures PostgreSQL 16 with development-friendly settings.

**Configuration:**

```json
"ghcr.io/the78mole/devcontainer-features/postgresql:1": {
  "version": "16"
}
```

## Development Environment

The DevContainer provides:

- ✅ Python 3.11 on Debian Bullseye
- ✅ uv package manager with shell completion
- ✅ PostgreSQL 16 database server
- ✅ VS Code Python and PostgreSQL extensions
- ✅ Streamlit application auto-start
- ✅ Git configuration
- ✅ PYTHONPATH configuration for src/ directory

## Usage

1. **Open in DevContainer**: VS Code will automatically detect the configuration
2. **Rebuild Container**: Use "Rebuild Container" to apply changes
3. **Start PostgreSQL**: Run `sudo /usr/local/share/pq-init.sh` (done automatically)
4. **Connect to database**: `psql -U postgres` or use VS Code PostgreSQL extension

## Scripts

### postCreateCommand.sh

- Configures Git settings
- Initializes PostgreSQL database
- Installs Python dependencies with `uv sync`
- Sets up Streamlit configuration

### updateContentCommand.sh

- Updates system packages if `packages.txt` exists
- Syncs Python dependencies

## Ports

- **8501**: Streamlit application (auto-forwarded with preview)
- **5432**: PostgreSQL database (forwarded, no auto-open)

## Environment Variables

- `PYTHONPATH`: Set to `${workspaceFolder}/src` for proper import resolution
- `DATABASE_URL`: PostgreSQL connection string (`postgresql://postgres@localhost:5432/postgres`)

## Database Quick Start

After container setup:

```bash
# Start PostgreSQL (done automatically in postCreateCommand)
sudo /usr/local/share/pq-init.sh

# Connect to database
psql -U postgres

# Create a database for your project
CREATE DATABASE vnbdigitaler;

# Use uv to add database dependencies
uv add psycopg2-binary sqlalchemy
```

## File Structure

```
.devcontainer/
├── devcontainer.json           # Main configuration
├── postCreateCommand.sh        # Post-creation setup
├── updateContentCommand.sh     # Update script
├── Dockerfile.backup          # Backup of previous custom setup
└── README.md                  # This file
```

## Customization

To modify the development environment:

1. **Add system packages**: Create `packages.txt` in project root
2. **Change uv version**: Update `version` in feature configuration
3. **Change PostgreSQL version**: Update `version` in postgresql feature
4. **Add VS Code extensions**: Update `extensions` array
5. **Modify Python path**: Update `PYTHONPATH` in settings

## Testing

Test the complete setup:

```bash
# Test uv installation
uv --version

# Test Python environment
uv run python -c "import sys; print(sys.path)"

# Test PostgreSQL connection
psql -U postgres -c "SELECT version();"

# Test Streamlit, currently not in Scope
#uv run streamlit run streamlit_app.py
```
