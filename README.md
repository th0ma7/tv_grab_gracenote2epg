# gracenote2epg - Modular TV Guide Grabber

A modular Python implementation for downloading TV guide data from tvlistings.gracenote.com with intelligent caching and TVheadend integration.

**Based on tv_grab_zap2epg v4.0** - Converted to pure Python with modular architecture.

## Key Features

- **🧩 Modular Architecture**: Clean separation of concerns for easy maintenance and testing
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

Only one external dependency required:

```bash
pip install requests>=2.25.0
```

## Quick Start

### Basic Usage

```bash
# Show capabilities
gracenote2epg --capabilities

# Download 7 days of guide data
gracenote2epg --days 7 --zip 92101 --debug

# Use Canadian postal code
gracenote2epg --days 3 --postal J3B1M4 --quiet
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
- Enhanced description formatting
- Genre mapping and program metadata

## Configuration Options

### Required Settings
```xml
<setting id="zipcode">92101</setting>  <!-- US ZIP or Canadian postal code -->
```

### Extended Details
```xml
<setting id="xdetails">true</setting>   <!-- Download series details -->
<setting id="xdesc">true</setting>      <!-- Enhanced descriptions -->
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
```

## Command-Line Interface

### XMLTV Baseline Capabilities

```bash
gracenote2epg --description       # Show grabber description
gracenote2epg --version          # Show version
gracenote2epg --capabilities     # Show capabilities
gracenote2epg --quiet            # Suppress progress information
gracenote2epg --debug            # Enable debug logging
```

### Guide Parameters

```bash
gracenote2epg --days 7           # Number of days (1-14)
gracenote2epg --offset 1         # Start tomorrow instead of today
gracenote2epg --output guide.xml # Redirect output to file
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

## Migration from tv_grab_zap2epg

### Differences from Original

- **Pure Python**: No bash wrapper required
- **Modular Design**: Easier to maintain and extend
- **Same Configuration**: Uses identical XML configuration format
- **Same Cache Structure**: Compatible with existing cache files
- **Enhanced Logging**: More detailed statistics and debugging

### Migration Steps

1. **Backup existing configuration**: Your `zap2epg.xml` works as-is
2. **Install gracenote2epg**: `pip install .`
3. **Update scripts**: Replace `tv_grab_zap2epg` with `gracenote2epg`
4. **Test functionality**: Run with `--debug` to verify operation

### Compatibility

- ✅ **Configuration Files**: 100% compatible
- ✅ **Cache Files**: Reuses existing cache
- ✅ **XMLTV Output**: Identical format
- ✅ **TVheadend Integration**: Same API and behavior
- ✅ **Command-line Arguments**: Same interface

## Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Ensure proper installation
pip install -e .

# Check Python path
python -c "import gracenote2epg; print(gracenote2epg.__file__)"
```

**Configuration Problems:**
```bash
# Check default config location
gracenote2epg --debug --days 1

# Use custom config
gracenote2epg --config-file /path/to/config.xml
```

**TVheadend Connection:**
```bash
# Test with debug output
gracenote2epg --debug --days 1 --zip 92101

# Check TVheadend settings in config.xml
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
gracenote2epg --debug --days 1 --zip 92101
```

Debug output includes:
- Configuration processing details
- Cache efficiency metrics
- Download statistics and timing
- TVheadend integration status
- Extended details processing

## License

GPL v3 - Same as original tv_grab_zap2epg

## Credits

Based on the excellent work of **edit4ever** on the original **script.module.zap2epg** project. This modular Python version maintains full compatibility while providing enhanced maintainability and extensibility.

## Version History

### 4.0.0
- **Modular Python Architecture**: Complete rewrite with clean module separation
- **Enhanced Cache Management**: Intelligent caching with 95%+ efficiency
- **Improved Error Handling**: Robust downloading and parsing
- **Better Logging**: Detailed statistics and debugging information
- **Platform Auto-detection**: Smart directory configuration
- **Full Backward Compatibility**: Works with existing configurations and cache
