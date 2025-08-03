# gracenote2epg - Modular TV Guide Grabber

A modular Python implementation for downloading TV guide data from tvlistings.gracenote.com with intelligent caching and TVheadend integration.

**Originally designed for Kodi/TVheadend integration** - This is a complete Python rewrite of the original zap2epg grabber.

## Key Features

- **🧩 Modular Architecture**: Clean separation of concerns for easy maintenance and testing
- **🎬 Kodi/TVheadend Ready**: Originally designed for seamless Kodi and TVheadend integration
- **🌍 Multi-Language Support**: Automatic language detection with French, English, and Spanish translations
- **🧠 Intelligent Cache Management**: Preserves existing data and only downloads what's needed
- **⚡ Smart Guide Refresh**: Refreshes first 48 hours while reusing cached data for later periods
- **💾 Automatic XMLTV Backup**: Safe backup system with retention management
- **📡 TVheadend Integration**: Automatic channel filtering and matching
- **🎯 Extended Program Details**: Optional enhanced descriptions with 95%+ cache efficiency
- **🛡️ WAF Protection**: Robust downloading with adaptive delays and retry logic
- **🔧 Platform Agnostic**: Auto-detection for Raspberry Pi, Synology NAS, and standard Linux

## Installation

### From Source

```bash
# Clone repository
git clone https://github.com/th0ma7/tv_grab_gracenote2epg.git
cd tv_grab_gracenote2epg

# Install with pip
pip install .

# Or install in development mode
pip install -e .
```

### Dependencies

#### Required Dependencies

Only one external dependency is required:

```bash
pip install requests>=2.25.0
```

#### Optional Dependencies (Recommended)

For automatic language detection, install langdetect:

```bash
pip install langdetect>=1.0.9
```

**Language Detection:**
- **Required for multi-language support**: langdetect is required for automatic French/English/Spanish detection
- **Without langdetect**: All content will be marked as English (no language detection errors)
- **Configurable**: Can be enabled/disabled via configuration or command line

The application will log the language detection status:
```
Language detection: Using langdetect library (enhanced accuracy)
# OR
Language detection: langdetect requested but not available
  Please install langdetect: pip install langdetect
Language detection: Disabled - defaulting to English for all content
# OR  
Language detection: Disabled by configuration - defaulting to English
```

## Quick Start

### Basic Usage

```bash
# Show capabilities
gracenote2epg --capabilities

# Download 7 days of guide data (XML to stdout, logs to file)
gracenote2epg --days 7 --zip 92101

# With console logging (logs to stderr + file)
gracenote2epg --days 7 --zip 92101 --console

# Use Canadian postal code
gracenote2epg --days 3 --postal J3B1M4 --warning --console
```

### Module Usage

```bash
# Run as Python module
python -m gracenote2epg --days 7 --zip 92101

# Direct script execution
./gracenote2epg.py --help
```

### Configuration

The script auto-creates a default configuration file on first run:

- **Linux/Docker**: `~/gracenote2epg/conf/gracenote2epg.xml`
- **Raspberry Pi**: `~/script.module.zap2epg/epggrab/conf/gracenote2epg.xml` (if exists)
- **Synology DSM7**: `/var/packages/tvheadend/var/epggrab/gracenote2epg/conf/gracenote2epg.xml`
- **Synology DSM6**: `/var/packages/tvheadend/target/var/epggrab/gracenote2epg/conf/gracenote2epg.xml`

## Logging Levels

The grabber follows XMLTV standards with XML output to `stdout` and configurable logging:

### Log Level Options (mutually exclusive):
- **Default**: INFO+WARNING+ERROR to file
- **`--warning`**: Only WARNING+ERROR to file  
- **`--debug`**: All DEBUG+INFO+WARNING+ERROR to file (very verbose)

### Console Output Options (mutually exclusive):
- **Default**: File logging only, XML to stdout
- **`--console`**: Display active log level to stderr + file
- **`--quiet`**: File logging only (explicit)

### Examples:

```bash
# Standard: XML to stdout, logs to file only
gracenote2epg --days 7 --zip 92101

# With console output: XML to stdout, logs to stderr + file
gracenote2epg --days 7 --zip 92101 --console

# Save XML to custom file instead of stdout
gracenote2epg --days 7 --zip 92101 --output guide.xml

# Custom file with console logs visible
gracenote2epg --days 7 --zip 92101 --output guide.xml --console
```

**Note**: When using `--output filename`, the XML is written to the specified file instead of stdout, and the default cache/xmltv.xml is replaced by your custom filename.

