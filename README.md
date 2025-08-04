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
tv_grab_gracenote2epg --capabilities

# Download 7 days of guide data (XML to stdout, logs to file)
tv_grab_gracenote2epg --days 7 --zip 92101

# With console logging (logs to stderr + file)
tv_grab_gracenote2epg --days 7 --zip 92101 --console

# Use Canadian postal code
tv_grab_gracenote2epg --days 3 --postal J3B1M4 --warning --console
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
tv_grab_gracenote2epg --days 7 --zip 92101

# With console output: XML to stdout, logs to stderr + file
tv_grab_gracenote2epg --days 7 --zip 92101 --console

# Save XML to custom file instead of stdout
tv_grab_gracenote2epg --days 7 --zip 92101 --output guide.xml

# Custom file with console logs visible
tv_grab_gracenote2epg --days 7 --zip 92101 --output guide.xml --console
```

**Note**: When using `--output filename`, the XML is written to the specified file instead of stdout, and the default cache/xmltv.xml is replaced by your custom filename.

### Complete Examples with Logging Levels:

```bash
# Default logging: INFO+WARNING+ERROR to file, XML to stdout
tv_grab_gracenote2epg --days 7 --zip 92101

# Console output: same logs to stderr + file, XML to stdout  
tv_grab_gracenote2epg --days 7 --zip 92101 --console

# Warnings only: WARNING+ERROR to file, XML to stdout
tv_grab_gracenote2epg --days 7 --zip 92101 --warning

# Warnings with console: WARNING+ERROR to stderr + file
tv_grab_gracenote2epg --days 7 --zip 92101 --warning --console

# Debug mode: ALL logs to file, XML to stdout
tv_grab_gracenote2epg --days 7 --zip 92101 --debug

# Debug with console: ALL logs to stderr + file (very verbose)
tv_grab_gracenote2epg --days 7 --zip 92101 --debug --console
```

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
<setting id="refresh">48</setting>      <!-- Cache refresh window (hours) -->
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
tv_grab_gracenote2epg --description       # Show grabber description
tv_grab_gracenote2epg --version          # Show version
tv_grab_gracenote2epg --capabilities     # Show capabilities
```

### Logging Control

```bash
tv_grab_gracenote2epg --quiet            # File logging only (explicit)
tv_grab_gracenote2epg --warning          # Only warnings/errors to file
tv_grab_gracenote2epg --debug            # All debug info to file
tv_grab_gracenote2epg --console          # Display logs on stderr too
```

### Guide Parameters

```bash
tv_grab_gracenote2epg --days 7           # Number of days (1-14)
tv_grab_gracenote2epg --offset 1         # Start tomorrow instead of today
tv_grab_gracenote2epg --output guide.xml # Save XML to file (replaces default cache/xmltv.xml)
tv_grab_gracenote2epg --langdetect true  # Enable automatic language detection
tv_grab_gracenote2epg --langdetect false # Disable language detection (all English)
tv_grab_gracenote2epg --refresh 24       # Refresh first 24 hours (default: 48)
tv_grab_gracenote2epg --norefresh        # Use all cached data (fastest)
```

### Location Codes

```bash
tv_grab_gracenote2epg --zip 92101        # US ZIP code
tv_grab_gracenote2epg --postal J3B1M4    # Canadian postal code
tv_grab_gracenote2epg --code 90210       # Generic location code
```

### Configuration

```bash
tv_grab_gracenote2epg --config-file /path/to/config.xml  # Custom config file
tv_grab_gracenote2epg --basedir /path/to/basedir         # Custom base directory
```

## Migration from Other EPG Grabbers

When migrating from other EPG grabber modules (such as `tv_grab_zap2epg` or other XMLTV grabbers), you must **completely reset the EPG database** to avoid conflicts and silent data rejection.

### ⚠️ **Important: EPG Database Conflicts**

TVheadend's EPG database can have conflicts when switching between different grabbers, causing **silent rejection** of program data. Even if the XML format is correct, TVheadend may accept channels but reject all programs without error messages.

