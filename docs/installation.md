# Installation Guide

This guide covers all installation methods for gracenote2epg on different platforms.

## System Requirements

- **Python**: 3.7 or higher
- **Operating System**: Linux, macOS, Windows (Linux distributions preferred)
- **Network**: Internet connection for downloading guide data

## Installation Methods

### Method 1: PyPI Installation (Recommended)

#### Basic Installation
```bash
# Install basic package
pip install gracenote2epg

# Install with full features (language detection + translations)
pip install gracenote2epg[full]
```

#### Feature-Specific Installation
```bash
# Only language detection
pip install gracenote2epg[langdetect]

# Only translations
pip install gracenote2epg[translations]
```

### Method 2: From Wheel Package
```bash
# Download and install wheel
pip install gracenote2epg-1.4-py3-none-any.whl[full]
```

### Method 3: From Source Distribution
```bash
# Extract and use directly (no installation required)
tar -xzf gracenote2epg-1.4.tar.gz
cd gracenote2epg-1.4
./tv_grab_gracenote2epg --capabilities
```

### Method 4: Development Installation
```bash
git clone https://github.com/th0ma7/gracenote2epg.git
cd gracenote2epg
pip install -e .[full]  # Editable install with full features
```

## Platform-Specific Instructions

### Ubuntu/Debian
```bash
# Update system packages
sudo apt update

# Install Python and pip if not already installed
sudo apt install python3 python3-pip python3-venv

# Install gracenote2epg
pip3 install gracenote2epg[full]
```

### CentOS/RHEL/Fedora
```bash
# Install Python and pip
sudo dnf install python3 python3-pip python3-venv

# Install gracenote2epg
pip3 install gracenote2epg[full]
```

### Arch Linux
```bash
# Install dependencies
sudo pacman -S python python-pip

# Install gracenote2epg
pip install gracenote2epg[full]
```

### Synology NAS
```bash
# Enable SSH and package center
# Install Python 3 from Package Center

# Install via SSH
pip3 install gracenote2epg[full]
```

### Raspberry Pi
```bash
# Update system
sudo apt update && sudo apt upgrade

# Install Python dependencies
sudo apt install python3 python3-pip python3-venv

# Install gracenote2epg
pip3 install gracenote2epg[full]
```

## Package Distribution Types

gracenote2epg is available in two distribution formats:

### 1. Wheel Package (.whl) - For pip install
- Creates both `gracenote2epg` and `tv_grab_gracenote2epg` commands
- Installs in Python site-packages and system bin
- **Recommended for most users**

### 2. Source Distribution (.tar.gz) - For manual installation
- Includes `tv_grab_gracenote2epg` wrapper script in bin/
- Works immediately after extraction (no installation required)
- Useful for systems where pip install isn't preferred

**Important**: The `tv_grab_gracenote2epg` wrapper script is **essential** for:
- **XMLTV Standard Compliance** - Required naming convention
- **TVheadend Integration** - TVheadend specifically looks for `tv_grab_*` scripts
- **Distribution Compatibility** - Works with both wheel and source distributions

## Available Commands After Installation

### After pip install (Wheel Package)
```bash
gracenote2epg --version              # Primary command
tv_grab_gracenote2epg --capabilities # XMLTV standard wrapper (ESSENTIAL)
python -m gracenote2epg --version    # Module execution
```

### From source distribution (extract .tar.gz)
```bash
./tv_grab_gracenote2epg --capabilities # Wrapper script in bin/ directory
python3 -m gracenote2epg --version     # Module execution
```

**Critical**: The `tv_grab_gracenote2epg` command is **required** for:
- TVheadend EPG grabber detection
- XMLTV standard compliance  
- Integration with other XMLTV-compatible software

Both installation methods provide this essential wrapper script.

## Feature Dependencies

### Core Dependencies (Always Installed)
- `requests>=2.25.0` - HTTP requests for downloading guide data

### Optional Dependencies
- `langdetect>=1.0.9` - Automatic language detection for French/English/Spanish
- `polib>=1.1.0` - Category and term translations using .po files

### Installing Optional Features
```bash
# Get all features
pip install gracenote2epg[full]

# Only language detection
pip install langdetect

# Only translations  
pip install polib

# Check if features are available
python -c "import langdetect; print('Language detection: OK')"
python -c "import polib; print('Translations: OK')"
```

## Verification

### Test Installation
```bash
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
    print('✗ Language detection not available')
"

# Test translations
python -c "
try:
    import polib
    print('✓ Translations available')  
except ImportError:
    print('✗ Translations not available')
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

### Synology DSM7
- **Config**: `/var/packages/tvheadend/var/epggrab/gracenote2epg/conf/gracenote2epg.xml`

### Synology DSM6
- **Config**: `/var/packages/tvheadend/target/var/epggrab/gracenote2epg/conf/gracenote2epg.xml`

## Troubleshooting Installation

### Common Issues

**Problem**: `Command 'gracenote2epg' not found`
```bash
# Solution: Install with pip
pip install gracenote2epg

# Alternative: Use module execution
python -m gracenote2epg
```

**Problem**: Permission denied
```bash
# Solution: Install for user only
pip install --user gracenote2epg[full]

# Or use virtual environment
python3 -m venv gracenote_env
source gracenote_env/bin/activate
pip install gracenote2epg[full]
```

**Problem**: Package conflicts
```bash
# Solution: Use virtual environment
python3 -m venv clean_env
source clean_env/bin/activate
pip install gracenote2epg[full]
```

## Next Steps

After installation:

1. **[Configure your lineup](lineup-configuration.md)** - Set up your TV lineup
2. **[Basic configuration](configuration.md)** - Configure the grabber settings
3. **[Test your setup](troubleshooting.md#testing-setup)** - Verify everything works

## Upgrading

### From PyPI
```bash
# Upgrade to latest version
pip install --upgrade gracenote2epg[full]

# Check new version
tv_grab_gracenote2epg --version
```

### Migration Notes
See the **[Migration Guide](migration.md)** if upgrading from:
- tv_grab_zap2epg  
- Other XMLTV grabbers
- Older versions of gracenote2epg
