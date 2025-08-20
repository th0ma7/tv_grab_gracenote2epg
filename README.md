# gracenote2epg - TV Guide Grabber for North America

A modern Python implementation for downloading TV guide data from tvlistings.gracenote.com with intelligent caching and TVheadend integration.

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

## 🌟 Key Features

- **XMLTV Standard Compliant** - Full DTD compliance for maximum compatibility
- **Intelligent Caching** - 95%+ cache efficiency with smart refresh strategies  
- **Multi-language Support** - Automatic French/English/Spanish detection and translations
- **TVheadend Integration** - Seamless channel filtering and matching
- **Unified Cache Management** - Streamlined configuration for all retention policies
- **Platform Agnostic** - Auto-detection for Raspberry Pi, Synology NAS, and Linux

## 🚀 Quick Start

### Installation

```bash
# Install with full features (recommended) - NOT YET PUBLISHED ON pypi.org
pip install gracenote2epg[full]

# Basic installation
pip install gracenote2epg
```

### Basic Usage

```bash
# Show capabilities (XMLTV standard)
tv_grab_gracenote2epg --capabilities

# Download 7 days of guide data
tv_grab_gracenote2epg --days 7 --zip 92101

# Test lineup detection
tv_grab_gracenote2epg --show-lineup --zip 92101
```

### Configuration

The script auto-creates a configuration file on first run. Basic setup:

```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <setting id="zipcode">92101</setting>        <!-- Your ZIP/postal code -->
  <setting id="lineupid">auto</setting>        <!-- Auto-detect lineup -->
  <setting id="days">7</setting>               <!-- Guide duration -->
</settings>
```

## 📚 Documentation

- **[Installation Guide](docs/installation.md)** - Detailed installation instructions for all platforms
- **[Configuration](docs/configuration.md)** - Complete configuration reference
- **[Lineup Configuration](docs/lineup-configuration.md)** - Finding and configuring your TV lineup
- **[Migration Guide](docs/migration.md)** - Migrating from other EPG grabbers
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

### Advanced Topics

- **[Cache & Retention Policies](docs/cache-retention.md)** - Managing cache and log retention
- **[Log Rotation](docs/log-rotation.md)** - Built-in log rotation system
- **[Development](docs/development.md)** - Contributing and development setup

## 🆘 Need Help?

1. **Check the [troubleshooting guide](docs/troubleshooting.md)**
2. **Test your lineup**: `tv_grab_gracenote2epg --show-lineup --zip YOUR_CODE`
3. **Enable debug logging**: `tv_grab_gracenote2epg --debug --console`
4. **[Create an issue](https://github.com/th0ma7/gracenote2epg/issues)** with logs

## 🛠️ Quick Examples

```bash
# Canadian postal code with console output
tv_grab_gracenote2epg --days 3 --postal J3B1M4 --console

# Save to custom file with debug info
tv_grab_gracenote2epg --days 7 --zip 92101 --output guide.xml --debug

# Use specific lineup (auto-extracts location)
tv_grab_gracenote2epg --days 7 --lineupid CAN-OTAJ3B1M4

# Disable language detection
tv_grab_gracenote2epg --days 7 --zip 92101 --langdetect false
```

## 📋 System Requirements

- **Python**: 3.7 or higher
- **Required**: `requests>=2.25.0`
- **Optional**: `langdetect>=1.0.9` (language detection), `polib>=1.1.0` (translations)

## 📄 License

GPL v3 - Same as original script.module.zap2epg project

## 🙏 Credits

Based on edit4ever's script.module.zap2epg with enhancements and modern Python architecture.

---

**[View Changelog](docs/changelog.md)** | **[Report Issues](https://github.com/th0ma7/gracenote2epg/issues)** | **[Contribute](docs/development.md)**