**Symptoms of EPG conflicts:**
```
[INFO]:xmltv: grab took 280 seconds
[INFO]:xmltv: parse took 0 seconds  
[INFO]:xmltv: channels   tot=   33 new=    0 mod=    0  ← Channels OK
[INFO]:xmltv: episodes   tot=    0 new=    0 mod=    0  ← No programs!
[INFO]:xmltv: broadcasts tot=    0 new=    0 mod=    0  ← No programs!
```

### 🛠️ **Complete Migration Procedure**

Follow these steps **exactly** for a successful migration:

#### **Step 1: Configure EPG Grabbers**
1. **TVheadend Web Interface** → **Configuration** → **Channel/EPG** → **EPG Grabber Modules**
2. **Enable**: `tv_grab_gracenote2epg` ✅
3. **Disable**: All other grabbers (especially `tv_grab_zap2epg`) ❌
4. **Save Configuration**

#### **Step 2: Stop TVheadend**
```bash
# Synology DSM7
sudo synopkg stop tvheadend

# Standard Linux
sudo systemctl stop tvheadend

# Wait for complete shutdown
sleep 5
```

#### **Step 3: Clean EPG Database and Cache**
```bash
# Synology DSM7 paths
sudo rm -f /var/packages/tvheadend/var/epgdb.v3
sudo rm -rf /var/packages/tvheadend/var/epggrab/xmltv/channels/*

# Synology DSM6 paths  
sudo rm -f /var/packages/tvheadend/target/var/epgdb.v3
sudo rm -rf /var/packages/tvheadend/target/var/epggrab/xmltv/channels/*

# Standard Linux paths
sudo rm -f /home/hts/.hts/tvheadend/epgdb.v3
sudo rm -rf /home/hts/.hts/tvheadend/epggrab/xmltv/channels/*
```

#### **Step 4: Start TVheadend**
```bash
# Synology DSM7
sudo synopkg start tvheadend

# Standard Linux  
sudo systemctl start tvheadend
```

#### **Step 5: Wait for First Pass (Channels Detection)**
- **Wait 2-5 minutes** after TVheadend startup
- First grabber run will detect **channels only**:

```
[INFO]:xmltv: grab took 280 seconds
[INFO]:xmltv: channels   tot=   33 new=   33 mod=   33  ← Channels detected ✅
[INFO]:xmltv: episodes   tot=    0 new=    0 mod=    0  ← No programs yet (normal)
[INFO]:xmltv: broadcasts tot=    0 new=    0 mod=    0  ← No programs yet (normal)
[INFO]:xmltv: scheduling save epg timer
```

- **Wait for EPG database save**:
```
[INFO]:epgdb: snapshot start
[INFO]:epgdb: save start  
[INFO]:epgdb: stored (size 79)  ← Small size = channels only
```

#### **Step 6: Manual Re-run for Program Data**
1. **TVheadend Web Interface** → **Configuration** → **Channel/EPG** → **EPG Grabber Modules**
2. Click **"Re-run internal EPG grabbers"** 
3. **Wait 5-10 minutes** for complete download

#### **Step 7: Verify Success**
Second run should show **full program data**:

```
[INFO]:xmltv: grab took 283 seconds
[INFO]:xmltv: parse took 2 seconds
[INFO]:xmltv: channels   tot=   33 new=    0 mod=    0  ← Channels stable
[INFO]:xmltv: seasons    tot=15249 new=15005 mod=  244  ← Programs detected ✅
[INFO]:xmltv: episodes   tot=11962 new=11810 mod=  152  ← Episodes detected ✅  
[INFO]:xmltv: broadcasts tot=15682 new=15434 mod=  248  ← Broadcasts detected ✅
```

- **Large EPG database save**:
```
[INFO]:epgdb: queued to save (size 9816663)  ← Large size = full data ✅
[INFO]:epgdb:   broadcasts 15244             ← Programs saved ✅
[INFO]:epgdb: stored (size 1887624)
```

### ✅ **Migration Complete**

Your EPG should now show:
- **Channel listings** with proper names and numbers
- **Program information** with descriptions, times, and metadata  
- **Extended details** (if enabled): cast, ratings, episode info
- **Multi-language support** with proper translations

### 🚨 **Troubleshooting Migration Issues**

