# Installation Guide

> **⚠️ Important**: gracenote2epg is not yet published on PyPI. Currently available installation methods are from source only.

This guide covers all installation methods for gracenote2epg on different platforms.

## 📦 Publication Status

- **✅ GitHub**: Available for source installation
- **⏳ PyPI**: Publication pending
- **🔮 Future**: `pip install gracenote2epg[full]` will be available once published

## Installation Methods

> **📝 Note**: Installation commands use PEP 508 syntax.

### Method 1: Install from GitHub (Recommended)

#### With Full Features
```bash
# Install directly from GitHub with all features (latest version) - Modern PEP 508 syntax
pip install "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.5"

# Basic installation from GitHub (latest)
pip install "gracenote2epg @ git+https://github.com/th0ma7/gracenote2epg.git@v1.5"
```

### Method 2: Clone and Install
```bash
# Clone repository and install (latest version)
git clone --branch v1.5 https://github.com/th0ma7/gracenote2epg.git
cd gracenote2epg
pip install .[full]  # Install with full features
pip install .        # Basic installation
```

### Method 4: Manual Installation (Source Distribution)
```bash
# Download source from GitHub releases (if available)
wget https://github.com/th0ma7/gracenote2epg/archive/v1.5.tar.gz
tar -xzf v1.5.tar.gz
cd gracenote2epg-1.5
pip install .[full]

# Or run directly without installation
./tv_grab_gracenote2epg --capabilities
```

### 🔮 Future: PyPI Installation (Once Published)

Once gracenote2epg is published on PyPI, these commands will work:

```bash
# Basic installation (future)
pip install gracenote2epg

# Install with full features (future - recommended)
pip install gracenote2epg[full]

# Install specific version (future)
pip install gracenote2epg==1.5

# Feature-specific installation (future)
pip install gracenote2epg[langdetect]
pip install gracenote2epg[translations]
```

## Platform-Specific Instructions

### Ubuntu/Debian/RaspberryPi
```bash
# Update and Install Python and pip if not already installed
sudo apt update && apt install -y python3 python3-pip python3-venv python3-langdetect python3-polib

# Install gracenote2epg from GitHub
pip3 install "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.5"

# Verify installation
pip3 list | grep gracenote2epg
tv_grab_gracenote2epg --version
```

### CentOS/RHEL/Fedora
```bash
# Install Python and pip
sudo dnf update -y && dnf install -y python3 python3-pip python3-virtualenv

# Install gracenote2epg from GitHub
pip3 install "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.5"

# Verify installation
pip3 list | grep gracenote2epg
tv_grab_gracenote2epg --version
```

### Arch Linux
```bash
# Install dependencies
sudo pacman -Syu python python-pip python-virtualenv python-langdetect python-polib

# Install gracenote2epg from GitHub
pip install "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.5"

# Verify installation
pip list | grep gracenote2epg
tv_grab_gracenote2epg --version
```

### Synology NAS with TVheadend
```bash
# Prerequisites: TVheadend must already be installed from Package Center

# Install in TVheadend environment (DSM7)
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 install "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.5"'

# Verify installation in TVheadend environment
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 list | grep gracenote2epg'
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/tv_grab_gracenote2epg --version'
```

## Package Distribution Types

gracenote2epg is available in two distribution formats:

### 1. Wheel Package (.whl) - For pip install
- Creates both `gracenote2epg` and `tv_grab_gracenote2epg` commands
- Installs in Python site-packages and system bin
- **Recommended for most users**

### 2. Source Distribution (.tar.gz) - For manual installation
- Includes **only** `tv_grab_gracenote2epg` wrapper script in bin/
- Works immediately after extraction (no installation required)
- Useful for systems where pip install isn't preferred

**Important**: The `tv_grab_gracenote2epg` wrapper script is **essential** for *XMLTV Standard Compliance* and *TVheadend Integration* (looks for `tv_grab_*` scripts).

## Available Commands After Installation

```bash
gracenote2epg --version              # Primary command (wheel based installed only)
tv_grab_gracenote2epg --capabilities # XMLTV standard wrapper (ESSENTIAL)
python -m gracenote2epg --version    # Module execution
```

## Feature Dependencies

### Core Dependencies (Always Installed)
- `requests>=2.25.0` - HTTP requests for downloading guide data

### Optional Dependencies (via extras_require)
- `langdetect>=1.0.9` - Automatic language detection for French/English/Spanish
- `polib>=1.1.0` - Category and term translations using .po files

### Alternative Installion Options
```bash
# Get all features (using PEP 508 syntax)
pip install "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.5"

# Only language detection
pip install "gracenote2epg[langdetect] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.5"

# Only translations  
pip install "gracenote2epg[translations] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.5"

# Development features
pip install "gracenote2epg[dev] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.5"

# Or install dependencies manually
pip install langdetect polib
```

## Verification

### Test Installation
```bash
# Check if package is installed
pip list | grep gracenote2epg
# Expected output: gracenote2epg    1.5    /path/to/installation

# Check version
tv_grab_gracenote2epg --version

# Show capabilities (XMLTV standard)
tv_grab_gracenote2epg --capabilities

# Test basic functionality
tv_grab_gracenote2epg --show-lineup --zip 92101
```

### Test Features
```bash
# Test language detection
python -c "
try:
    import langdetect
    print('✓ Language detection available')
except ImportError:
    print('✗ Language detection not available - install with [full]')
"

# Test translations
python -c "
try:
    import polib
    print('✓ Translations available')  
except ImportError:
    print('✗ Translations not available - install with [full]')
"
```

## Default Directories

gracenote2epg auto-detects your system and creates appropriate directories:

### Linux/Docker
- **Config**: `~/gracenote2epg/conf/gracenote2epg.xml`
- **Cache**: `~/gracenote2epg/cache/`
- **Logs**: `~/gracenote2epg/log/`

### Raspberry Pi
- **Config**: `~/script.module.zap2epg/epggrab/conf/gracenote2epg.xml` (if exists)
- **Fallback**: `~/gracenote2epg/conf/gracenote2epg.xml`

### Synology (with TVheadend)
- **Config**: `/var/packages/tvheadend/var/epggrab/gracenote2epg/conf/gracenote2epg.xml` (DSM7)
- **Config**: `/var/packages/tvheadend/target/var/epggrab/gracenote2epg/conf/gracenote2epg.xml` (DSM6)


## Troubleshooting Installation

### Common Issues

**Problem**: Permission denied
```bash
# Solution: Install for user only (modern PEP 508 syntax)
pip install --user "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.5"
```

**Problem**: Package conflicts
```bash
# Solution: Use virtual environment
python3 -m venv gracenote_env
source gracenote_env/bin/activate
pip install "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.5"
```

### Migration Notes
See the **[TVheadend Guide](tvheadend.md)** if integrating with TVheadend after upgrading.
