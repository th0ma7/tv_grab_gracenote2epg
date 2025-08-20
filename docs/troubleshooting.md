# Troubleshooting Guide

This guide covers general issues with gracenote2epg. For TVheadend-specific problems, see the **[TVheadend Guide](tvheadend.md)**.

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

## 📺 TVheadend Issues

**For TVheadend-specific problems**, see the **[TVheadend Integration Guide](tvheadend.md)**:

- Channels appear but no programs in TVheadend
- EPG grabber migration in TVheadend  
- TVheadend EPG database reset procedures
- Channel filtering and matching issues
- TVheadend log analysis

**Continue reading below for general gracenote2epg issues.**

## Installation Issues

### Command Not Found

**Problem**: `Command 'tv_grab_gracenote2epg' not found`

**Solutions**:
```bash
# Solution 1: Install from GitHub (PyPI not yet available)
pip install git+https://github.com/th0ma7/gracenote2epg.git[full]

# Solution 2: Check if installed
pip list | grep gracenote2epg

# Solution 3: Use module execution
python -m gracenote2epg --version

# Solution 4: Check if script is in PATH (for manual installations)
find /usr/local/bin /usr/bin ~/.local/bin -name "tv_grab_gracenote2epg" 2>/dev/null

# Solution 5: For Synology TVheadend environment
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/which tv_grab_gracenote2epg'

# 🔮 Future: Once PyPI is available
# pip install gracenote2epg[full]
```

**Important**: The `tv_grab_gracenote2epg` wrapper script is **essential** for TVheadend integration. If missing:
- TVheadend won't detect the grabber
- XMLTV standard compliance is broken
- Re-installation from GitHub may be required

### Missing Features

**Problem**: Language detection not working
```bash
# Check if langdetect is installed
python -c "import langdetect; print('OK')"
# If error: ModuleNotFoundError: No module named 'langdetect'

# Solution: Install with full features from GitHub
pip install git+https://github.com/th0ma7/gracenote2epg.git[full]
# OR manually install dependency
pip install langdetect

# 🔮 Future PyPI command:
# pip install gracenote2epg[full]
```

**Problem**: Categories not translating
```bash
# Check if polib is installed  
python -c "import polib; print('OK')"
# If error: ModuleNotFoundError: No module named 'polib'

# Solution: Install with full features from GitHub
pip install git+https://github.com/th0ma7/gracenote2epg.git[full]
# OR manually install dependency
pip install polib
```

### Permission Issues

**Problem**: Permission denied when creating directories
```bash
# Solution 1: Install for user only
pip install --user git+https://github.com/th0ma7/gracenote2epg.git[full]

# Verify user installation
pip list --user | grep gracenote2epg

# Solution 2: Use virtual environment
python3 -m venv gracenote_env
source gracenote_env/bin/activate
pip install git+https://github.com/th0ma7/gracenote2epg.git[full]

# Verify virtual environment installation
pip list | grep gracenote2epg

# Solution 3: Fix directory permissions
chmod 755 ~/gracenote2epg/

# 🔮 Future PyPI commands:
# pip install --user gracenote2epg[full]
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

## XMLTV Issues

### XMLTV File Problems

**Problem**: Issues with XMLTV output format or content
```bash
# Basic file check
ls -lh ~/gracenote2epg/cache/xmltv.xml

# Quick content verification
grep -c "programme start=" ~/gracenote2epg/cache/xmltv.xml  # Should show program count
head -5 ~/gracenote2epg/cache/xmltv.xml | grep -E "(xml|DOCTYPE)"  # Check format

# Check file encoding
file ~/gracenote2epg/cache/xmltv.xml  # Should show UTF-8
```

**For technical XMLTV validation** (DTD validation, standards compliance): See **[Development Guide](development.md#xmltv-validation)**

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

# Check XMLTV file was created
ls -lh ~/gracenote2epg/cache/xmltv.xml

# For technical XMLTV validation: see docs/development.md
```

### Documentation References

- **[TVheadend Issues](tvheadend.md)** - TVheadend-specific problems and EPG migration
- **[Configuration Guide](configuration.md)** - Complete configuration reference  
- **[Installation Guide](installation.md)** - Installation and software migration
- **[Development Guide](development.md)** - Technical validation, testing, and development
- **[GitHub Issues](https://github.com/th0ma7/gracenote2epg/issues)** - Report bugs and get help

## Common Solutions Summary

| Problem | Quick Solution |
|---------|----------------|
| Command not found | Install from GitHub: `pip install git+https://github.com/th0ma7/gracenote2epg.git[full]` |
| No language detection | `pip install git+https://github.com/th0ma7/gracenote2epg.git[full]` |
| Configuration errors | `tv_grab_gracenote2epg --show-lineup --zip CODE` |
| **TVheadend no programs** | **[See TVheadend Guide](tvheadend.md)** |
| Download failures | Enable `--debug` and check network |
| Cache issues | Verify `redays >= days` |
| Slow performance | Increase cache retention, reduce refresh window |
| **XMLTV validation** | **[See Development Guide](development.md)** |

**For TVheadend-specific issues**: See the **[TVheadend Integration Guide](tvheadend.md)**

Remember: Most issues can be diagnosed with `--debug --console` output!
