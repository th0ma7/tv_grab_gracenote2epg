# gracenote2epg - Modular TV Guide Grabber

A modular Python implementation for downloading TV guide data from tvlistings.gracenote.com with intelligent caching and TVheadend integration.

**Originally designed for Kodi/TVheadend integration** - This is a Python rewrite of the original zap2epg grabber.

## Key Features

- **✅ Strict XMLTV DTD Compliance**: Now following strict DTD compliance
- **🧩 Modular Architecture**: Clean separation of concerns for easy maintenance and testing
- **🎬 Kodi/TVheadend Ready**: Originally designed for seamless Kodi and TVheadend integration
- **🌟 Enhanced XMLTV Metadata**: Language, country, video/audio elements with DTD compliance
- **🚀 Language Detection & Caching**: Automated language detection with high cache efficiency
- **🌍 Multilingual Translation**: Automated English/French/Spanish generic details translation
- **🧠 Smart Cache Management**: Preserves existing data and only downloads what's needed
- **⚡ Optimized Guide Refresh**: Refreshes first 48 hours while reusing cached data for later periods
- **📡 Advanced TVheadend Integration**: Automatic channel filtering and matching
- **🎯 Extended Program Details**: Optional enhanced descriptions
- **🛡️ Robust WAF Protection**: Adaptive delays and retry logic with intelligent downloading
- **📝 Built-in Log Rotation**: Intelligent multi-period log management
- **🔧 Platform Agnostic**: Auto-detection for Raspberry Pi, Synology NAS, and standard Linux


**IMPORTANT:** Raspberry Pi setup was not tested - requiring testers to confirm functionality or make any necessary changes.

## Installation

### From PyPI (Recommended)

```bash
# Install basic package
pip install gracenote2epg

# Install with full features (language detection + translations)
pip install gracenote2epg[full]
```

### From Wheel Package

```bash
# Download and install wheel
pip install gracenote2epg-1.4-py3-none-any.whl[full]
```

### From Source Distribution

```bash
# Extract and use directly (no installation required)
tar -xzf gracenote2epg-1.4.tar.gz
cd gracenote2epg-1.4
./tv_grab_gracenote2epg --capabilities

# Or install from source
pip install .
```

### Development Installation

```bash
git clone https://github.com/th0ma7/gracenote2epg.git
cd gracenote2epg
pip install -e .[full]  # Editable install with full features
```

## ⚠️ **Important Installation Notes**

### Package Distribution Types

gracenote2epg is available in two distribution formats:

1. **Wheel Package (.whl)** - For standard `pip install`
   - Creates both `gracenote2epg` and `tv_grab_gracenote2epg` commands
   - Installs in Python site-packages
   - Recommended for most users

2. **Source Distribution (.tar.gz)** - For manual installation
   - Includes `tv_grab_gracenote2epg` wrapper script
   - Works immediately after extraction (no installation required)
   - Useful for systems where pip install isn't preferred

### Command Availability

**After `pip install gracenote2epg`**:
```bash
gracenote2epg --version              # Primary command
tv_grab_gracenote2epg --capabilities # XMLTV standard name
python -m gracenote2epg --version    # Module execution
```

**From source distribution** (extract .tar.gz):
```bash
./tv_grab_gracenote2epg --capabilities # Wrapper script only
python3 -m gracenote2epg --version     # Module execution
```

### Feature Dependencies

- **Basic functionality**: Only requires `requests` (automatically installed)
- **Language detection**: Requires `langdetect` → Install with `[full]` extra
- **Category translations**: Requires `polib` → Install with `[full]` extra

```bash
# Get all features
pip install gracenote2epg[full]
```

## Quick Start

### Available Commands

After installation, gracenote2epg provides multiple command options:

```bash
# XMLTV standard command (recommended for compatibility)
tv_grab_gracenote2epg --capabilities
tv_grab_gracenote2epg --days 7 --zip 92101

# Alternative command name
gracenote2epg --days 7 --zip 92101

# Python module execution (always available)
python -m gracenote2epg --days 7 --zip 92101
```

**From source distribution** (without installation):
```bash
# Only tv_grab_gracenote2epg wrapper available
./tv_grab_gracenote2epg --capabilities
```

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

