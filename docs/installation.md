# Installation Guide

> **⚠️ Important**: gracenote2epg is not yet published on PyPI. Currently available installation methods are from source only.

This guide covers all installation methods for gracenote2epg on different platforms.

## 📦 Publication Status

- **✅ GitHub**: Available for source installation
- **⏳ PyPI**: Publication pending
- **🔮 Future**: `pip install gracenote2epg[full]` will be available once published

## Installation Methods

### Method 1: Install from GitHub (Recommended)

#### With Full Features
```bash
# Install directly from GitHub with all features
pip install git+https://github.com/th0ma7/gracenote2epg.git[full]

# Basic installation from GitHub
pip install git+https://github.com/th0ma7/gracenote2epg.git
```

### Method 2: Clone and Install
```bash
# Clone repository and install
git clone https://github.com/th0ma7/gracenote2epg.git
cd gracenote2epg
pip install .[full]  # Install with full features
pip install .        # Basic installation
```

### Method 3: Development Installation
```bash
git clone https://github.com/th0ma7/gracenote2epg.git
cd gracenote2epg
pip install -e .[full]  # Editable install with full features
```

### Method 4: Manual Installation (Source Distribution)
```bash
# Download source from GitHub releases (if available)
wget https://github.com/th0ma7/gracenote2epg/archive/v1.4.tar.gz
tar -xzf v1.4.tar.gz
cd gracenote2epg-1.4
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

# Feature-specific installation (future)
pip install gracenote2epg[langdetect]
pip install gracenote2epg[translations]
```

## Platform-Specific Instructions

### Ubuntu/Debian
```bash
# Update system packages
sudo apt update

# Install Python and pip if not already installed
sudo apt install python3 python3-pip python3-venv

# Install gracenote2epg from GitHub
pip3 install git+https://github.com/th0ma7/gracenote2epg.git[full]

# Verify installation
pip3 list | grep gracenote2epg
tv_grab_gracenote2epg --version
```

### CentOS/RHEL/Fedora
```bash
# Install Python and pip
sudo dnf install python3 python3-pip python3-venv

# Install gracenote2epg from GitHub
pip3 install git+https://github.com/th0ma7/gracenote2epg.git[full]

# Verify installation
pip3 list | grep gracenote2epg
tv_grab_gracenote2epg --version
```

### Arch Linux
```bash
# Install dependencies
sudo pacman -S python python-pip

# Install gracenote2epg from GitHub
pip install git+https://github.com/th0ma7/gracenote2epg.git[full]

# Verify installation
pip list | grep gracenote2epg
tv_grab_gracenote2epg --version
```

### Synology NAS with TVheadend (DSM7)
```bash
# Prerequisites: TVheadend must already be installed from Package Center

# Install in TVheadend environment (DSM7)
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 install git+https://github.com/th0ma7/gracenote2epg.git[full]'

# Verify installation in TVheadend environment
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 list | grep gracenote2epg'
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/tv_grab_gracenote2epg --version'
```

### Synology NAS with TVheadend (DSM6)
```bash
# Prerequisites: TVheadend must already be installed from Package Center

# Install in TVheadend environment (DSM6)
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 install git+https://github.com/th0ma7/gracenote2epg.git[full]'

# Verify installation in TVheadend environment
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 list | grep gracenote2epg'
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/tv_grab_gracenote2epg --version'
```

### Raspberry Pi
```bash
# Update system
sudo apt update && sudo apt upgrade

# Install Python dependencies
sudo apt install python3 python3-pip python3-venv

# Install gracenote2epg from GitHub
pip3 install git+https://github.com/th0ma7/gracenote2epg.git[full]

# Verify installation
pip3 list | grep gracenote2epg
tv_grab_gracenote2epg --version

# Optional: Check available memory (Pi can be resource-constrained)
free -h
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

### After GitHub Installation
```bash
gracenote2epg --version              # Primary command
tv_grab_gracenote2epg --capabilities # XMLTV standard wrapper (ESSENTIAL)
python -m gracenote2epg --version    # Module execution
```

### From Manual Source Installation
```bash
./tv_grab_gracenote2epg --capabilities # Wrapper script in project directory
python3 -m gracenote2epg --version     # Module execution (if installed)
```

**Critical**: The `tv_grab_gracenote2epg` command is **required** for:
- TVheadend EPG grabber detection
- XMLTV standard compliance  
- Integration with other XMLTV-compatible software

All installation methods provide this essential wrapper script.

## Feature Dependencies

### Core Dependencies (Always Installed)
- `requests>=2.25.0` - HTTP requests for downloading guide data

### Optional Dependencies (via extras_require)
- `langdetect>=1.0.9` - Automatic language detection for French/English/Spanish
- `polib>=1.1.0` - Category and term translations using .po files

### Setup.py Configuration for Extras

To support feature-specific installation (`pip install gracenote2epg[langdetect]`), add this to your `setup.py`:

```python
setup(
    # ... other parameters ...
    install_requires=[
        'requests>=2.25.0',
    ],
    extras_require={
        'langdetect': ['langdetect>=1.0.9'],
        'translations': ['polib>=1.1.0'],
        'full': ['langdetect>=1.0.9', 'polib>=1.1.0'],
        'dev': ['langdetect>=1.0.9', 'polib>=1.1.0', 'pytest>=6.0'],
    },
    # ... rest of setup.py ...
)
```

### Installing Optional Features
```bash
# Get all features
pip install gracenote2epg[full]

# Only language detection
pip install gracenote2epg[langdetect]

# Only translations  
pip install gracenote2epg[translations]

# Development features
pip install gracenote2epg[dev]

# Or install dependencies manually
pip install langdetect polib

