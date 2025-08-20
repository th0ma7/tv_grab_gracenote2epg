# Troubleshooting Guide

This guide covers common issues and their solutions when using gracenote2epg.

## Quick Diagnostic Commands

### Test Your Setup
```bash
# 1. Check version and capabilities
tv_grab_gracenote2epg --version
tv_grab_gracenote2epg --capabilities

# 2. Test lineup detection  
tv_grab_gracenote2epg --show-lineup --zip YOUR_CODE

# 3. Test basic download with debug info
tv_grab_gracenote2epg --days 1 --zip YOUR_CODE --debug --console

# 4. Check dependencies
python -c "import langdetect; print('Language detection: OK')"
python -c "import polib; print('Translations: OK')"
```

## Installation Issues

### Command Not Found

**Problem**: `Command 'tv_grab_gracenote2epg' not found`

**Solutions**:
```bash
# Solution 1: Install with pip (installs both commands)
pip install gracenote2epg

# Solution 2: Use module execution
python -m gracenote2epg --version

# Solution 3: Check if script is in PATH (for manual installations)
find /usr/local/bin /usr/bin ~/.local/bin -name "tv_grab_gracenote2epg" 2>/dev/null

# Solution 4: Verify installation includes wrapper script
pip show -f gracenote2epg | grep tv_grab_gracenote2epg
```

**Important**: The `tv_grab_gracenote2epg` wrapper script is **essential** for TVheadend integration. If missing:
- TVheadend won't detect the grabber
- XMLTV standard compliance is broken
- Manual re-installation may be required

### Missing Features

**Problem**: Language detection not working
```bash
# Check if langdetect is installed
python -c "import langdetect; print('OK')"
# If error: ModuleNotFoundError: No module named 'langdetect'

# Solution: Install full features
pip install gracenote2epg[full]
```

**Problem**: Categories not translating
```bash
# Check if polib is installed  
python -c "import polib; print('OK')"
# If error: ModuleNotFoundError: No module named 'polib'

# Solution: Install translations
pip install polib
# OR
pip install gracenote2epg[full]
```

### Permission Issues

**Problem**: Permission denied when creating directories
```bash
# Solution 1: Install for user only
pip install --user gracenote2epg[full]

# Solution 2: Use virtual environment
python3 -m venv gracenote_env
source gracenote_env/bin/activate
pip install gracenote2epg[full]

# Solution 3: Fix directory permissions
chmod 755 ~/gracenote2epg/
```

## Configuration Issues

### Lineup Configuration Problems

**Problem**: "Missing required zipcode in configuration"
```bash
# Check current configuration
grep zipcode ~/gracenote2epg/conf/gracenote2epg.xml

# Solution: Add zipcode to configuration or command line
tv_grab_gracenote2epg --zip 92101 --lineupid auto
```

**Problem**: "Inconsistent location codes"
```
ERROR: Inconsistent location codes: lineupid contains 'J3B1M4' but explicit location is '90210'
```
```bash
# Solution: Use consistent location codes
tv_grab_gracenote2epg --lineupid CAN-OTAJ3B1M4 --postal J3B1M4  # ✅ Consistent
tv_grab_gracenote2epg --lineupid CAN-OTAJ3B1M4                   # ✅ Auto-extract
```

**Problem**: Can't find lineup for my area
```bash
# Test lineup detection
tv_grab_gracenote2epg --show-lineup --zip YOUR_CODE

# Check tvtv.com manually
# Canada: https://www.tvtv.ca/
# US: https://www.tvtv.us/
```

### Invalid Configuration Values

**Problem**: Configuration validation errors
```bash
# Check configuration validity
tv_grab_gracenote2epg --debug --console --days 1

# Common fixes:
# days: must be 1-14
# refresh: must be 0-168 hours  
# redays: must be >= days
```

## Download Issues

### Network/Connection Problems

**Problem**: Download failures or timeouts
```bash
# Enable debug to see network details
tv_grab_gracenote2epg --debug --console --days 1

# Check common errors:
# - HTTP 403: WAF blocking (automatic retry with delays)
# - HTTP 404: Invalid lineup ID
# - Timeout: Network issues
```