# Save to custom file
tv_grab_gracenote2epg --days 7 --zip 92101 --output guide.xml
```

### Dependencies Information

**Required**: `requests>=2.25.0`

**Optional (recommended)**:
- `langdetect>=1.0.9` - For automatic French/English/Spanish detection
- `polib>=1.1.0` - For multilingual category translations

Install with `pip install gracenote2epg[full]` to get all optional dependencies.

### Configuration

The script auto-creates a default configuration file on first run:

- **Linux/Docker**: `~/gracenote2epg/conf/gracenote2epg.xml`
- **Raspberry Pi**: `~/script.module.zap2epg/epggrab/conf/gracenote2epg.xml` (if exists)
- **Synology DSM7**: `/var/packages/tvheadend/var/epggrab/gracenote2epg/conf/gracenote2epg.xml`
- **Synology DSM6**: `/var/packages/tvheadend/target/var/epggrab/gracenote2epg/conf/gracenote2epg.xml`

Translation files are automatically managed in:
- **Locales Directory**: `~/gracenote2epg/gracenote2epg/locales/`
  - `fr/LC_MESSAGES/gracenote2epg.po` (French translations)
  - `es/LC_MESSAGES/gracenote2epg.po` (Spanish translations)
  - `gracenote2epg.pot` (Translation template)

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

## **Enhanced XMLTV Metadata**
When `xdetails=true`, additional DTD-compliant elements are included:
- **`<credits>`**: Name, role and image URL of actors
- **`<category>`**: Translated categories per detected language
- **`<language>`**: Full language names (Français, English, Español)
- **`<country>`**: US/CA based on zipcode format
- **`<video>`**: Aspect ratio (4:3 for pre-1960 content, 16:9 modern) + color info
- **`<audio>`**: Stereo detection from program tags

## Language Detection

gracenote2epg features automatic language detection and translation with intelligent caching:

### **Language Caching**
- **Enhanced Performance**: Reuses language detections from previous XMLTV files
- **95-100% Cache Efficiency**: Typical performance with established guides
- **Speed Improvement**: XMLTV generation time reduced from ~15 minutes to ~2-3 minutes

### **Automatic Language Detection**
- **langdetect Library Integration**: Uses statistical language detection for accurate French/English/Spanish identification
- **Configurable**: Can be enabled/disabled via configuration (`langdetect=true/false`) or command line (`--langdetect true/false`)
- **Smart Default**: Automatically enabled if langdetect is installed, disabled otherwise
- **Contextual Application**: Uses description analysis to set language for titles and metadata
- **XMLTV Compliance**: Proper `lang` attributes for all text elements
- **Fallback Behavior**: When disabled, all content is marked as English (no detection errors)

### **Language Statistics**
Runtime statistics show distribution of detected languages when enabled:
```
Language cache loaded: 13234 programs cached
Language cache performance:
  Cache efficiency: 100.0% (4693 hits / 4693 lookups)

Language detection statistics (using langdetect library with cache):
  French: 1424 episodes (35.6%)
  English: 2497 episodes (62.4%)
  Spanish: 81 episodes (2.0%)
```

When disabled:
```
Language detection: Disabled by configuration - defaulting to English
Language detection disabled - all content marked as English
```

## Multilingual Translation

gracenote2epg features automatic category translation with intelligent language detection for French and Spanish.

### **Translation Features**
- **Proper Capitalization**: Per language capitalization
- **Fallback Support**: Categories remain readable even if translation files are unavailable

### **Translation Examples**
```xml
<!-- English program -->
<category lang="en">Comedy Drama</category>
<category lang="en">Books &amp; Literature</category>

<!-- French program -->
<category lang="fr">Comédie dramatique</category>
<category lang="fr">Livres et littérature</category>

<!-- Spanish program -->
<category lang="es">Comedia dramática</category>
<category lang="es">Libros y literatura</category>
```

### **Status Term Translation**
Status terms in enhanced descriptions are also translated:
- **English**: "Rated: PG | NEW | CC"
- **French**: "CLASSÉ: G | NOUVEAU | CC"
- **Spanish**: "CLASIFICADO: PG | NUEVO | CC"

## Log Management

gracenote2epg includes built-in log rotation with intelligent multi-period support:

- **Smart Content Analysis**: Separates complete periods (days/weeks/months) into individual backup files
- **tail -f Compatible**: Uses copytruncate strategy to maintain log monitoring compatibility  
- **Configurable**: Daily, weekly, or monthly rotation with adjustable retention
- **Visible Actions**: Rotation activities are logged with clear reporting

See **[LOG_ROTATION.md](LOG_ROTATION.md)** for detailed configuration and troubleshooting.

## Configuration Options

### Required Settings
```xml
<setting id="zipcode">92101</setting>  <!-- US ZIP or Canadian postal code -->
```

### Simple Lineup Configuration
```xml
<setting id="lineupid">auto</setting>  <!-- Simple lineup configuration -->
```

**Accepted values for `lineupid`:**
- **`auto`** (default) - Auto-detect Over-the-Air lineup
- **`CAN-OTAJ3B1M4`** - Copy directly from tvtv.com (auto-normalized to API format)
- **`CAN-0005993-X`** - Cable/Satellite provider (complete format)

**Examples:**
```xml
<!-- Over-the-Air (antenna) - Default -->
<setting id="lineupid">auto</setting>

