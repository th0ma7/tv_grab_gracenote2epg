# TVheadend Integration Guide

This guide covers complete TVheadend integration for gracenote2epg, including migration from other EPG grabbers and troubleshooting.

## 📺 TVheadend EPG Grabber Configuration

### Initial Setup

1. **Access TVheadend Web Interface** (usually http://your-server:9981)
2. **Navigate**: Configuration → Channel/EPG → EPG Grabber Modules  
3. **Enable gracenote2epg**: 
   - Find `tv_grab_gracenote2epg` in the list
   - Check ✅ **Enabled**
   - Set appropriate **Interval** (recommended: every 4-12 hours)
4. **Save Configuration**

### TVheadend Integration Settings

Configure gracenote2epg for optimal TVheadend integration:

```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <!-- Basic guide settings -->
  <setting id="zipcode">92101</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">7</setting>

  <!-- TVheadend integration -->
  <setting id="tvhoff">true</setting>                 <!-- Enable TVH integration -->
  <setting id="tvhurl">127.0.0.1</setting>           <!-- TVH server IP -->
  <setting id="tvhport">9981</setting>               <!-- TVH port -->
  <setting id="tvhmatch">true</setting>              <!-- Use TVH channel filtering -->
  <setting id="chmatch">true</setting>               <!-- Channel number matching -->
  
  <!-- Optional: TVH authentication -->
  <setting id="usern"></setting>                     <!-- TVH username -->
  <setting id="passw"></setting>                     <!-- TVH password -->
</settings>
```

## 🔄 Migrating EPG Grabbers in TVheadend

### Step 1: Disable Old EPG Grabber

> **💡 Philosophy**: Most EPG grabber migrations work smoothly without special procedures.

1. **TVheadend Web Interface** → **Configuration** → **Channel/EPG** → **EPG Grabber Modules**
2. **Find old grabber** (e.g., `tv_grab_zap2epg`)
3. **Uncheck ❌ Enabled**
4. **Save Configuration**

### Step 2: Enable gracenote2epg

1. **Find `tv_grab_gracenote2epg`** in the EPG grabber list
2. **Check ✅ Enabled**
3. **Configure interval** (e.g., "Every 6 hours")
4. **Save Configuration**

### Step 3: Test Migration

#### Option A: Wait for Next Scheduled Update
- **Normal behavior**: TVheadend will run gracenote2epg at next scheduled interval
- **Typical wait**: 1-6 hours depending on your interval setting

#### Option B: Manual Trigger (Recommended for Testing)
1. **Click "Re-run internal EPG grabbers"** in EPG Grabber Modules
2. **Monitor progress** in TVheadend logs
3. **Wait 5-15 minutes** for completion

### Step 4: Verify Success

**Check TVheadend logs** for success indicators:

#### ✅ **Successful Migration**
```
[INFO]:xmltv: grab took 283 seconds
[INFO]:xmltv: parse took 2 seconds  
[INFO]:xmltv: channels   tot=   33 new=    0 mod=    0  ← Channels detected
[INFO]:xmltv: seasons    tot=15249 new=15005 mod=  244  ← Series data ✅
[INFO]:xmltv: episodes   tot=11962 new=11810 mod=  152  ← Episodes ✅
[INFO]:xmltv: broadcasts tot=15682 new=15434 mod=  248  ← Programs ✅
```

#### ❌ **Migration Problems - Troubleshooting Needed**
```
[INFO]:xmltv: grab took 280 seconds
[INFO]:xmltv: parse took 0 seconds  
[INFO]:xmltv: channels   tot=   33 new=    0 mod=    0  ← Channels OK
[INFO]:xmltv: episodes   tot=    0 new=    0 mod=    0  ← No programs! ❌
[INFO]:xmltv: broadcasts tot=    0 new=    0 mod=    0  ← No programs! ❌
```

**If you see the problem pattern above**, proceed to [EPG Database Troubleshooting](#epg-database-troubleshooting).

## 🔧 EPG Database Troubleshooting

### When EPG Database Reset is Required

⚠️ **Use this procedure ONLY if you experience these symptoms:**

1. **Channels appear but no programs** after grabber migration
2. **Silent data rejection**: XMLTV is valid but TVheadend rejects program data
3. **Zero episodes/broadcasts** in logs despite successful grabber run
4. **Corrupted or incomplete program data** in TVheadend interface

### EPG Database Reset Procedure

> **⚠️ Important**: This procedure deletes all EPG data and requires complete re-download.

#### Step 1: Stop TVheadend Service

```bash
# Synology DSM7
sudo synopkg stop tvheadend

# Synology DSM6  
sudo systemctl stop tvheadend

# Standard Linux
sudo systemctl stop tvheadend

# Docker container
docker stop tvheadend_container_name
```

#### Step 2: Clean EPG Database and Cache

```bash
# Synology DSM7
sudo rm -f /var/packages/tvheadend/var/epgdb.v3
sudo rm -rf /var/packages/tvheadend/var/epggrab/xmltv/channels/*

# Synology DSM6
sudo rm -f /var/packages/tvheadend/target/var/epgdb.v3  
sudo rm -rf /var/packages/tvheadend/target/var/epggrab/xmltv/channels/*

# Standard Linux (adjust paths for your installation)
sudo rm -f /home/hts/.hts/tvheadend/epgdb.v3
sudo rm -rf /home/hts/.hts/tvheadend/epggrab/xmltv/channels/*

# Docker (adjust volume paths as needed)
docker exec tvheadend_container rm -f /config/epgdb.v3
docker exec tvheadend_container rm -rf /config/epggrab/xmltv/channels/*
```

#### Step 3: Start TVheadend Service

```bash
# Synology DSM7
sudo synopkg start tvheadend

# Standard Linux
sudo systemctl start tvheadend

# Docker
docker start tvheadend_container_name
```

#### Step 4: Wait for Channel Detection

- **Wait 2-5 minutes** after TVheadend startup
- **First run detects channels only** (this is normal):

```
[INFO]:xmltv: grab took 280 seconds
[INFO]:xmltv: channels   tot=   33 new=   33 mod=   33  ← Channels ✅
[INFO]:xmltv: episodes   tot=    0 new=    0 mod=    0  ← No programs (normal)
[INFO]:xmltv: broadcasts tot=    0 new=    0 mod=    0  ← No programs (normal)
```

- **Wait for EPG database save**:
```
[INFO]:epgdb: snapshot start
[INFO]:epgdb: save start  
[INFO]:epgdb: stored (size 79)  ← Small size = channels only
```

#### Step 5: Trigger Program Data Download

1. **TVheadend Web Interface** → **Configuration** → **Channel/EPG** → **EPG Grabber Modules**
2. **Click "Re-run internal EPG grabbers"**
3. **Wait 10-15 minutes** for complete download

#### Step 6: Verify Complete Success

**Second run should show full program data**:

```
[INFO]:xmltv: grab took 283 seconds
[INFO]:xmltv: parse took 2 seconds
[INFO]:xmltv: channels   tot=   33 new=    0 mod=    0  ← Channels stable
[INFO]:xmltv: seasons    tot=15249 new=15005 mod=  244  ← Series ✅
[INFO]:xmltv: episodes   tot=11962 new=11810 mod=  152  ← Episodes ✅
[INFO]:xmltv: broadcasts tot=15682 new=15434 mod=  248  ← Programs ✅
```

**Large EPG database save confirms success**:
```
[INFO]:epgdb: queued to save (size 9816663)  ← Large size = full data ✅
[INFO]:epgdb:   broadcasts 15244             ← Programs saved ✅
[INFO]:epgdb: stored (size 1887624)
```

## 📊 TVheadend-Specific Monitoring

### Log File Locations

```bash
# Synology DSM7
tail -f /var/packages/tvheadend/var/log/tvheadend.log

# Synology DSM6
tail -f /var/packages/tvheadend/target/var/log/tvheadend.log

# Standard Linux
tail -f /var/log/tvheadend/tvheadend.log
# OR
journalctl -f -u tvheadend

# Docker
docker logs -f tvheadend_container_name
```

### Key Log Patterns to Monitor

#### Successful EPG Update
```
[INFO]:epggrab: grabber tv_grab_gracenote2epg started
[INFO]:xmltv: grab took 283 seconds
[INFO]:xmltv: parse took 2 seconds
[INFO]:xmltv: broadcasts tot=15682 new=15434 mod=248
[INFO]:epgdb: queued to save
```

#### Channel Filtering Working
```
[DEBUG]:xmltv: channel 'NBC-HD' found
[DEBUG]:xmltv: channel 'NBC-HD' enabled, processing
```

#### EPG Database Issues
```
[WARNING]:xmltv: failed to parse
[ERROR]:epggrab: no data received
[INFO]:xmltv: episodes tot=0 new=0 mod=0  ← Problem indicator
```

## 🎛️ Channel Configuration

### Channel Mapping and Filtering

When `tvhmatch=true`, gracenote2epg only processes channels that exist in TVheadend:

1. **Automatic filtering**: Only downloads EPG for channels you've configured
2. **Bandwidth savings**: Skips unused channels
3. **Faster processing**: Reduced XMLTV file size

### Channel Number Matching

When `chmatch=true`, gracenote2epg applies intelligent channel matching:

```
Lineup Channel: "5" → TVheadend Channel: "5.1" ✅ Match
Lineup Channel: "NBC" → TVheadend Channel: "NBC-HD" ✅ Match  
Lineup Channel: "Discovery" → TVheadend Channel: "DISC" ✅ Match
```

### Manual Channel Configuration

If automatic matching doesn't work:

1. **TVheadend Web Interface** → **Configuration** → **Channel/EPG** → **Channels**
2. **Find problematic channel**
3. **Set EPG Source** → **XMLTV**
4. **Set XMLTV channel name** to match gracenote2epg output
5. **Save configuration**

## 🔍 Advanced TVheadend Troubleshooting

### No EPG Data in TVheadend Interface

#### Check 1: EPG Grabber Status
```bash
# Check if gracenote2epg runs successfully
grep "tv_grab_gracenote2epg" /path/to/tvheadend.log | tail -10
```

#### Check 2: XMLTV File Content
```bash
# Check if XMLTV file exists and has reasonable size
ls -lh ~/gracenote2epg/cache/xmltv.xml

# Quick content check (should show programs)
grep -c "programme start=" ~/gracenote2epg/cache/xmltv.xml

# Check for recent program data
head -20 ~/gracenote2epg/cache/xmltv.xml | grep -E "(generator|programme)"
```

#### Check 3: Channel Matching Issues
```bash
# Debug channel matching
tv_grab_gracenote2epg --debug --console --days 1 | grep -i "channel"

# Compare with TVheadend channels
curl -s "http://127.0.0.1:9981/api/channel/grid" | jq '.entries[].val.name'
```

### Performance Issues in TVheadend

#### High Memory Usage During EPG Update
```xml
<!-- Reduce gracenote2epg resource usage -->
<setting id="days">3</setting>              <!-- Shorter guide period -->
<setting id="refresh">12</setting>          <!-- More aggressive caching -->
<setting id="redays">3</setting>           <!-- Smaller cache -->
```

#### Long EPG Update Times
1. **Check cache efficiency**: Should be 95%+ after first run
2. **Monitor network**: WAF delays are normal and handled automatically
3. **Verify lineup size**: Large lineups take longer

### TVheadend Authentication Issues

If TVheadend requires authentication:

```xml
<setting id="usern">your_username</setting>
<setting id="passw">your_password</setting>
```

Or configure in TVheadend:
1. **Configuration** → **Access Entries**
2. **Add entry** for gracenote2epg access
3. **Allow EPG grabber access** without authentication

## 🔄 Rollback Procedures

### Simple Rollback (Try First)

If you need to return to your previous EPG grabber:

1. **Disable gracenote2epg** in TVheadend EPG grabber modules
2. **Enable previous grabber** (e.g., tv_grab_zap2epg)  
3. **Wait for next EPG update** or manually trigger
4. **Monitor logs** for successful program data

### Full Rollback with Database Reset

If simple rollback doesn't work:

1. **Follow EPG Database Reset Procedure** (Steps 1-3 above)
2. **Enable previous grabber** instead of gracenote2epg
3. **Complete reset verification** (Steps 4-6)

## 📚 Related Documentation

- **[Installation Guide](installation.md)** - Installing gracenote2epg software
- **[Configuration Guide](configuration.md)** - Detailed configuration options
- **[General Troubleshooting](troubleshooting.md)** - Non-TVheadend issues
- **[Cache Configuration](cache-retention.md)** - Optimizing performance

## 🆘 Getting Help

For TVheadend-specific issues:

1. **Enable debug logging**: `tv_grab_gracenote2epg --debug --console`
2. **Collect TVheadend logs**: Include relevant log sections in reports
3. **Test outside TVheadend**: Verify gracenote2epg works independently
4. **[Report issues](https://github.com/th0ma7/gracenote2epg/issues)** with:
   - TVheadend version and platform
   - Complete debug output
   - TVheadend log excerpts
   - Your gracenote2epg configuration (remove passwords)
