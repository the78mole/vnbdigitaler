# uv DevContainer Feature

This DevContainer feature installs [uv](https://docs.astral.sh/uv/), the extremely fast Python package and project manager written in Rust.

## What it does

- Installs uv binary to the specified location
- Configures shell completion for bash and zsh
- Ensures uv is available in PATH
- Supports specific version installation or latest version

## Usage

Add this feature to your `devcontainer.json`:

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

## Options

| Option                  | Type    | Default            | Description                                                                 |
| ----------------------- | ------- | ------------------ | --------------------------------------------------------------------------- |
| `version`               | string  | `"latest"`         | Version of uv to install. Can be "latest" or specific version like "0.8.11" |
| `installPath`           | string  | `"/usr/local/bin"` | Installation path for uv binary                                             |
| `enableShellCompletion` | boolean | `true`             | Enable shell completion for bash and zsh                                    |

## Examples

### Latest version with default settings

```json
{
  "features": {
    "./features/uv": {}
  }
}
```

### Specific version

```json
{
  "features": {
    "./features/uv": {
      "version": "0.8.11"
    }
  }
}
```

### Custom installation path

```json
{
  "features": {
    "./features/uv": {
      "version": "latest",
      "installPath": "/opt/uv/bin",
      "enableShellCompletion": true
    }
  }
}
```

## What gets installed

- uv binary at the specified installation path
- Shell completion files for bash and zsh (if enabled)
- Symlink to `/usr/local/bin/uv` if installing to custom location
- PATH configuration in shell profiles

## After installation

Once installed, you can use uv commands:

```bash
# Initialize a new project
uv init my-project

# Add dependencies
uv add requests fastapi

# Run scripts with managed environment
uv run python app.py

# Sync dependencies from lockfile
uv sync

# Show installed packages
uv list
```

## Compatibility

- ✅ Linux (x86_64, aarch64)
- ✅ macOS (x86_64, aarch64)
- ✅ Debian/Ubuntu based containers
- ✅ Alpine Linux containers

## Links

- [uv Documentation](https://docs.astral.sh/uv/)
- [uv GitHub Repository](https://github.com/astral-sh/uv)
- [DevContainer Features Documentation](https://containers.dev/features)