### Complete Examples with Logging Levels:

```bash
# Default logging: INFO+WARNING+ERROR to file, XML to stdout
gracenote2epg --days 7 --zip 92101

# Console output: same logs to stderr + file, XML to stdout  
gracenote2epg --days 7 --zip 92101 --console

# Warnings only: WARNING+ERROR to file, XML to stdout
gracenote2epg --days 7 --zip 92101 --warning

# Warnings with console: WARNING+ERROR to stderr + file
gracenote2epg --days 7 --zip 92101 --warning --console

# Debug mode: ALL logs to file, XML to stdout
gracenote2epg --days 7 --zip 92101 --debug

# Debug with console: ALL logs to stderr + file (very verbose)
gracenote2epg --days 7 --zip 92101 --debug --console
```

## Architecture

### Modular Structure

```
gracenote2epg/
├── __init__.py                    # Package initialization and exports
├── gracenote2epg_args.py          # Command-line argument parsing
├── gracenote2epg_config.py        # XML configuration management
├── gracenote2epg_downloader.py    # Optimized HTTP downloader with WAF protection
├── gracenote2epg_parser.py        # Guide data parsing and extended details
├── gracenote2epg_tvheadend.py     # TVheadend server integration
├── gracenote2epg_utils.py         # Cache management and utilities
└── gracenote2epg_xmltv.py         # XMLTV generation with intelligent descriptions

gracenote2epg.py                   # Main orchestration script
gracenote2epg.xml                  # Configuration file template
```

### Key Components

#### 🎛️ ArgumentParser (`gracenote2epg_args.py`)
- XMLTV baseline capabilities compliance
- System-specific directory auto-detection
- Input validation and normalization
- Flexible logging configuration

#### ⚙️ ConfigManager (`gracenote2epg_config.py`)
- XML configuration parsing and validation
- Automatic cleanup of deprecated settings
- Migration from older configuration versions

#### 🌐 OptimizedDownloader (`gracenote2epg_downloader.py`)
- WAF protection with adaptive delays
- Connection reuse and intelligent retry
- Support for both requests and urllib fallback

#### 📡 TvheadendClient (`gracenote2epg_tvheadend.py`)
- Automatic channel list fetching
- Channel number matching with subchannel logic
- Flexible station filtering

#### 💾 CacheManager (`gracenote2epg_utils.py`)
- Intelligent guide block caching (3-hour blocks)
- Series details cache with optimal reuse
- Automatic XMLTV backup and retention

#### 🔍 GuideParser (`gracenote2epg_parser.py`)
- TV guide data parsing from JSON
- Extended series details integration
- Intelligent cache usage for series data

#### 📺 XmltvGenerator (`gracenote2epg_xmltv.py`)
- XMLTV standard compliance
- Enhanced description formatting with multi-language support
- Genre mapping and program metadata

## Multi-Language Support

gracenote2epg features automatic language detection and translation for improved Kodi/TVheadend display:

### **Automatic Language Detection**
- **langdetect Library Required**: Uses statistical language detection for accurate French/English/Spanish identification
- **Configurable**: Can be enabled/disabled via configuration (`langdetect=true/false`) or command line (`--langdetect true/false`)
- **Smart Default**: Automatically enabled if langdetect is installed, disabled otherwise
- **Contextual Application**: Uses description analysis to set language for titles and metadata
- **XMLTV Compliance**: Proper `lang` attributes for all text elements
- **Fallback Behavior**: When disabled, all content is marked as English (no detection errors)

### **Smart Translations**
- **Localized Terms**: Automatically translates rating and status terms
- **Examples**:
  - English: "Rated: PG | NEW | CC"
  - French: "Classé: G | NOUVEAU | CC" 
  - Spanish: "Clasificado: PG | NUEVO | CC"

### **Enhanced Formatting**
- **Kodi-Optimized Display**: Line breaks separate main description from details
- **Before**: `Description text • S01E05 | Rated: G | CC` (single line)
- **After**: 
  ```
  Description text
  S01E05 | Classé: G | CC
  ```

### **Language Statistics**
Runtime statistics show distribution of detected languages when enabled:
```
Language detection: Using langdetect library (enhanced accuracy)
Language detection statistics (using langdetect library):
  French: 1424 episodes (35.6%)
  English: 2497 episodes (62.4%)
  Spanish: 81 episodes (2.0%)
```

When disabled:
```
Language detection: Disabled by configuration - defaulting to English
Language detection disabled - all content marked as English
```

## Configuration Options