<!-- Copy from tvtv.com: Remove 'lu' prefix from URL -->
<setting id="lineupid">CAN-OTAJ3B1M4</setting>

<!-- Cable/Satellite provider (e.g., Videotron) -->
<setting id="lineupid">CAN-0005993-X</setting>
```

**How to find your lineup ID:**
1. Go to [tvtv.ca](https://www.tvtv.ca) (Canada) or [tvtv.us](https://www.tvtv.us) (USA)
2. Enter your postal/ZIP code
3. **For Over-the-Air**: Click "Broadcast" → "Local Over the Air"
4. **For Cable/Satellite**: Select your provider
5. Copy the lineup ID from the URL (remove the `lu` prefix)

📖 **For detailed lineup configuration guide, see [LINEUPID.md](LINEUPID.md)**

### Lineup Testing and Configuration

Before configuring your lineup, you can test the auto-detection with your postal/ZIP code:

```bash
# Test lineup detection (simplified output)
tv_grab_gracenote2epg --show-lineup --zip 92101

# Test with detailed technical information
tv_grab_gracenote2epg --show-lineup --zip 92101 --debug

# Test Canadian postal code
tv_grab_gracenote2epg --show-lineup --postal J3B1M4
```

**Example output (simplified mode):**
```
🌐 GRACENOTE API URL PARAMETERS:
   lineupId=CAN-OTAJ3B1M4-DEFAULT
   country=CAN
   postalCode=J3B1M4

✅ VALIDATION URLs (manual verification):
   Auto-generated: https://www.tvtv.ca/qc/saint-jean-sur-richelieu/j3b1m4/luCAN-OTAJ3B1M4
   Manual lookup:
     1. Go to https://www.tvtv.ca/
     2. Enter postal code: J3B1M4
     3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → URL shows luCAN-OTAJ3B1M4
     3b. For Cable/Sat: Select provider → URL shows luCAN-[ProviderID]-X

🔗 GRACENOTE API URL FOR TESTING:
   https://tvlistings.gracenote.com/api/grid?aid=orbebb&country=CAN&postalCode=J3B1M4&time=1755432000&timespan=3&isOverride=true&userId=-&lineupId=CAN-OTAJ3B1M4-DEFAULT&headendId=lineupId
```

**Debug mode** provides additional technical details including manual download commands, API parameter explanations, and configuration recommendations.

### Core Settings
```xml
<setting id="days">7</setting>          <!-- Guide duration (1-14 days) -->
<setting id="redays">7</setting>        <!-- Cache retention days (match days) -->
<setting id="refresh">48</setting>      <!-- Cache refresh window (hours, 0=disabled) -->
```

### Extended Details with Multi-Language Support
```xml
<setting id="xdetails">true</setting>   <!-- Download series details + enhanced metadata -->
<setting id="xdesc">true</setting>      <!-- Enhanced descriptions with translations -->
<setting id="langdetect">true</setting> <!-- Enable automatic language detection -->
```

### Station and Content Filtering
```xml
<setting id="slist"></setting>          <!-- Comma-separated station IDs (empty=all) -->
<setting id="stitle">false</setting>    <!-- Safe titles (replace special chars) -->
<setting id="epgenre">3</setting>       <!-- Genre mode: 0=none, 1=primary, 2=EIT, 3=all -->
<setting id="epicon">1</setting>        <!-- Icon mode: 0=none, 1=series+episode, 2=episode only -->
```

### TVheadend Integration
```xml
<setting id="tvhoff">true</setting>     <!-- Enable TVH integration -->
<setting id="tvhurl">127.0.0.1</setting> <!-- TVH server IP -->
<setting id="tvhport">9981</setting>    <!-- TVH port -->
<setting id="tvhmatch">true</setting>   <!-- Use TVH channel filtering -->
<setting id="chmatch">true</setting>    <!-- Enable channel number matching -->
<setting id="usern"></setting>          <!-- TVH username (optional) -->
<setting id="passw"></setting>          <!-- TVH password (optional) -->
```

### Log Rotation Settings
```xml
<setting id="logrotate_enabled">true</setting>     <!-- Enable log rotation -->
<setting id="logrotate_interval">weekly</setting>  <!-- daily/weekly/monthly -->
<setting id="logrotate_keep">14</setting>          <!-- Number of backups to keep -->
```

## Performance & Caching

### Cache System

The modular design includes a sophisticated caching system with major performance improvements:

#### Language Detection Cache
- **Smart Reuse**: Extracts language information from previous XMLTV files to avoid redundant langdetect calls
- **Performance Gain**: 95-100% cache efficiency typical, reducing generation time from ~15 minutes to ~2-3 minutes

#### Guide Cache (3-hour blocks)
- **Smart Refresh**: Only refreshes first 48 hours (tunable)
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

#### Log Management
- **Multi-Period Rotation**: Intelligent separation of complete periods into individual backup files
- **Content Analysis**: Analyzes actual log content instead of file timestamps
- **Period Detection**: Automatically identifies daily/weekly/monthly boundaries

### Performance Statistics Example

```
Language cache loaded: 13234 programs cached
Language cache performance:
  Cache efficiency: 100.0% (4693 hits / 4693 lookups)

