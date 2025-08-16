# Building and Testing gracenote2epg Python Wheel Package

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
│   ├── main.py                  # Main script (formerly gracenote2epg.py)
│   ├── gracenote2epg_*.py       # Utility modules
│   └── locales/                 # FR/ES translations
├── setup.py                     # Package configuration
├── MANIFEST.in                  # Files to include in distribution
├── LICENSE                      # GPL-3.0 license
├── README.md                    # Documentation
├── gracenote2epg.xml           # Default configuration
└── dist/                       # Output directory (created automatically)
```

## Step 1: Building the Wheel

### Clean previous builds (optional)
```bash
# Navigate to project directory
cd tv_grab_gracenote2epg

# Clean previous builds
rm -rf build/ dist/ *.egg-info/
```

### Build the package
```bash
# Build both source distribution and wheel
python3 -m build

# Expected output:
# * Creating venv isolated environment...
# * Installing packages in isolated environment... (setuptools >= 40.8.0, wheel)
# * Getting build dependencies for sdist...
# Successfully built gracenote2epg-1.4.tar.gz and gracenote2epg-1.4-py3-none-any.whl
```

### Verify build artifacts
```bash
# Check generated files
ls -la dist/
# Expected files:
# gracenote2epg-1.4-py3-none-any.whl  (binary wheel)
# gracenote2epg-1.4.tar.gz           (source distribution)
```

## Step 2: Testing the Wheel

### Create isolated test environment
```bash
# Create virtual environment
python3 -m venv ~/test_env

# Activate the environment
source ~/test_env/bin/activate

# Verify activation (prompt should show (test_env))
# (test_env) user@hostname:~/tv_grab_gracenote2epg$
```

### Install and upgrade pip
```bash
# Upgrade pip to latest version
pip install --upgrade pip

# Expected output:
# Requirement already satisfied: pip in ./test_env/lib/python3.12/site-packages (24.0)
# Collecting pip
#   Downloading pip-25.2-py3-none-any.whl.metadata (4.7 kB)
# ...
# Successfully installed pip-25.2
```

### Install the wheel package
```bash
# Install basic package
pip install tv_grab_gracenote2epg/dist/gracenote2epg-1.4-py3-none-any.whl

# OR install with full dependencies (recommended)
pip install "tv_grab_gracenote2epg/dist/gracenote2epg-1.4-py3-none-any.whl[full]"
```

The `[full]` extra installs:
- `langdetect>=1.0.9` - For automatic language detection
- `polib>=1.1.0` - For category translations

### Verify installation
```bash
# Check installed packages
pip list

# Expected packages:
# gracenote2epg      1.4
# requests           2.32.4
# langdetect         1.0.9   (if [full] was used)
# polib              1.2.0   (if [full] was used)
# + dependencies

# Show package details
pip show gracenote2epg

# Expected output:
# Name: gracenote2epg
# Version: 1.4
# Summary: North America TV Guide Grabber for gracenote.com
# Home-page: https://github.com/th0ma7/gracenote2epg
# Author: th0ma7
# Location: /home/user/test_env/lib/python3.12/site-packages
# Requires: requests
```

## Step 3: Testing Functionality

### Test package import
```bash
# Test Python import
python -c "import gracenote2epg; print(gracenote2epg.__file__)"
# Expected: /home/user/test_env/lib/python3.12/site-packages/gracenote2epg/__init__.py

# Test version
python -c "import gracenote2epg; print(gracenote2epg.__version__)"
# Expected: 1.4
```

### Test command-line interfaces
```bash
# Test module execution
python -m gracenote2epg --version
# Expected: 1.4

python -m gracenote2epg --capabilities
# Expected: baseline

# Test entry points (if configured)
gracenote2epg --version
# Expected: 1.4

gracenote2epg --capabilities
# Expected: baseline
```

### Test translations (if [full] was installed)
```bash
# Test translation system
python3 -c "
from gracenote2epg import get_category_translation, get_translation_statistics
print('🇬🇧 EN:', get_category_translation('comedy drama', 'en'))
print('🇫🇷 FR:', get_category_translation('comedy drama', 'fr'))
print('🇪🇸 ES:', get_category_translation('comedy drama', 'es'))
print('Translation stats:', get_translation_statistics())
"

# Expected output:
# 🇬🇧 EN: Comedy Drama
# 🇫🇷 FR: Comédie dramatique
# 🇪🇸 ES: Comedia dramática
# Translation stats: {'fr': 126, 'es': 126}
```

### Test with real data (optional)
```bash
# Test with minimal data fetch (requires network)
gracenote2epg --days 1 --postal J3B1M4 --norefresh --console --warning --output /tmp/test.xml

# Verify output
head -10 /tmp/test.xml
# Should show XMLTV header
```

## Step 4: Clean Up Test Environment

```bash
# Deactivate virtual environment
deactivate

# Remove test environment (optional)
rm -rf ~/test_env
```

## Version Management

To change the version:

1. **Edit only one file**: `gracenote2epg/__init__.py`
   ```python
   __version__ = "1.5"  # Update this line only
   ```

2. **Rebuild**:
   ```bash
   rm -rf build/ dist/ *.egg-info/
   python3 -m build
   ```

3. **The new wheel will be**: `gracenote2epg-1.5-py3-none-any.whl`