**Problem**: Channels detected but no programs after re-run
- **Solution**: Repeat Step 3 (database cleanup) and try again
- **Cause**: Residual conflicts from previous grabber

**Problem**: No channels detected at all  
- **Solution**: Check `gracenote2epg.xml` configuration
- **Verify**: TVheadend integration settings (`tvhurl`, `tvhport`)

**Problem**: Some channels missing
- **Solution**: Check TVheadend channel configuration
- **Verify**: Enabled channels in TVheadend match your lineup

**Problem**: Extended details not showing
- **Solution**: Verify `xdetails=true` and `xdesc=true` in configuration
- **Note**: First run downloads 1000+ series details (normal delay)

### 📝 **Why This Process is Necessary**

1. **Database Schema Differences**: Different grabbers may use incompatible data structures
2. **Channel ID Conflicts**: IDs like `45867.zap2epg` vs `45867.gracenote2epg` cause conflicts  
3. **Timestamp Format Issues**: Different time formats can cause silent rejection
4. **Cache Corruption**: Mixed cache data from different sources
5. **TVheadend Logic**: TVheadend requires clean state for proper grabber switching

### 🔄 **Switching Back to Previous Grabber**

If you need to switch back to your previous grabber:
1. **Repeat the entire procedure** with the previous grabber enabled
2. **Always clean EPG database** when switching grabbers
3. **Never run multiple XMLTV grabbers** simultaneously

**Remember**: Always perform a **complete EPG reset** when changing grabbers to ensure proper data ingestion.

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
4. **Update scripts**: Replace `tv_grab_zap2epg` calls with `tv_grab_gracenote2epg`
5. **Test functionality**: Run with `--console` to verify operation

### Compatibility

- ✅ **Configuration Files**: 100% compatible with zap2epg.xml format
- ✅ **Cache Files**: Reuses existing zap2epg cache structure
- ✅ **XMLTV Output**: Identical format to original
- ✅ **TVheadend Integration**: Same API and behavior as original zap2epg
- ✅ **Command-line Arguments**: Enhanced interface with new logging options

## Troubleshooting

### XMLTV Validation

To validate the generated XMLTV file against the standard DTD:

```bash
# Validate XMLTV output
xmllint --noout --dtdvalid /usr/share/xmltv/xmltv.dtd xmltv.xml

# If xmltv.dtd is not available, download it
wget http://xmltv.cvs.sourceforge.net/viewvc/*checkout*/xmltv/xmltv/xmltv.dtd
xmllint --noout --dtdvalid xmltv.dtd xmltv.xml
```

**Expected DTD Validation Result:**
The XMLTV output is mostly DTD-compliant except for one intentional extension:

```xml
<credits>
    <actor role="Max Perkins" src="https://zap2it.tmsimg.com/assets/71352_v9_bb.jpg">Colin Firth</actor>
    <actor role="Thomas Wolfe" src="https://zap2it.tmsimg.com/assets/71369_v9_bb.jpg">Jude Law</actor>
</credits>
```

**Note**: The `src=` attribute in actor tags is **not part of the strict XMLTV DTD** but can be used by XMLTV consumers for displaying actor photos. This extension provides enhanced program information without breaking XMLTV parsing.

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
tv_grab_gracenote2epg --debug --console --days 1 --zip 92101
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

### 1.1 - Current Release
- **Progress Tracking**: Real-time progress indicators for long operations
- **Migration Documentation**: Complete migration guide from other EPG grabbers
- **Directory Permissions Fix**: Create directories with proper 755 permissions instead of 777
- **Enhanced Synology Detection**: Improved system detection for DSM6/DSM7 path selection
- **Extended Details Improvements**: Better handling and corrections for xdetails and xdesc configuration
- **Strict XMLTV DTD Compliance**: Full DTD compliance except for actor photo `src=` attribute extension
- **XMLTV Generation Progress**: Percentage progress indicators during XML generation (especially useful for langdetect operations)
- **Download Progress Counters**: Added "x/y" counters for extended details downloads to show remaining downloads
- **Cache Refresh Options**: New `--refresh X` and `--norefresh` command-line options for flexible cache management
- **Configuration Version 4**: Updated configuration schema to support new refresh options

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