### Required Settings
```xml
<setting id="zipcode">92101</setting>  <!-- US ZIP or Canadian postal code -->
```

### Extended Details with Multi-Language Support
```xml
<setting id="xdetails">true</setting>   <!-- Download series details -->
<setting id="xdesc">true</setting>      <!-- Enhanced descriptions with translations -->
<setting id="langdetect">true</setting> <!-- Enable automatic language detection -->
```

### TVheadend Integration
```xml
<setting id="tvhoff">true</setting>     <!-- Enable TVH integration -->
<setting id="tvhurl">127.0.0.1</setting> <!-- TVH server IP -->
<setting id="tvhport">9981</setting>    <!-- TVH port -->
<setting id="tvhmatch">true</setting>   <!-- Use TVH channel filtering -->
```

### Performance Tuning
```xml
<setting id="days">7</setting>          <!-- Guide duration (1-14 days) -->
<setting id="redays">7</setting>        <!-- Cache retention (match days) -->
```

## Performance & Caching

### Intelligent Cache System

The modular design includes a sophisticated caching system:

#### Guide Cache (3-hour blocks)
- **Smart Refresh**: Only refreshes first 48 hours
- **Block Reuse**: Reuses cached blocks outside refresh window
- **Safe Updates**: Backup/restore on failed downloads

#### Series Details Cache
- **First Run**: Downloads ~1000+ series details (normal)
- **Subsequent Runs**: 95%+ cache efficiency (much faster)
- **Intelligent Cleanup**: Removes only unused series

#### XMLTV Management
- **Always Backup**: Timestamped backup before each generation
- **Smart Retention**: Keeps backups for guide duration
- **Automatic Cleanup**: Removes old backups beyond retention

### Performance Statistics Example

```
Extended details processing completed:
  Total unique series: 1137
  Downloads attempted: 45        ← Only new series
  Unique series from cache: 1092 ← Reused existing (96.0% efficiency!)
  Cache efficiency: 96.0% (1092/1137 unique series reused)

Guide download completed:
  Blocks: 56 total (8 downloaded, 48 cached, 0 failed)
  Cache efficiency: 85.7% reused
  Success rate: 100.0%

Language detection statistics (using langdetect library):
  French: 1424 episodes (35.6%)
  English: 2497 episodes (62.4%)
  Spanish: 81 episodes (2.0%)
```

**Note**: Language statistics only appear when langdetect is enabled and available. Without langdetect, all content is marked as English.

## Command-Line Interface

### XMLTV Baseline Capabilities

```bash
gracenote2epg --description       # Show grabber description
gracenote2epg --version          # Show version
gracenote2epg --capabilities     # Show capabilities
```

### Logging Control

```bash
gracenote2epg --quiet            # File logging only (explicit)
gracenote2epg --warning          # Only warnings/errors to file
gracenote2epg --debug            # All debug info to file
gracenote2epg --console          # Display logs on stderr too
```

### Guide Parameters

```bash
gracenote2epg --days 7           # Number of days (1-14)
gracenote2epg --offset 1         # Start tomorrow instead of today
gracenote2epg --output guide.xml # Save XML to file (replaces default cache/xmltv.xml)
gracenote2epg --langdetect true  # Enable automatic language detection
gracenote2epg --langdetect false # Disable language detection (all English)
```

### Location Codes

```bash
gracenote2epg --zip 92101        # US ZIP code
gracenote2epg --postal J3B1M4    # Canadian postal code
gracenote2epg --code 90210       # Generic location code
```

### Configuration

```bash
gracenote2epg --config-file /path/to/config.xml  # Custom config file
gracenote2epg --basedir /path/to/basedir         # Custom base directory
```

## Development

### Project Structure for Development

```bash
tv_grab_gracenote2epg/
├── gracenote2epg/              # Main package
│   ├── __init__.py
│   ├── gracenote2epg_*.py      # Individual modules
│   └── __main__.py             # Module entry point
├── gracenote2epg.py            # Main script
├── gracenote2epg.xml           # Config template
├── setup.py                    # Installation setup
├── README.md                   # This file
├── LICENSE                     # GPL v3 license
└── tv_grab_gracenote2epg -> gracenote2epg.py  # Symlink
```

### Running Tests

```bash
# Install development dependencies
pip install -e .[dev]

# Install optional dependencies for enhanced features
pip install langdetect>=1.0.9

# Run tests (when available)
python -m pytest

# Type checking
mypy gracenote2epg/

# Code formatting
black gracenote2epg/
```

### Adding New Features