Extended details processing completed:
  Total unique series: 1137
  Downloads attempted: 45        ← Only new series
  Unique series from cache: 1092 ← Reused existing (96.0% efficiency!)
  Cache efficiency: 96.0% (1092/1137 unique series reused)

Guide download completed:
  Blocks: 56 total (8 downloaded, 48 cached, 0 failed)
  Cache efficiency: 85.7% reused
  Success rate: 100.0%

Log Rotation Report:
  Recent rotation detected - 2 backup files created:
    Created backup: gracenote2epg.log.2025-W31 (5.2 MB) - weekly rotation
    Created backup: gracenote2epg.log.2025-W32 (1.7 MB) - weekly rotation
    Current log: gracenote2epg.log (0.0 MB) - contains current weekly only
  Log rotation completed successfully

Language detection statistics (using langdetect library with cache):
  French: 1424 episodes (35.6%)
  English: 2497 episodes (62.4%)
  Spanish: 81 episodes (2.0%)
```

**Note**: Language statistics only appear when langdetect is enabled and available. With the new cache system, most language detections are reused from previous runs, dramatically improving performance.

## Command-Line Interface

### XMLTV Baseline Capabilities

```bash
tv_grab_gracenote2epg --description      # Show grabber description
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

### 🛠️ **EPG Migration Procedure**

Follow these steps for a successful migration:

#### **Step 1: Configure EPG Grabbers**
1. **TVheadend Web Interface** → **Configuration** → **Channel/EPG** → **EPG Grabber Modules**
2. **Enable**: `tv_grab_gracenote2epg` ✅
3. **Disable**: All other grabbers ❌
4. **Save Configuration**

#### **Step 2: Stop TVheadend**
```bash
# Synology DSM7
sudo synopkg stop tvheadend

# Standard Linux
sudo systemctl stop tvheadend
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
- **Multi-language support** with proper translations and categories

### 🔄 **Switching Back to Previous Grabber**

If you need to switch back to your previous grabber:
1. **Repeat the entire procedure** with the previous grabber enabled
2. **Always clean EPG database** when switching grabbers
3. **Never run multiple XMLTV grabbers** simultaneously

## 🔧 **Troubleshooting**

### Installation Issues

**Problem**: `Command 'gracenote2epg' not found`
- **Solution**: Install with pip: `pip install gracenote2epg`
- **Alternative**: Use module execution: `python -m gracenote2epg`

**Problem**: Language detection not working  
- **Solution**: Install full features: `pip install gracenote2epg[full]`
- **Check**: `python -c "import langdetect; print('OK')"`

**Problem**: Categories not translating
- **Solution**: Install full features: `pip install gracenote2epg[full]`
- **Check**: `python -c "import polib; print('OK')"`

### Configuration Issues

**Problem**: Confused about lineup configuration
- **Solution**: Use `--show-lineup` to test: `tv_grab_gracenote2epg --show-lineup --zip 92101`
- **For OTA**: Just use `<setting id="lineupid">auto</setting>`
- **For Cable/Satellite**: Copy lineup ID from tvtv.com URL (remove `lu` prefix)
- **Documentation**: See [LINEUPID.md](LINEUPID.md) for detailed lineup configuration guide

### TVheadend Issues

**Problem**: Channels detected but no programs after re-run
- **Solution**: Clear EPG database and cache (see Migration section above)

**Problem**: No channels detected at all
- **Solution**: Check `gracenote2epg.xml` configuration
- **Verify**: ZIP/postal code is correct
- **Test**: Use `--show-lineup` to verify lineup detection

**Problem**: Extended details not showing
- **Solution**: Verify `xdetails=true` and `xdesc=true` in configuration
- **Note**: First run downloads 1000+ series details (normal delay)

### Performance Issues

**Problem**: Slow language detection
- **Solution**: Language cache improves performance after first run (95%+ cache efficiency typical)

**Problem**: Extended details downloading too many files
- **Solution**: Cache efficiency improves significantly after first run (96%+ typical)

### Log Issues

**Problem**: Log file growing too large
- **Solution**: Log rotation is enabled by default with weekly rotation and 14-file retention
- **Check**: Verify `logrotate_enabled=true` in configuration

**Problem**: Log rotation not working
- **Solution**: Check rotation messages in log, see [LOG_ROTATION.md](LOG_ROTATION.md) for troubleshooting

For detailed troubleshooting and EPG migration procedures, see the Migration section above.

### XMLTV Validation

To validate the generated XMLTV file against the standard DTD:

```bash
# Validate XMLTV output
xmllint --noout --dtdvalid /usr/share/xmltv/xmltv.dtd xmltv.xml