**Problem**: WAF (Web Application Firewall) blocking
```
WARNING: WAF block detected, backing off 5.2s...
```
```bash
# This is normal - gracenote2epg handles WAF automatically
# - Uses rotating User-Agent headers
# - Implements adaptive delays  
# - Retries with exponential backoff
# Just wait - it will recover automatically
```

**Problem**: No guide data downloaded
```bash
# Check lineup detection first
tv_grab_gracenote2epg --show-lineup --zip YOUR_CODE --debug

# Verify API URL works by copying URL from debug output
# and testing in browser
```

### Cache Issues

**Problem**: Cache not working effectively
```bash
# Check cache directory
ls -la ~/gracenote2epg/cache/

# Check cache configuration
grep -E "(redays|refresh)" ~/gracenote2epg/conf/gracenote2epg.xml

# Solution: Ensure redays >= days
<setting id="days">7</setting>
<setting id="redays">7</setting>    <!-- Must be >= days -->
```

**Problem**: Cache taking too much space
```bash
# Check disk usage
du -sh ~/gracenote2epg/cache/
du -sh ~/gracenote2epg/log/

# Solution: Reduce retention periods
<setting id="redays">2</setting>     <!-- Minimal cache -->
<setting id="relogs">7</setting>     <!-- 1 week logs -->
<setting id="rexmltv">3</setting>    <!-- 3 days XMLTV backups -->
```

## TVheadend Integration Issues

### Channels Detected But No Programs

**Problem**: TVheadend shows channels but no EPG data
```
[INFO]:xmltv: channels   tot=   33 new=    0 mod=    0  ← Channels OK
[INFO]:xmltv: episodes   tot=    0 new=    0 mod=    0  ← No programs!
```

**Solution**: Complete EPG database reset (see [Migration Guide](migration.md))

### Channel Filtering Not Working

**Problem**: Wrong channels or no filtering
```bash
# Check TVheadend connection
grep -E "(tvhoff|tvhurl|tvhport)" ~/gracenote2epg/conf/gracenote2epg.xml

# Test TVheadend access
curl http://127.0.0.1:9981/api/channel/grid

# Enable debug to see filtering details
tv_grab_gracenote2epg --debug --console --days 1
```

### Channel Number Mismatches

**Problem**: Channel numbers don't match TVheadend
```bash
# Enable channel number matching
<setting id="chmatch">true</setting>

# Check debug output for channel matching
tv_grab_gracenote2epg --debug --console --days 1 | grep -i channel
```

## XMLTV Issues

### Invalid XMLTV Output

**Problem**: XMLTV fails validation
```bash
# Validate XMLTV output
xmllint --noout --dtdvalid xmltv.dtd ~/gracenote2epg/cache/xmltv.xml

# Download DTD if needed
wget http://xmltv.cvs.sourceforge.net/viewvc/*checkout*/xmltv/xmltv/xmltv.dtd
```

**Problem**: Encoding issues in XMLTV
```bash
# Check file encoding
file ~/gracenote2epg/cache/xmltv.xml

# Should show: UTF-8 Unicode text
# If not, check locale settings
locale
```

### Missing Program Data

**Problem**: Programs missing descriptions or details
```bash
# Check if extended details are enabled
grep -E "(xdetails|xdesc)" ~/gracenote2epg/conf/gracenote2epg.xml

# Enable extended features
<setting id="xdetails">true</setting>  <!-- Download extended data -->
<setting id="xdesc">true</setting>     <!-- Use extended descriptions -->
```

## Language Detection Issues

### Language Detection Not Working

**Problem**: All content marked as English
```bash
# Check if langdetect is available
python -c "import langdetect; print('Available')"

# Check configuration
grep langdetect ~/gracenote2epg/conf/gracenote2epg.xml

# Enable language detection
<setting id="langdetect">true</setting>
```

**Problem**: Incorrect language detection
```bash
# Check language statistics in logs
grep -i "language.*statistics" ~/gracenote2epg/log/gracenote2epg.log

# Language detection accuracy improves with cache
# First run: Lower accuracy  
# Subsequent runs: High accuracy from cache
```

## Performance Issues

### Slow Performance

**Problem**: Very slow downloads
```bash
# Check cache efficiency
grep -i "cache efficiency" ~/gracenote2epg/log/gracenote2epg.log

# Optimize cache settings
<setting id="refresh">24</setting>     <!-- Reduce refresh window -->
<setting id="redays">14</setting>      <!-- Increase cache retention -->
```

