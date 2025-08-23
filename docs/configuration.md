# Configuration Guide

This guide covers all configuration options for gracenote2epg. The script auto-creates a default configuration file on first run.

## Configuration File Locations

gracenote2epg auto-detects your system and uses appropriate directories:

### Linux/Docker
- **Config**: `~/gracenote2epg/conf/gracenote2epg.xml`

### Raspberry Pi
- **Config**: `~/script.module.zap2epg/epggrab/conf/gracenote2epg.xml` (if exists)
- **Fallback**: `~/gracenote2epg/conf/gracenote2epg.xml`

### Synology DSM7
- **Config**: `/var/packages/tvheadend/var/epggrab/gracenote2epg/conf/gracenote2epg.xml`

### Synology DSM6
- **Config**: `/var/packages/tvheadend/target/var/epggrab/gracenote2epg/conf/gracenote2epg.xml`

## Complete Configuration Reference

```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <!-- Basic guide settings -->
  <setting id="zipcode">92101</setting>                        <!-- US ZIP or Canadian postal code -->
  <setting id="lineupid">auto</setting>                        <!-- Lineup configuration -->
  <setting id="days">7</setting>                               <!-- Guide duration (1-14 days) -->

  <!-- Station filtering -->
  <setting id="slist"></setting>                               <!-- Comma-separated station IDs (empty=all) -->
  <setting id="stitle">false</setting>                         <!-- Safe titles (replace special chars) -->

  <!-- Extended details and language detection -->
  <setting id="xdetails">true</setting>                        <!-- Download series details + enhanced metadata -->
  <setting id="xdesc">true</setting>                           <!-- Use enhanced descriptions (see below) -->
  <setting id="langdetect">true</setting>                      <!-- Enable automatic language detection -->

  <!-- Display options -->
  <setting id="epgenre">3</setting>                            <!-- Genre mode: 0=none, 1=primary, 2=EIT, 3=all -->
  <setting id="epicon">1</setting>                             <!-- Icon mode: 0=none, 1=series+episode, 2=episode only -->

  <!-- TVheadend integration -->
  <setting id="tvhoff">true</setting>                          <!-- Enable TVH integration -->
  <setting id="tvhurl">127.0.0.1</setting>                     <!-- TVH server IP -->
  <setting id="tvhport">9981</setting>                         <!-- TVH port -->
  <setting id="tvhmatch">true</setting>                        <!-- Use TVH channel filtering -->
  <setting id="chmatch">true</setting>                         <!-- Enable channel number matching -->
  <setting id="usern"></setting>                               <!-- TVH username (optional) -->
  <setting id="passw"></setting>                               <!-- TVH password (optional) -->

  <!-- Cache and retention policies -->
  <setting id="redays">7</setting>                             <!-- Cache retention days (must be >= days) -->
  <setting id="refresh">48</setting>                           <!-- Forced refresh first 48 hours (0=disabled) -->
  <setting id="logrotate">true</setting>                       <!-- Log rotation: true(daily)|false|daily|weekly|monthly -->
  <setting id="relogs">30</setting>                            <!-- Log retention: days(number) or weekly|monthly|quarterly -->
  <setting id="rexmltv">7</setting>                            <!-- XMLTV backup retention: days(number) or weekly|monthly|quarterly -->
</settings>
```

## Required Settings

### zipcode
**Required**: Your location code
- **US**: 5-digit ZIP code (e.g., `92101`)
- **Canada**: Postal code with or without space (e.g., `J3B1M4` or `J3B 1M4`)

```xml
<setting id="zipcode">92101</setting>          <!-- San Diego, CA -->
<setting id="zipcode">J3B1M4</setting>         <!-- Saint-Jean-sur-Richelieu, QC -->
```

## Lineup Configuration

### lineupid
**Simple lineup configuration** - replaces complex multi-parameter setup

**Values**:
- **`auto`** (default) - Auto-detect Over-the-Air lineup (requires valid zipcode)
- **tvtv.com format** - Copy directly from tvtv.com URL (e.g., `CAN-OTAJ3B1M4`)
- **Complete format** - Cable/Satellite provider (e.g., `CAN-0005993-X`)

