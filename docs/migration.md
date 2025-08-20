# Migration Guide

This guide covers migrating to gracenote2epg from other EPG grabbers, with special focus on TVheadend integration.

## ⚠️ Important: EPG Database Reset Required

When migrating from other EPG grabber modules, you **must completely reset the EPG database** to avoid conflicts and silent data rejection.

### Why Reset is Necessary

TVheadend's EPG database can have conflicts when switching between different grabbers, causing **silent rejection** of program data. Even if the XML format is correct, TVheadend may accept channels but reject all programs without error messages.

**Symptoms of EPG conflicts:**
```
[INFO]:xmltv: grab took 280 seconds
[INFO]:xmltv: parse took 0 seconds  
[INFO]:xmltv: channels   tot=   33 new=    0 mod=    0  ← Channels OK
[INFO]:xmltv: episodes   tot=    0 new=    0 mod=    0  ← No programs!
[INFO]:xmltv: broadcasts tot=    0 new=    0 mod=    0  ← No programs!
```

## Migration from tv_grab_zap2epg

### Step-by-Step Migration Procedure

#### **Step 1: Install gracenote2epg**
```bash
# Install with full features
pip install gracenote2epg[full]

# Verify installation
tv_grab_gracenote2epg --capabilities
```

#### **Step 2: Configure EPG Grabbers**
1. **TVheadend Web Interface** → **Configuration** → **Channel/EPG** → **EPG Grabber Modules**
2. **Enable**: `tv_grab_gracenote2epg` ✅
3. **Disable**: `tv_grab_zap2epg` and all other grabbers ❌
4. **Save Configuration**

#### **Step 3: Stop TVheadend**
```bash
# Synology DSM7
sudo synopkg stop tvheadend

# Synology DSM6
sudo systemctl stop tvheadend

# Standard Linux
sudo systemctl stop tvheadend

# Docker
docker stop tvheadend
```

#### **Step 4: Clean EPG Database and Cache**
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

# Docker (adjust volume paths as needed)
docker exec tvheadend rm -f /config/epgdb.v3
docker exec tvheadend rm -rf /config/epggrab/xmltv/channels/*
```

#### **Step 5: Start TVheadend**
```bash
# Synology DSM7
sudo synopkg start tvheadend

# Standard Linux  
sudo systemctl start tvheadend

# Docker
docker start tvheadend
```

#### **Step 6: Wait for First Pass (Channels Detection)**
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

#### **Step 7: Manual Re-run for Program Data**
1. **TVheadend Web Interface** → **Configuration** → **Channel/EPG** → **EPG Grabber Modules**
2. Click **"Re-run internal EPG grabbers"** 
3. **Wait 5-10 minutes** for complete download

#### **Step 8: Verify Success**
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

## Migration from Other XMLTV Grabbers

The same procedure applies when migrating from any other XMLTV grabber:

### Supported Grabbers
- `tv_grab_zap2epg`
- `tv_grab_zap2xml`
- `tv_grab_sd_json`
- `tv_grab_hdhomerun`
- Any other XMLTV-compatible grabber

### Key Points
1. **Always clean EPG database** when switching grabbers
2. **Never run multiple XMLTV grabbers** simultaneously
3. **Complete the full reset procedure** - partial resets don't work
4. **Wait for two complete cycles** before verifying success

## Configuration Migration

### From zap2epg Configuration

gracenote2epg is designed to be backward compatible with zap2epg configurations:

```xml
<!-- Old zap2epg format (still works) -->
<setting id="auto_lineup">true</setting>
<setting id="lineupcode">OTA</setting>
<setting id="lineup">CAN-OTAJ3B1M4</setting>
<setting id="device">-</setting>

<!-- New gracenote2epg format (recommended) -->
<setting id="lineupid">auto</setting>
```

### Automatic Migration
- Old settings are automatically migrated to new format
- Backup of old configuration is created
- New unified cache and retention policies are applied

### Manual Configuration Update
If you prefer to update manually:

```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <!-- Basic guide settings -->
  <setting id="zipcode">92101</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">7</setting>
  
  <!-- Enhanced features -->
  <setting id="xdetails">true</setting>
  <setting id="xdesc">true</setting>
  <setting id="langdetect">true</setting>
  
  <!-- Cache and retention policies -->
  <setting id="redays">7</setting>
  <setting id="refresh">48</setting>
  <setting id="logrotate">true</setting>
  <setting id="relogs">30</setting>
  <setting id="rexmltv">7</setting>
</settings>
```

## Verification Steps

### 1. Check Channel List
```bash
# Verify channels are appearing
grep "channel id=" /path/to/xmltv.xml | head -10
```

### 2. Check Program Data
```bash
# Verify programs exist
grep "programme start=" /path/to/xmltv.xml | head -5
```

### 3. Check File Size
```bash
# XMLTV file should be substantial (several MB)
ls -lh /path/to/xmltv.xml
```

### 4. TVheadend Verification
- **Check channel count** in TVheadend interface
- **Verify EPG data** appears in channel list
- **Test program information** by clicking on programs

## Common Migration Issues

### Issue: Channels detected but no programs after re-run
**Solution**: Repeat the EPG database cleanup procedure

### Issue: Old grabber still running
**Solution**: 
1. Completely disable old grabber in TVheadend
2. Verify only gracenote2epg is enabled
3. Restart TVheadend service

### Issue: Configuration conflicts
**Solution**:
1. Remove old configuration files
2. Let gracenote2epg create new default configuration
3. Migrate settings manually if needed

### Issue: Permission problems
**Solution**:
```bash
# Fix permissions for TVheadend user
sudo chown -R hts:hts /path/to/tvheadend/config/
sudo chmod -R 755 /path/to/tvheadend/config/
```

## Switching Back to Previous Grabber

If you need to switch back to your previous grabber:

1. **Repeat the entire EPG reset procedure** with the previous grabber enabled
2. **Always clean EPG database** when switching grabbers  
3. **Never run multiple XMLTV grabbers** simultaneously

## Performance Comparison

### Expected Improvements with gracenote2epg

| Feature | zap2epg | gracenote2epg |
|---------|---------|---------------|
| **Cache Efficiency** | Basic | 95%+ intelligent caching |
| **Language Detection** | None | Automatic FR/EN/ES |
| **Categories** | Basic | Translated categories |
| **Extended Details** | Limited | Full series descriptions |
| **Log Management** | Basic | Unified retention policies |
| **Configuration** | Complex | Simplified lineup setup |

### Typical Performance
- **First run**: ~10-15 minutes (downloading everything)
- **Subsequent runs**: ~2-3 minutes (cache efficiency)
- **Memory usage**: ~50-100MB during operation
- **Disk usage**: ~10-50MB cache (configurable)

## Getting Help

If you encounter issues during migration:

1. **[Check troubleshooting guide](troubleshooting.md)**
2. **Enable debug logging**: `tv_grab_gracenote2epg --debug --console`
3. **Test lineup detection**: `tv_grab_gracenote2epg --show-lineup --zip YOUR_CODE`
4. **[Report issues](https://github.com/th0ma7/gracenote2epg/issues)** with complete logs

## Next Steps

After successful migration:

1. **[Configure advanced features](configuration.md)** - Enable language detection, extended details
2. **[Optimize cache settings](cache-retention.md)** - Tune cache and retention policies  
3. **[Set up monitoring](log-rotation.md)** - Configure log rotation and monitoring
