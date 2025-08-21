# Development Scripts

This directory contains utility scripts for gracenote2epg development and maintenance.

> **📖 See also**: [Development Guide](../docs/development.md) for development overview and workflow concepts.
> 
> **💡 Quick start**: Most developers should use `make` commands (see [Makefile Integration](#makefile-integration) below) rather than calling scripts directly.

## Overview

The development scripts provide the foundation for the project's automated workflow:

- **Primary interface**: `Makefile` at project root (recommended for most users)
- **Direct usage**: Individual scripts for advanced use cases and CI/CD integration
- **Complete automation**: From code quality to distribution testing

## Available Scripts

### `dev-helper.bash`
**Development workflow assistant**

Provides command-line shortcuts for common development tasks and workflow automation.

#### Usage
```bash
# Development task commands
./scripts/dev-helper.bash <command>

# Available commands:
./scripts/dev-helper.bash clean        # Clean all build artifacts and caches
./scripts/dev-helper.bash autofix     # Auto-fix imports and common issues with autoflake
./scripts/dev-helper.bash format      # Format code with black
./scripts/dev-helper.bash lint        # Run linting with flake8
./scripts/dev-helper.bash test-basic  # Quick functionality test
./scripts/dev-helper.bash test-full   # Full distribution test
./scripts/dev-helper.bash install-dev # Install in development mode
./scripts/dev-helper.bash check-deps  # Check and install development dependencies
./scripts/dev-helper.bash show-dist   # Show current distribution files
./scripts/dev-helper.bash help        # Show help
```

#### What the script does
1. **Environment management** - Cleans Python caches and build artifacts
2. **Auto-fixing** - Uses autoflake to remove unused imports and variables automatically
3. **Code quality** - Runs Black formatter and flake8 linting with project-specific configuration
4. **Development setup** - Installs package in editable mode with dev dependencies
5. **Dependency management** - Detects system vs pip packages, warns about conflicts
6. **Distribution inspection** - Shows built packages and their contents

#### Safe auto-fixing
The `autofix` command safely removes:
- Unused imports (F401 errors)
- Unused variables (F841 errors)  
- Trailing whitespace (W293 errors)
- Some bare except statements (E722 errors)

**Note:** F541 (f-string without placeholders) is NOT auto-fixed to avoid breaking valid f-strings.

### `test-distribution.bash`
**Main Python distribution testing script**

Tests building, installation, and functionality of both wheel and source packages.

#### Usage
```bash
# Full test (recommended)
./scripts/test-distribution.bash

# Basic test (basic functionality only)
./scripts/test-distribution.bash --basic

# Test wheel only
./scripts/test-distribution.bash --wheel-only

# Test source distribution only
./scripts/test-distribution.bash --source-only

# Clean builds only (no testing)
./scripts/test-distribution.bash --clean-only
```

#### What the script does
1. **Dependency check** - Ensures python3, pip, and build are available
2. **Cleanup** - Removes old builds and test environments
3. **Build** - Generates wheel (.whl) and source (.tar.gz) distributions
4. **Content verification** - Verifies essential files are included (especially locales)
5. **Installation test** - Installs in clean virtual environments
6. **Functionality test** - Verifies commands work correctly
7. **Translation test** - Verifies translation system is operational

#### Special locale validation
The script specifically checks that translation `.po` files are included in distributions, which was the main issue identified.

#### Colored output
The script uses colors for better readability:
- 🔵 **BLUE**: General information
- 🟢 **GREEN**: Success
- 🟡 **YELLOW**: Warnings
- 🔴 **RED**: Errors

Use `--no-color` to disable colors.

## Makefile Integration

**Recommended approach**: Use `Makefile` targets for most development tasks:

### Make targets
```bash
# Quick development tasks
make clean               # Clean all artifacts
make autofix             # Auto-fix imports and common issues
make format              # Format code with black  
make lint                # Run linting
make test-basic          # Quick test
make test-full           # Full test (alias: make test)

# Build and install
make build               # Build distributions
make install-dev         # Development installation
make check-deps          # Check dependencies
make show-dist           # Show distribution files

# Complete workflow
make all                 # Run clean, autofix, format, lint, and test-full
```

The Makefile automatically handles script permissions and provides a unified interface for all development tasks.

### When to use scripts directly

Use the scripts directly when you need:
- **Advanced options** not exposed through Makefile
- **CI/CD integration** with specific parameters
- **Debugging** script behavior
- **Custom workflows** beyond the standard make targets

## Recommended development workflow

### Before committing changes
```bash
# Option 1: Using individual dev-helper commands
./scripts/dev-helper.bash format
./scripts/dev-helper.bash lint  
./scripts/test-distribution.bash --basic

# Option 2: Using Makefile shortcuts
make format lint test-basic

# Option 3: Complete validation
make all
```

### Before creating a release
```bash
# Full validation with all features
./scripts/test-distribution.bash --full
# or
make test-full

# If everything passes, distributions are ready for publication
ls -la dist/
```

### Quick development cycle
```bash
# Clean, format, and quick test
make clean format test-basic

# Or using scripts directly
./scripts/dev-helper.bash clean
./scripts/dev-helper.bash format
./scripts/test-distribution.bash --basic
```

### To debug packaging issues
```bash
# Clean and see build errors
./scripts/test-distribution.bash --clean-only
python3 -m build --verbose

# Inspect package contents
./scripts/test-distribution.bash --wheel-only
python3 -m zipfile -l dist/*.whl | grep locales
```

## Test environments

The script creates temporary virtual environments:
- `~/test_env_wheel` - For testing wheel installation
- `~/test_env_source` - For testing source installation

These environments are automatically removed and recreated on each run.

## Debugging

### Detailed logs
The script shows detailed logs for each step. If something fails, look at the failed section.

### Manual testing and debugging
For more thorough testing and debugging:
```bash
# Create and activate test environment
source ~/test_env_wheel/bin/activate

# Manual functionality testing
gracenote2epg --show-lineup --zip 92101 --debug
tv_grab_gracenote2epg --days 1 --zip 92101 --console

# Verify translations
python3 -c "
import gracenote2epg.gracenote2epg_dictionaries as gd
tm = gd.get_translation_manager()
print('Stats:', tm.get_statistics())
print('Test:', tm.translate('comedy', 'fr', 'category'))
"

# Clean up
deactivate

# Debug package contents
./scripts/dev-helper.bash show-dist
python3 -m zipfile -l dist/*.whl | grep locales
```

### Using development helper
```bash
# Check what's available
./scripts/dev-helper.bash help

# Show current distributions
./scripts/dev-helper.bash show-dist

# Clean and rebuild
./scripts/dev-helper.bash clean
make build
```

### Troubleshooting Development Tools

#### flake8-black conflicts
If you see `BLK100` errors during linting:
```bash
# Remove the conflicting plugin
pip uninstall flake8-black

# Check what's installed
pip list | grep flake8
```

The `flake8-black` plugin is **not needed** for this project and causes conflicts with our development workflow.

#### Mixed system/pip installations  
The scripts handle mixed installations (Ubuntu apt + pip) gracefully:
```bash
# Check what you have installed
./scripts/dev-helper.bash check-deps

# Typical Ubuntu setup (recommended):
# - black, flake8: via apt
# - autoflake, build, twine: via pip
```

#### Tool version conflicts
If you encounter tool conflicts:
```bash
# Option 1: Use virtual environment
python3 -m venv dev-env
source dev-env/bin/activate
pip install -e .[dev]

# Option 2: Check tool versions
black --version        # Should be 20.8b1+
flake8 --version       # Should be 3.8.0+
autoflake --version    # Should be 1.4+
```

## Integration with Development Workflow

These scripts integrate seamlessly with the overall development process:

### Code Quality Pipeline
```bash
# Individual steps (can be automated in CI/CD)
./scripts/dev-helper.bash format    # Code formatting
./scripts/dev-helper.bash lint      # Linting 
./scripts/test-distribution.bash    # Distribution testing

# One-shot validation
make all
```

### Version Management
The scripts work with the centralized version system in `gracenote2epg/__init__.py`:

```bash
# Check current version
python3 -c "import gracenote2epg; print(gracenote2epg.__version__)"

# After version update, test everything
make all
```

### Development Environment
```bash
# Set up complete development environment
./scripts/dev-helper.bash check-deps
./scripts/dev-helper.bash install-dev
make test-basic
```

## CI/CD integration

This script can be used in GitHub Actions workflows:

```yaml
# .github/workflows/test.yml
- name: Test distributions
  run: |
    chmod +x scripts/test-distribution.bash
    ./scripts/test-distribution.bash --full
```

## Contributing

To add new scripts or improve existing ones:

1. **Place scripts** in this `scripts/` directory
2. **Make them executable**: `chmod +x scripts/new-script.bash`  
3. **Follow naming convention**: Use `.bash` extension for bash scripts
4. **Add Makefile targets** if appropriate (in project root)
5. **Document in this README** with usage examples
6. **Use consistent logging**: Follow the color/logging conventions used in existing scripts
7. **Test integration**: Ensure new scripts work with `make` targets

### Style Guidelines
- Use the same color scheme: `RED`, `GREEN`, `YELLOW`, `BLUE`, `BOLD`, `NC`
- Provide `--help` option for all scripts
- Handle errors gracefully with `set -e`
- Log steps clearly with appropriate functions

### Integration with Main Documentation
- Update [Development Guide](../docs/development.md) for significant workflow changes
- Cross-reference between this README and development.md
- Maintain consistency with version management and release process