# If xmltv.dtd is not available, download it
wget http://xmltv.cvs.sourceforge.net/viewvc/*checkout*/xmltv/xmltv/xmltv.dtd
xmllint --noout --dtdvalid xmltv.dtd xmltv.xml
```

**Expected DTD Validation Result:** The XMLTV output is expected to be DTD-compliant.

### Translation Issues

Common translation problems and solutions:

```bash
# Check if polib is installed
python -c "import polib; print('polib available')"

# Verify translation files exist
ls -la ~/gracenote2epg/gracenote2epg/locales/*/LC_MESSAGES/

# Verify category translations are working
grep '<category lang="fr">' cache/xmltv.xml | head -5
grep '<category lang="en">' cache/xmltv.xml | head -5

# Check translation system status in logs
grep "Translation system initialized" log/gracenote2epg.log
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
tv_grab_gracenote2epg --debug --console --days 1 --zip 92101
```

Debug output includes:
- Configuration processing details
- Language detection method and statistics
- Translation system status and loading
- Cache efficiency metrics
- Download statistics and timing
- TVheadend integration status
- Extended details processing
- Log rotation activities

## Development

### For Developers and Contributors

See **[PACKAGING.md](PACKAGING.md)** for the complete development guide covering:
- Building wheel and source distributions
- Comprehensive testing procedures
- Development environment setup
- Version management
- Creating releases

### Project Structure for Development

```bash
tv_grab_gracenote2epg/
├── gracenote2epg/                             # Main package
│   ├── __init__.py
│   ├── gracenote2epg_*.py                     # Individual modules
│   ├── __main__.py                            # Module entry point
│   └── locales/                               # Translation files
│       ├── gracenote2epg.pot                  # Translation template
│       ├── fr/
│       │   └── LC_MESSAGES/
│       │       └── gracenote2epg.po           # French translations
│       └── es/
│           └── LC_MESSAGES/
│               └── gracenote2epg.po           # Spanish translations
├── tv_grab_gracenote2epg                      # Source distribution wrapper
├── setup.py                                   # Installation setup
├── PACKAGING.md                               # Development guide
├── README.md                                  # This file
├── LINEUPID.md                                # Lineup configuration guide
├── CHANGELOG.md                               # Version history and release notes
├── LOG_ROTATION.md                            # Log rotation documentation
├── LICENSE                                    # GPL v3 license
└── gracenote2epg.xml                          # Config template
```

## License

GPL v3 - Same as original script.module.zap2epg project

## Credits & Origins

This project was originally designed to be easily setup in Kodi for use as a grabber for TVheadend. This version builds upon edit4ever's script.module.zap2epg with tv_grab_zap2epg improvements and adds Python modular architecture.

**Original Sources:**
- **edit4ever**: Original **script.module.zap2epg** project (much thanks to @edit4ever)
- **th0ma7**: tv_grab_zap2epg improvements based on PR edit4ever/script.module.zap2epg#37

This modular version builds upon the original zap2epg foundation with enhanced architecture, improved error handling, and modern Python development practices while maintaining compatibility with existing configurations and cache formats.

## Version History

See **[CHANGELOG.md](CHANGELOG.md)** for detailed release notes and version history.
