# gracenote2epg Packaging & Development Guide

This comprehensive guide covers building, testing, and developing the gracenote2epg package.

## Overview

The gracenote2epg package supports multiple distribution formats:

- **Wheel (.whl)**: Binary distribution for `pip install`, creates both command names
- **Source (.tar.gz)**: Source distribution with wrapper script, works without installation
- **Development**: Editable install for development work

## System Prerequisites

### Ubuntu/Debian
```bash
# Update system packages
sudo apt update

# Install required Python build tools
sudo apt install python3-build python3-pip python3-venv
```

### Other distributions
```bash
# CentOS/RHEL/Fedora
sudo dnf install python3-build python3-pip python3-venv

# Arch Linux
sudo pacman -S python-build python-pip python-virtualenv
```

## Project Structure

Ensure your project has this structure:

```
tv_grab_gracenote2epg/
├── gracenote2epg/
│   ├── __init__.py              # Contains __version__ = "1.4"
│   ├── __main__.py              # Entry point for console commands
│   ├── main.py                  # Main script
│   ├── gracenote2epg_*.py       # Utility modules
│   └── locales/                 # FR/ES translations
├── tv_grab_gracenote2epg        # Wrapper script for source distribution
├── setup.py                     # Package configuration
├── MANIFEST.in                  # Files to include in distribution
├── LICENSE                      # GPL-3.0 license
├── README.md                    # Documentation
├── gracenote2epg.xml           # Default configuration
└── dist/                       # Output directory (created automatically)
```

## Build Package

```bash
# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build both wheel and source distribution
python3 -m build

# Verify build artifacts
ls -la dist/
# Expected: gracenote2epg-1.4-py3-none-any.whl and gracenote2epg-1.4.tar.gz
```

## Manual Testing

### Test Wheel
```bash
python3 -m venv ~/test_env && source ~/test_env/bin/activate
pip install dist/gracenote2epg-1.4-py3-none-any.whl[full]
gracenote2epg --version && tv_grab_gracenote2epg --capabilities
deactivate && rm -rf ~/test_env
```

### Test Source
```bash
tar -xzf dist/gracenote2epg-1.4.tar.gz
cd gracenote2epg-1.4
./tv_grab_gracenote2epg --version && ./tv_grab_gracenote2epg --capabilities
cd .. && rm -rf gracenote2epg-1.4
```

## Package Contents

### Wheel Distribution (.whl)
- Creates `gracenote2epg` and `tv_grab_gracenote2epg` commands via entry_points
- Installs package modules in site-packages
- Works with `pip install`

### Source Distribution (.tar.gz)  
- Includes `tv_grab_gracenote2epg` wrapper script that works without installation
- Contains all source code and data files
- Can be used directly after extraction

## Command Equivalents

### After pip install (wheel):
```bash
gracenote2epg --version           # Entry point command
tv_grab_gracenote2epg --version   # Entry point command  
python -m gracenote2epg --version # Module execution
```

### From source directory (.tar.gz):
```bash
./tv_grab_gracenote2epg --version  # Wrapper script
python3 -m gracenote2epg --version # Module execution
```

All commands do the same thing - the wrapper and entry points both call `gracenote2epg.__main__:main`.

## Version Management

To update version:
1. Edit `gracenote2epg/__init__.py`: `__version__ = "1.5"`
2. Rebuild: `python3 -m build`
3. Test: `./test_packaging.sh`

The version is automatically extracted from `__init__.py` during build.