```xml
<!-- Over-the-Air (antenna) - Auto-detection -->
<setting id="zipcode">92101</setting>
<setting id="lineupid">auto</setting>

<!-- Copy from tvtv.com (auto-normalized to API format) -->
<setting id="lineupid">CAN-OTAJ3B1M4</setting>

<!-- Cable/Satellite provider -->
<setting id="lineupid">CAN-0005993-X</setting>
```

**How to find your lineup**:
1. Visit [tvtv.ca](https://www.tvtv.ca) (Canada) or [tvtv.us](https://www.tvtv.us) (US)
2. Enter your postal/ZIP code
3. **For Over-the-Air**: Click "Broadcast" → "Local Over the Air"
4. **For Cable/Satellite**: Select your provider
5. Copy the lineup ID from the URL (remove the `lu` prefix)

**Test your lineup**:
```bash
tv_grab_gracenote2epg --show-lineup --zip 92101
tv_grab_gracenote2epg --show-lineup --postal J3B1M4 --debug
```

📖 **Detailed guide**: [Lineup Configuration](lineup-configuration.md)

## Core Settings

### days
**Guide duration** (1-14 days)
```xml
<setting id="days">7</setting>         <!-- 7 days of guide data -->
```

### Extended Details

#### xdetails
**Download series details** from the API for enhanced metadata
```xml
<setting id="xdetails">true</setting>  <!-- Enable extended data download -->
```

When enabled:
- Downloads detailed series information from the API
- Adds cast and crew with photos
- Includes original air dates
- Provides enhanced ratings (MPAA system)
- Adds technical details (language, country, video/audio info)
- Enables extended series descriptions (if available)

#### xdesc  
**Description mode and enhancements** - Controls BOTH description (e.g. extended if available) AND additional info (e.g. `• new | live | CC`)
```xml
<setting id="xdesc">true</setting>     <!-- Use enhanced descriptions with additional info -->
<setting id="xdesc">false</setting>    <!-- Use basic descriptions WITHOUT additional info -->
```

When `xdesc=true`:
- Uses extended series descriptions when available (falls back to basic episode description if extended not available)
- **ADDS enhanced info** to descriptions: year, rating, NEW/LIVE/PREMIERE flags, CC/HD tags

When `xdesc=false`:
- Uses basic episode descriptions from the default guide
- **NO additional info added** - descriptions are displayed exactly as received
- Clean, simple descriptions without any enhancements
- Ideal for users who prefer minimal descriptions or when Kodi/Plex adds its own metadata

**Examples of description differences**:

```
xdesc=true:  "A detective investigates a mysterious case. • 2023 | Rated: TV-14 | NEW | CC"
xdesc=false: "A detective investigates a mysterious case."
```

**Interaction with xdetails**:
- `xdetails=false, xdesc=false`: Basic descriptions, no downloads, no enhancements
- `xdetails=false, xdesc=true`: Basic descriptions WITH enhancements (year, flags, etc.)
- `xdetails=true, xdesc=false`: Downloads extended data but uses basic descriptions without enhancements
- `xdetails=true, xdesc=true`: Full functionality - extended descriptions with all enhancements

#### langdetect
**Automatic language detection** (requires `langdetect` library)
```xml
<setting id="langdetect">true</setting> <!-- Auto-detect French/English/Spanish -->
```

When enabled:
- Automatically detects French, English, Spanish content
- Translates categories and terms appropriately
- Applies proper capitalization rules per language
- Uses intelligent caching for performance

**Install language detection**:
```bash
pip install gracenote2epg[full]
# OR
pip install langdetect
```

## Display Options

### epgenre
**Genre/category mode**
```xml
<setting id="epgenre">3</setting>      <!-- All genres -->
```

**Values**:
- `0` - No genres
- `1` - Primary genre only
- `2` - EIT categories  
- `3` - All genres (recommended)

### epicon
**Program icon mode**
```xml
<setting id="epicon">1</setting>       <!-- Series + episode icons -->
```

**Values**:
- `0` - No icons
- `1` - Series + episode icons (recommended)
- `2` - Episode icons only

### stitle
**Safe titles** (replace special characters)
```xml
<setting id="stitle">false</setting>   <!-- Keep original titles -->
```

When `true`: Replaces `\/*?:|` with `_` in episode titles (useful for file systems)

## Station Filtering

### slist
**Explicit station list** (comma-separated station IDs)
```xml
<setting id="slist"></setting>         <!-- Empty = all stations -->
<setting id="slist">12345,67890</setting> <!-- Only specific stations -->
```

When empty: Processes all available stations
When specified: Only processes listed station IDs

## TVheadend Integration

### tvhoff
**Enable TVheadend integration**
```xml
<setting id="tvhoff">true</setting>    <!-- Enable TVH integration -->
```

### Connection Settings
```xml
<setting id="tvhurl">127.0.0.1</setting>   <!-- TVH server IP -->
<setting id="tvhport">9981</setting>       <!-- TVH port -->
<setting id="usern"></setting>             <!-- Username (optional) -->
<setting id="passw"></setting>             <!-- Password (optional) -->
```

### Filtering Options
```xml
<setting id="tvhmatch">true</setting>      <!-- Use TVH channel filtering -->
<setting id="chmatch">true</setting>       <!-- Enable channel number matching -->
```

**tvhmatch**: When enabled, only processes channels that exist in TVheadend
**chmatch**: When enabled, applies intelligent channel number matching (e.g., `5` → `5.1`)

## Cache and Retention Policies

📖 **Detailed guide**: [Cache & Retention Policies](cache-retention.md)

### Cache Settings
```xml
<setting id="redays">7</setting>       <!-- Cache retention days (must be >= days) -->
<setting id="refresh">48</setting>     <!-- Refresh first 48 hours (0=disabled) -->
```

**redays**: How long to keep cached guide blocks
**refresh**: How many hours from now to refresh (0 = use all cached data)

### Log Rotation
```xml
<setting id="logrotate">true</setting> <!-- Enable log rotation -->
<setting id="relogs">30</setting>      <!-- Log retention -->
```

**logrotate values**:
- `true` or `daily` - Rotate daily
- `weekly` - Rotate weekly  
- `monthly` - Rotate monthly
- `false` - No rotation

**relogs values**:
- Number - Days to keep (e.g., `30`)
- `weekly` - Keep for 7 days
- `monthly` - Keep for 30 days
- `quarterly` - Keep for 90 days
- `unlimited` - Never delete

### XMLTV Backup Retention
```xml
<setting id="rexmltv">7</setting>      <!-- XMLTV backup retention -->
```

Same format as `relogs` - controls how long to keep XMLTV backup files.

## Configuration Examples

### Standard Home Setup
```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <!-- Basic guide settings -->
  <setting id="zipcode">92101</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">7</setting>

  <!-- Extended features -->
  <setting id="xdetails">true</setting>
  <setting id="xdesc">true</setting>
  <setting id="langdetect">true</setting>

  <!-- Cache and retention -->
  <setting id="redays">7</setting>
  <setting id="refresh">48</setting>
  <setting id="logrotate">true</setting>
  <setting id="relogs">30</setting>
  <setting id="rexmltv">7</setting>
</settings>
```

### Minimal Descriptions Setup
```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <!-- Basic guide settings -->
  <setting id="zipcode">92101</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">7</setting>

  <!-- Minimal descriptions without enhancements -->
  <setting id="xdetails">false</setting>
  <setting id="xdesc">false</setting>
  <setting id="langdetect">false</setting>

  <!-- Cache and retention -->
  <setting id="redays">7</setting>
  <setting id="refresh">48</setting>
  <setting id="logrotate">true</setting>
  <setting id="relogs">30</setting>
  <setting id="rexmltv">7</setting>
</settings>
```

### High-Volume Server
```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <!-- Extended cache for stability -->
  <setting id="zipcode">90210</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">14</setting>

  <!-- Full features -->
  <setting id="xdetails">true</setting>
  <setting id="xdesc">true</setting>
  <setting id="langdetect">true</setting>
  
  <!-- Cache and retention -->
  <setting id="redays">21</setting>
  <setting id="refresh">24</setting>
  <setting id="logrotate">daily</setting>
  <setting id="relogs">quarterly</setting>
  <setting id="rexmltv">monthly</setting>
</settings>
```

### Resource-Limited System
```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <!-- Minimal resource usage -->
  <setting id="zipcode">J3B1M4</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">3</setting>

  <!-- Basic features only -->
  <setting id="xdetails">false</setting>
  <setting id="xdesc">false</setting>
  <setting id="langdetect">false</setting>
  
  <!-- Cache and retention -->
  <setting id="redays">3</setting>
  <setting id="refresh">12</setting>
  <setting id="logrotate">daily</setting>
  <setting id="relogs">7</setting>
  <setting id="rexmltv">3</setting>
</settings>
```

### Development/Testing
```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <!-- Testing configuration -->
  <setting id="zipcode">92101</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">2</setting>

  <!-- Full debugging -->
  <setting id="xdetails">true</setting>
  <setting id="xdesc">true</setting>
  <setting id="langdetect">true</setting>
  
  <!-- Keep all logs for debugging -->
  <setting id="redays">2</setting>
  <setting id="refresh">0</setting>
  <setting id="logrotate">false</setting>
  <setting id="relogs">unlimited</setting>
  <setting id="rexmltv">unlimited</setting>
</settings>
```

## Command Line Overrides

You can override most configuration options from the command line:

```bash
# Override basic settings
tv_grab_gracenote2epg --days 3 --zip 90210 --lineupid auto

# Override language detection
tv_grab_gracenote2epg --langdetect false --zip 92101

# Override cache settings
tv_grab_gracenote2epg --refresh 24 --zip 92101    # Refresh first 24 hours
tv_grab_gracenote2epg --norefresh --zip 92101     # Use all cached data

# Override output location
tv_grab_gracenote2epg --output custom.xml --zip 92101
```

## Configuration Validation

gracenote2epg validates configuration on startup:

### Common Validation Messages
```
WARNING: redays (5) must be >= days (7), adjusting redays to 7
WARNING: Invalid logrotate value "bad_value", using default "true"
WARNING: Invalid relogs value "invalid", using default "30"
```

### Testing Configuration
```bash
# Test with debug output
tv_grab_gracenote2epg --debug --console --days 1

# Check configuration processing
grep -A 20 "Configuration values processed" ~/gracenote2epg/log/gracenote2epg.log
```

## Configuration Migration

gracenote2epg automatically migrates from older configuration formats:

### Legacy Settings (Automatically Migrated)
```xml
<!-- Old format (still works) -->
<setting id="auto_lineup">true</setting>
<setting id="lineupcode">OTA</setting>
<setting id="lineup">CAN-OTAJ3B1M4</setting>
<setting id="device">-</setting>

<!-- Migrated to new format -->
<setting id="lineupid">auto</setting>
```

### Backup and Migration
- Automatic backup of old configuration created
- Migration messages logged at INFO level
- New configuration format provides cleaner organization

## Advanced Configuration

### Custom Base Directory
```bash
# Use custom directory for all files
tv_grab_gracenote2epg --basedir /custom/path/gracenote2epg
```

### Custom Configuration File
```bash
# Use custom configuration file
tv_grab_gracenote2epg --config-file /path/to/custom.xml
```

### Environment-Specific Configurations

You can maintain multiple configurations for different environments:

```bash
# Production configuration
cp gracenote2epg.xml gracenote2epg-prod.xml

# Testing configuration  
cp gracenote2epg.xml gracenote2epg-test.xml

# Use specific configuration
tv_grab_gracenote2epg --config-file gracenote2epg-test.xml
```

## Next Steps

- **[Test your configuration](troubleshooting.md#testing-setup)**
- **[Configure lineup detection](lineup-configuration.md)**  
- **[Optimize cache settings](cache-retention.md)**
- **[Set up TVheadend integration](migration.md)**
