# DevContainer Configuration

This directory contains the development container configuration for the VNBdigitaler project.

## Files

- `devcontainer.json` - Main DevContainer configuration
- `postCreateCommand.sh` - Script executed after container creation
- `updateContentCommand.sh` - Script executed when container content is updated
- `features/` - Local DevContainer features

## Features

### uv Python Package Manager

A custom DevContainer feature that installs [uv](https://docs.astral.sh/uv/), the extremely fast Python package manager.

**Location:** `./features/uv/`

**Configuration in devcontainer.json:**

```json
{
  "features": {
    "./features/uv": {
      "version": "latest",
      "installPath": "/usr/local/bin",
      "enableShellCompletion": true
    }
  }
}
```

## Development Environment

The DevContainer provides:

- ✅ Python 3.11 on Debian Bullseye
- ✅ uv package manager with shell completion
- ✅ VS Code Python extensions (Pylance, Python)
- ✅ Streamlit application auto-start
- ✅ Git configuration
- ✅ PYTHONPATH configuration for src/ directory

## Usage

1. **Open in DevContainer**: VS Code will automatically detect the configuration
2. **Rebuild Container**: Use "Rebuild Container" to apply changes
3. **Test uv Feature**: Run `.devcontainer/features/uv/test.sh` to verify installation

## Scripts

### postCreateCommand.sh

- Configures Git settings
- Installs Python dependencies with `uv sync`
- Sets up Streamlit configuration

### updateContentCommand.sh

- Updates system packages if `packages.txt` exists
- Syncs Python dependencies

## Ports

- **8501**: Streamlit application (auto-forwarded with preview)

## Environment Variables

- `PYTHONPATH`: Set to `${workspaceFolder}/src` for proper import resolution

## File Structure

```
.devcontainer/
├── devcontainer.json           # Main configuration
├── postCreateCommand.sh        # Post-creation setup
├── updateContentCommand.sh     # Update script
├── features/                   # Local features
│   ├── .gitkeep               # Git tracking
│   └── uv/                    # uv feature
│       ├── devcontainer-feature.json
│       ├── install.sh
│       ├── test.sh
│       └── README.md
└── README.md                  # This file
```

## Customization

To modify the development environment:

1. **Add system packages**: Create `packages.txt` in project root
2. **Change uv version**: Update `version` in `devcontainer.json`
3. **Add VS Code extensions**: Update `extensions` array
4. **Modify Python path**: Update `PYTHONPATH` in settings

## Testing

Test the complete setup:

```bash
# Test uv installation
.devcontainer/features/uv/test.sh

# Test Python environment
uv run python -c "import sys; print(sys.path)"

# Test Streamlit
uv run streamlit run streamlit_app.py
```