# Check if features are available
python -c "import langdetect; print('Language detection: OK')"
python -c "import polib; print('Translations: OK')"
```

## Verification

### Test Installation
```bash
# Check if package is installed
pip list | grep gracenote2epg
# Expected output: gracenote2epg    1.4    /path/to/installation

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

# Check all installed packages related to gracenote2epg
pip list | grep -E "(gracenote2epg|langdetect|polib|requests)"
```

### Synology TVheadend Environment Verification
```bash
# For Synology with TVheadend, verify in the correct environment:

# Check installation in TVheadend environment
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 list | grep gracenote2epg'

# Test capabilities in TVheadend environment  
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/tv_grab_gracenote2epg --capabilities'

# Test lineup detection in TVheadend environment
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/tv_grab_gracenote2epg --show-lineup --zip 92101'
```

## Upgrading

### From GitHub
```bash
# Upgrade to latest version
pip install --upgrade git+https://github.com/th0ma7/gracenote2epg.git[full]

# Verify new installation
pip list | grep gracenote2epg
tv_grab_gracenote2epg --version

# For editable installs
cd gracenote2epg
git pull
pip install -e .[full]
```

### Synology TVheadend Environment
```bash
# Upgrade in TVheadend environment
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 install --upgrade git+https://github.com/th0ma7/gracenote2epg.git[full]'

# Verify upgrade
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 list | grep gracenote2epg'
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/tv_grab_gracenote2epg --version'
```

### 🔮 Future: From PyPI (Once Published)
```bash
# Upgrade to latest version (future)
pip install --upgrade gracenote2epg[full]

# Check new version
tv_grab_gracenote2epg --version
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

### Synology DSM7 (with TVheadend)
- **Config**: `/var/packages/tvheadend/var/epggrab/gracenote2epg/conf/gracenote2epg.xml`

### Synology DSM6 (with TVheadend)
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

## Migration from Other EPG Grabbers

If you're migrating from another EPG grabber, gracenote2epg can often replace it directly.

### Common Migration Scenarios

#### From tv_grab_zap2epg
```bash
# 1. Install gracenote2epg
pip install git+https://github.com/th0ma7/gracenote2epg.git[full]

# 2. Test gracenote2epg works
tv_grab_gracenote2epg --show-lineup --zip YOUR_CODE

# 3. Configuration migration (optional - gracenote2epg auto-migrates)
# Your existing zap2epg configuration will be automatically detected and migrated

# 4. TVheadend integration - see docs/tvheadend.md
```

#### From Other XMLTV Grabbers
```bash
# Install gracenote2epg
pip install git+https://github.com/th0ma7/gracenote2epg.git[full]

# Test basic functionality
tv_grab_gracenote2epg --capabilities
tv_grab_gracenote2epg --show-lineup --zip YOUR_CODE

# Configure (create new configuration)
tv_grab_gracenote2epg --days 1 --zip YOUR_CODE --console --debug
```

### Configuration Compatibility

gracenote2epg automatically migrates compatible settings from:

- **tv_grab_zap2epg**: Most settings auto-migrate
- **tv_grab_zap2xml**: Lineup settings compatible
- **Other XMLTV grabbers**: Manual configuration needed

### Software-Level Migration Notes

- **Parallel installation**: You can install gracenote2epg alongside existing grabbers
- **Testing phase**: Test gracenote2epg before removing old grabber
- **Configuration backup**: Old configurations are automatically backed up
- **Dependencies**: gracenote2epg has minimal dependencies (just `requests`)

## Next Steps

After installation:

1. **[Configure your lineup](lineup-configuration.md)** - Set up your TV lineup
2. **[Basic configuration](configuration.md)** - Configure the grabber settings
3. **[TVheadend integration](tvheadend.md)** - Configure TVheadend EPG grabber (if using TVheadend)
4. **[Test your setup](troubleshooting.md#testing-setup)** - Verify everything works

### Post-Installation Validation

```bash
# Complete installation check
echo "=== Installation Verification ==="
pip list | grep -E "(gracenote2epg|langdetect|polib|requests)"

echo "=== Command Availability ==="
which tv_grab_gracenote2epg
which gracenote2epg

echo "=== Version Check ==="
tv_grab_gracenote2epg --version
gracenote2epg --version

echo "=== Capabilities Test ==="
tv_grab_gracenote2epg --capabilities

echo "=== Quick Lineup Test ==="
tv_grab_gracenote2epg --show-lineup --zip 92101
```

### For Synology/TVheadend Users

```bash
# Synology TVheadend environment validation
echo "=== TVheadend Environment Check ==="
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 list | grep gracenote2epg'

echo "=== TVheadend Command Check ==="
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/which tv_grab_gracenote2epg'

echo "=== TVheadend Capabilities ==="
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/tv_grab_gracenote2epg --capabilities'

echo "=== TVheadend Lineup Test ==="
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/tv_grab_gracenote2epg --show-lineup --zip 92101'

# Next: Configure in TVheadend EPG Grabber Modules
echo "Next step: Configure tv_grab_gracenote2epg in TVheadend"
echo "See: docs/tvheadend.md"
```

## 🚀 Publishing to PyPI (For Maintainers)

When ready to publish on PyPI:

```bash
# 1. Install build tools
pip install build twine

# 2. Build distributions
python -m build

# 3. Upload to PyPI (requires API token)
python -m twine upload dist/*

# 4. Test PyPI installation
pip install gracenote2epg[full]
```

After PyPI publication, update documentation to use standard pip commands.

### Migration Notes
See the **[TVheadend Guide](tvheadend.md)** if integrating with TVheadend after upgrading.