The modular architecture makes it easy to extend functionality:

1. **New Download Sources**: Extend `OptimizedDownloader`
2. **Additional Parsers**: Create new parser modules
3. **Output Formats**: Extend `XmltvGenerator` or create new generators
4. **Cache Strategies**: Modify `CacheManager` methods
5. **TVheadend Features**: Enhance `TvheadendClient`

## Migration from script.module.zap2epg / tv_grab_zap2epg

### Differences from Original

- **Modular Python Architecture**: Enhanced code organization and maintainability
- **No Dependencies on Bash**: Pure Python implementation  
- **Same Configuration**: Uses identical XML configuration format (zap2epg.xml/gracenote2epg.xml)
- **Same Cache Structure**: Compatible with existing cache files
- **Enhanced Logging**: Configurable output with proper stdout/stderr separation
- **Improved Error Handling**: Better WAF protection and retry logic
- **Enhanced Language Detection**: Optional langdetect integration for better accuracy

### Migration Steps

1. **Backup existing configuration**: Your existing `zap2epg.xml` works as-is (rename to `gracenote2epg.xml`)
2. **Install gracenote2epg**: `pip install .`
3. **Install optional dependencies**: `pip install langdetect` (recommended)
4. **Update scripts**: Replace `tv_grab_zap2epg` calls with `gracenote2epg`
5. **Test functionality**: Run with `--console` to verify operation

### Compatibility

- ✅ **Configuration Files**: 100% compatible with zap2epg.xml format
- ✅ **Cache Files**: Reuses existing zap2epg cache structure
- ✅ **XMLTV Output**: Identical format to original
- ✅ **TVheadend Integration**: Same API and behavior as original zap2epg
- ✅ **Command-line Arguments**: Enhanced interface with new logging options

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Ensure proper installation
pip install -e .

# Check Python path
python -c "import gracenote2epg; print(gracenote2epg.__file__)"
```

**Language Detection:**
```bash
# Install langdetect for automatic language detection
pip install langdetect

# Enable language detection
gracenote2epg --langdetect true --console --days 1 --zip 92101

# Disable language detection (all content marked as English)  
gracenote2epg --langdetect false --console --days 1 --zip 92101

# Check language detection status in logs
gracenote2epg --console --days 1 --zip 92101
```

**Configuration Problems:**
```bash
# Check default config location
gracenote2epg --console --days 1

# Use custom config
gracenote2epg --config-file /path/to/config.xml
```

**TVheadend Connection:**
```bash
# Test with console output
gracenote2epg --console --days 1 --zip 92101

# Check TVheadend settings in config.xml
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
gracenote2epg --debug --console --days 1 --zip 92101
```

Debug output includes:
- Configuration processing details
- Language detection method and statistics
- Cache efficiency metrics
- Download statistics and timing
- TVheadend integration status
- Extended details processing

## License

GPL v3 - Same as original script.module.zap2epg project

## Credits & Origins

This project was originally designed to be easily setup in Kodi for use as a grabber for TVheadend. This version builds upon edit4ever's script.module.zap2epg with tv_grab_zap2epg improvements and adds Python modular architecture.

**Original Sources:**
- **edit4ever**: Original **script.module.zap2epg** project and Python3 branch
- **th0ma7**: tv_grab_zap2epg improvements based on PR edit4ever/script.module.zap2epg#37 (much thanks for your great original work @edit4ever !!!)

This modular version builds upon the original zap2epg foundation with enhanced architecture, improved error handling, and modern Python development practices while maintaining full compatibility with existing configurations and cache formats.

## Version History

### 1.0 - Initial Release
- **Python Modularization**: Based on edit4ever's script.module.zap2epg with tv_grab_zap2epg improvements and Python modular architecture
- **Multi-Language Support**: Automatic French/English/Spanish detection with localized translations
- **Reliable Language Detection**: langdetect library integration with configurable enable/disable options
- **Enhanced XMLTV Generation**: Line breaks for better Kodi display, proper language attributes
- **Intelligent Cache Management**: Smart caching with 95%+ efficiency  
- **Flexible Logging System**: File-based logging with optional console output and language statistics
- **Improved Error Handling**: Robust downloading and parsing with WAF protection
- **Better Debugging**: Detailed statistics including language distribution and configurable verbosity
- **Platform Auto-detection**: Smart directory configuration for Raspberry Pi, Synology, etc.
- **Full Backward Compatibility**: Works with existing zap2epg configurations and cache
- **Kodi/TVheadend Integration**: Maintains original design goals for media center use with enhanced formatting
