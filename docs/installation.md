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

## Upgrading

### From GitHub
```bash
# Upgrade to latest version
pip install --upgrade git+https://github.com/th0ma7/gracenote2epg.git[full]

# For editable installs
cd gracenote2epg
git pull
pip install -e .[full]

# Check new version
tv_grab_gracenote2epg --version
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
See the **[Migration Guide](migration.md)** if upgrading from:
- tv_grab_zap2epg  
- Other XMLTV grabbers
- Older versions of gracenote2epg