**Problem**: High memory usage
```bash
# Monitor memory during execution
top -p $(pgrep -f gracenote2epg)

# Reduce concurrent operations
# Current: Optimized for single-threaded operation
# Solution: Run with --days 1 for testing
```

### Log Rotation Issues

**Problem**: Logs not rotating
```bash
# Check rotation configuration
grep -E "(logrotate|relogs)" ~/gracenote2epg/conf/gracenote2epg.xml

# Add rotation configuration
<setting id="logrotate">true</setting>
<setting id="relogs">30</setting>

# Manual trigger test
tv_grab_gracenote2epg --debug --console --days 1
```

## Debug Information Collection

### Complete Debug Session
```bash
# Run complete debug session
tv_grab_gracenote2epg --debug --console --days 1 --zip YOUR_CODE 2>&1 | tee debug.log

# This captures:
# - Configuration processing
# - Lineup detection details  
# - Download attempts and results
# - Cache operations
# - Language detection
# - XMLTV generation
```

### Log File Analysis
```bash
# Check recent logs
tail -100 ~/gracenote2epg/log/gracenote2epg.log

# Search for errors
grep -i error ~/gracenote2epg/log/gracenote2epg.log

# Search for warnings
grep -i warning ~/gracenote2epg/log/gracenote2epg.log

# Check download statistics
grep -i "download.*completed" ~/gracenote2epg/log/gracenote2epg.log
```

### System Information
```bash
# Check Python version
python3 --version

# Check installed packages
pip list | grep -E "(gracenote2epg|langdetect|polib|requests)"

# Check system resources
df -h ~/gracenote2epg/
free -h
```

## Platform-Specific Issues

### Synology NAS

**Problem**: Path detection issues
```bash
# Check if TVheadend paths exist
ls -la /var/packages/tvheadend/var/
ls -la /var/packages/tvheadend/target/var/

# Manual path override if needed
tv_grab_gracenote2epg --basedir /volume1/gracenote2epg
```

### Raspberry Pi

**Problem**: Performance issues
```bash
# Check available memory
free -h

# Reduce cache if needed
<setting id="redays">3</setting>      <!-- Minimal cache -->
<setting id="days">3</setting>        <!-- Shorter guide -->
```

### Docker

**Problem**: Permission or path issues
```bash
# Check volume mounts
docker inspect container_name | grep -i mount

# Ensure proper permissions
chmod -R 755 /host/path/gracenote2epg/
```

## Getting Additional Help

### Enable Debug Mode
```bash
# Always run with debug when reporting issues
tv_grab_gracenote2epg --debug --console --days 1 --zip YOUR_CODE
```

### Information to Include When Reporting Issues

1. **Version**: `tv_grab_gracenote2epg --version`
2. **Platform**: OS version, Python version
3. **Configuration**: Your gracenote2epg.xml (remove passwords)
4. **Complete debug output**: Full console output with --debug
5. **Log files**: Recent entries from ~/gracenote2epg/log/
6. **Expected vs actual behavior**

### Useful Test Commands
```bash
# Test lineup detection
tv_grab_gracenote2epg --show-lineup --zip YOUR_CODE --debug

# Test basic functionality  
tv_grab_gracenote2epg --days 1 --zip YOUR_CODE --debug --console

# Test TVheadend integration
curl -s http://127.0.0.1:9981/api/channel/grid | head

# Validate XMLTV output
xmllint --noout ~/gracenote2epg/cache/xmltv.xml
```

## Common Solutions Summary

| Problem | Quick Solution |
|---------|----------------|
| Command not found | `pip install gracenote2epg` |
| No language detection | `pip install gracenote2epg[full]` |
| Configuration errors | `tv_grab_gracenote2epg --show-lineup --zip CODE` |
| No programs in TVheadend | [Complete EPG reset](migration.md) |
| Download failures | Enable `--debug` and check network |
| Cache issues | Verify `redays >= days` |
| Slow performance | Increase cache retention, reduce refresh window |
| Invalid XMLTV | Check encoding and validate with xmllint |

Remember: Most issues can be diagnosed with `--debug --console` output!
