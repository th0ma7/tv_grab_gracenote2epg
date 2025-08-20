# Log Rotation in gracenote2epg

gracenote2epg includes a built-in log rotation system that automatically manages log files without interfering with log monitoring tools like `tail -f`. **Part of the unified cache and retention policy system**.

## Features

- **Built-in rotation**: No external logrotate configuration needed
- **`tail -f` compatible**: Uses copytruncate strategy to maintain file monitoring
- **Multi-period support**: Intelligent daily, weekly, or monthly rotation with content analysis
- **Content-based analysis**: Analyzes actual log content instead of file timestamps for accurate rotation
- **Automatic cleanup**: Configurable retention of backup files
- **Visible rotation messages**: Clear reporting of rotation activities in logs
- **Seamless operation**: Rotation happens transparently during startup
- **Unified configuration**: Part of the unified cache and retention policy system

## Configuration

Log rotation is configured as part of the unified cache and retention policy system in `gracenote2epg.xml`:

```xml
<!-- Cache and retention policies -->
<setting id="logrotate">true</setting>                       <!-- Log rotation: true(daily)|false|daily|weekly|monthly -->
<setting id="relogs">30</setting>                            <!-- Log retention: days(number) or weekly|monthly|quarterly -->
```

### Configuration Options

| Setting | Values | Default | Description |
|---------|--------|---------|-------------|
| `logrotate` | `true`/`false`/`daily`/`weekly`/`monthly` | `true` | Rotation frequency (`true` = daily) |
| `relogs` | Number or `weekly`/`monthly`/`quarterly`/`unlimited` | `30` | Log retention period |

**Retention Values:**
- **Number (days)**: `7`, `30`, `90` - Keep files for specified number of days
- **Period names**: `weekly` (7 days), `monthly` (30 days), `quarterly` (90 days)
- **Unlimited**: `unlimited` or `0` - Never delete old files

## Configuration Examples

### Standard Home Setup
```xml
<!-- Cache and retention policies -->
<setting id="logrotate">true</setting>    <!-- Daily log rotation -->
<setting id="relogs">30</setting>         <!-- 30 days log retention -->
```

**Result**: Logs rotate daily, kept for 30 days

### High-Volume Server
```xml
<!-- Cache and retention policies -->
<setting id="logrotate">daily</setting>   <!-- Explicit daily rotation -->
<setting id="relogs">quarterly</setting>  <!-- 90 days log retention -->
```

**Result**: Daily rotation with long retention for debugging

### Low-Volume System
```xml
<!-- Cache and retention policies -->
<setting id="logrotate">weekly</setting>  <!-- Weekly rotation -->
<setting id="relogs">monthly</setting>    <!-- 30 days retention -->
```

**Result**: Weekly rotation, monthly retention

### Disable Rotation
```xml
<!-- Cache and retention policies -->
<setting id="logrotate">false</setting>   <!-- No rotation -->
<setting id="relogs">unlimited</setting>  <!-- Keep all logs -->
```

**Result**: Single log file grows indefinitely

## How It Works

### Multi-Period Rotation

gracenote2epg uses an intelligent **multi-period rotation system** that:

1. **Analyzes log content** line by line instead of relying on file timestamps
2. **Identifies complete periods** (days, weeks, or months) within the log file
3. **Separates periods** into individual backup files 
4. **Preserves current period** in the main log file
5. **Reports activities** with clear, visible messages

### Content Analysis vs File Timestamps

**Traditional approach** (problematic):
```bash
# Uses file modification time - inaccurate for logs spanning multiple periods
file_mtime = 2025-08-16 19:19:49  # Recent timestamp
# Result: No rotation even if log contains weeks of old data
```

**gracenote2epg approach** (intelligent):
```bash
# Analyzes actual log entries by timestamp
first_log_entry = 2025-08-03 00:14:27  # Real content age
# Result: Proper rotation based on actual log content age
```

### Copytruncate Strategy

gracenote2epg uses a "copytruncate" approach that:

1. **Analyzes** the current log file content by periods
2. **Creates separate backups** for each complete period
3. **Rebuilds** the main log file with only current period data
4. **Continues writing** to the same file descriptor

This ensures compatibility with:
- `tail -f gracenote2epg.log` ✅
- Log monitoring tools ✅  
- Syslog forwarding ✅
- File watchers ✅

### Startup Rotation Check

The rotation system performs intelligent startup analysis:

- **Analyzes existing log content** by reading actual timestamps
- **Groups entries by periods** (daily/weekly/monthly boundaries)
- **Identifies complete periods** vs current period
- **Performs multi-period rotation** if needed
- **Reports all activities** with clear messages in the log

### Rotation Schedule & Examples

| Interval | Rotation Boundary | Week Definition | Backup File Examples |
|----------|-------------------|-----------------|----------------------|
| **Daily** | Every midnight | N/A | `gracenote2epg.log.2025-08-15`, `gracenote2epg.log.2025-08-14` |
| **Weekly** | Every Sunday at midnight | Sunday to Saturday (US standard) | `gracenote2epg.log.2025-W33`, `gracenote2epg.log.2025-W32` |
| **Monthly** | First day of month at midnight | Calendar month | `gracenote2epg.log.2025-08`, `gracenote2epg.log.2025-07` |

**Note**: For weekly rotation, Sunday is considered the first day of the week (US standard).

### Example: Multi-Week Rotation

If your log file contains multiple weeks of data:

```bash
# Before rotation - single file with multiple weeks
gracenote2epg.log  (7.2 MB, contains weeks 31, 32, and current week 33)

# After rotation - separated by complete weeks
gracenote2epg.log.2025-W31  (5.2 MB, week 31: Aug 3-9, complete)
gracenote2epg.log.2025-W32  (1.7 MB, week 32: Aug 10-16, complete)  
gracenote2epg.log           (0.1 MB, week 33: Aug 17+, current)
```

### Backup Cleanup

Old backup files are automatically removed based on the unified retention configuration:

- **relogs=30**: Keeps logs for 30 days
- **relogs=weekly**: Keeps logs for 7 days
- **relogs=quarterly**: Keeps logs for 90 days
- **relogs=unlimited**: Unlimited backups (manual cleanup required)

## Monitoring Log Rotation

### Visible Rotation Messages

Log rotation activities are clearly reported in the current log:

```bash
2025/08/17 01:49:08 INFO     Checking for startup log rotation...
2025/08/17 01:49:14 INFO     Log analysis complete (weekly rotation):
2025/08/17 01:49:14 INFO       Complete weeklys found: 2 (2025-W31, 2025-W32)
2025/08/17 01:49:14 INFO       Current weekly: 2025-W33 (will remain in current log)
2025/08/17 01:49:14 INFO     Multi-weekly rotation starting: 2 complete weeklys to rotate
2025/08/17 01:49:14 INFO     Created weekly backup: gracenote2epg.log.2025-W31 (5.2 MB, 2025-08-03 to 2025-08-09, 37542 lines)
2025/08/17 01:49:14 INFO     Created weekly backup: gracenote2epg.log.2025-W32 (1.7 MB, 2025-08-10 to 2025-08-16, 18234 lines)
2025/08/17 01:49:14 INFO     Current log rebuilt with 1 lines from current weekly
2025/08/17 01:49:14 INFO     Multi-weekly rotation completed successfully
2025/08/17 01:49:14 INFO     Startup rotation check completed
2025/08/17 01:49:14 INFO     Log Rotation Report:
2025/08/17 01:49:14 INFO       Recent rotation detected - 2 backup files created:
2025/08/17 01:49:14 INFO         Created backup: gracenote2epg.log.2025-W31 (5.2 MB) - weekly rotation
2025/08/17 01:49:14 INFO         Created backup: gracenote2epg.log.2025-W32 (1.7 MB) - weekly rotation
2025/08/17 01:49:14 INFO         Current log: gracenote2epg.log (0.0 MB) - contains current weekly only
2025/08/17 01:49:14 INFO       Log rotation completed successfully
```

### Unified Retention Status

The system also reports the overall retention policy:

```bash
2025/08/17 01:49:14 INFO     Unified cache and retention policy applied:
2025/08/17 01:49:14 INFO       logrotate: weekly (30 days retention)
2025/08/17 01:49:14 INFO       rexmltv: 7 days retention
```

### View Current Backup Files

```bash
# List all log files and backups
ls -la ~/gracenote2epg/log/

# Example output after multi-week rotation:
-rw-r--r-- 1 user user     1234 Aug 17 01:49 gracenote2epg.log               # Current week
-rw-r--r-- 1 user user  5443894 Aug 17 01:49 gracenote2epg.log.2025-W31      # Week 31 (complete)
-rw-r--r-- 1 user user  1776337 Aug 17 01:49 gracenote2epg.log.2025-W32      # Week 32 (complete)
```

### Monitor Current Log (tail -f compatible)

```bash
# Monitor current log in real-time (works during rotation)
tail -f ~/gracenote2epg/log/gracenote2epg.log

# Monitor with timestamps
tail -f ~/gracenote2epg/log/gracenote2epg.log | while read line; do
  echo "[$(date '+%H:%M:%S')] $line"
done
```

## Troubleshooting

### Rotation Not Working

**Check if unified retention parameters are in your configuration**:
```bash
grep -E "(logrotate|relogs)" ~/gracenote2epg/conf/gracenote2epg.xml
```

If nothing appears, add these parameters to your `gracenote2epg.xml`:
```xml
<!-- Cache and retention policies -->
<setting id="logrotate">true</setting>
<setting id="relogs">30</setting>
```

**Check for rotation messages**:
```bash
# Run with console output to see rotation messages
gracenote2epg --days 1 --zip 92101 --console --debug

# Look for these messages:
# "Checking for startup log rotation..."
# "Log analysis complete (weekly rotation):"
# "Multi-weekly rotation starting..."
# "Log rotation completed successfully"
```

**Check for errors**:
```bash
grep -i "error.*rotation" ~/gracenote2epg/log/gracenote2epg.log
```

### Old Logs Not Rotating

**Problem**: Log file has entries from weeks/months ago but no backup files created.

**Solution**: The enhanced rotation system analyzes content automatically:
1. **Add unified retention parameters** to your configuration (see above)
2. **Run gracenote2epg once** - it will analyze content and create appropriate backups
3. **Check rotation messages** in the log for details
4. **Verify backup files** created with proper date/period names

**Example of successful content analysis**:
```bash
# Check if backup files were created
ls -la ~/gracenote2epg/log/gracenote2epg.log.*

# Check rotation messages in current log
grep -A 10 -B 5 "Log analysis complete" ~/gracenote2epg/log/gracenote2epg.log
```

### Multi-Period Analysis Issues

**Problem**: Rotation creates unexpected number of backup files.

**Verification**: Check the content analysis results:
```bash
# Look for analysis details in debug mode
gracenote2epg --days 1 --zip 92101 --console --debug 2>&1 | grep -A 20 "Log analysis complete"

# Expected output:
# "Complete weeklys found: X (W31, W32, ...)"
# "Current weekly: W33 (will remain in current log)"
```

### Configuration Issues

**Problem**: Invalid retention values or validation errors.

**Check retention validation**:
```bash
# Look for validation messages
grep -i "retention.*invalid" ~/gracenote2epg/log/gracenote2epg.log

# Check unified policy status
grep -A 5 "Unified retention policy:" ~/gracenote2epg/log/gracenote2epg.log
```

**Fix invalid retention values**:
```xml
<!-- Valid retention values -->
<setting id="relogs">30</setting>        <!-- Number of days -->
<setting id="relogs">weekly</setting>    <!-- Period name -->
<setting id="relogs">monthly</setting>   <!-- Period name -->
<setting id="relogs">quarterly</setting> <!-- Period name -->
<setting id="relogs">unlimited</setting> <!-- No cleanup -->
```

### Disk Space Issues

**Check log directory size**:
```bash
du -sh ~/gracenote2epg/log/
```

**Reduce backup retention**:
```xml
<!-- Aggressive cleanup -->
<setting id="logrotate">daily</setting>
<setting id="relogs">7</setting>         <!-- 1 week only -->
```

### Permission Issues

**Check log directory permissions**:
```bash
ls -ld ~/gracenote2epg/log/
# Should be: drwxr-xr-x (755)
```

**Fix permissions if needed**:
```bash
chmod 755 ~/gracenote2epg/log/
chmod 644 ~/gracenote2epg/log/*.log*
```

## Advanced Configuration

### Integration with Unified System

The log rotation system is fully integrated with the unified cache and retention policy system. See **[CACHE_RETENTION_POLICIES.md](CACHE_RETENTION_POLICIES.md)** for:

- Complete unified configuration guide
- Examples for different use cases
- Performance impact details
- Best practices
- Implementation details

### Custom Rotation Times

The rotation happens at:
- **Daily**: 00:00:00 (midnight)
- **Weekly**: Sunday 00:00:00 (start of week)
- **Monthly**: 1st day 00:00:00 (start of month)

These times are not configurable to maintain simplicity and predictability.

### Integration with System Logrotate

If you prefer system logrotate, disable built-in rotation:

```xml
<!-- Cache and retention policies -->
<setting id="logrotate">false</setting>
<setting id="relogs">unlimited</setting>
```

Then configure system logrotate:
```bash
# /etc/logrotate.d/gracenote2epg
/home/*/gracenote2epg/log/gracenote2epg.log {
    weekly
    rotate 14
    copytruncate
    compress
    delaycompress
    notifempty
    missingok
}
```

**Note**: System logrotate won't have the intelligent multi-period content analysis or unified policy integration.

## Performance Impact

- **Rotation operation**: < 10 seconds typically for multi-week analysis
- **Content analysis**: Minimal CPU usage (regex-based timestamp parsing)
- **Disk I/O**: Efficient (separate backup writes + single main file rebuild)
- **Memory usage**: Minimal (processes log line by line)
- **Log monitoring**: No interruption to `tail -f` or monitoring tools
- **Unified integration**: No additional overhead from unified policy system

The multi-period content analysis adds minimal overhead while providing much more intelligent rotation behavior.

## Technical Details

### Content Analysis Algorithm

1. **Line-by-line processing**: Reads log file sequentially
2. **Timestamp extraction**: Uses regex to find `YYYY/MM/DD HH:MM:SS` patterns
3. **Period calculation**: Determines period boundaries (daily/weekly/monthly)
4. **Grouping**: Assigns each log line to appropriate period
5. **Completion detection**: Identifies which periods are complete vs current
6. **Multi-file creation**: Creates separate backup files for complete periods
7. **Main file rebuild**: Writes only current period back to main log

### Week Boundary Calculation

For weekly rotation:
- **Week starts**: Sunday 00:00:00 (US standard)
- **Week ends**: Saturday 23:59:59
- **Current week**: Any week containing today's date
- **Complete weeks**: All weeks that ended before current week started

### Unified Policy Integration

The log rotation system integrates with the unified cache and retention policy system by:

- **Shared configuration**: Uses the same configuration section
- **Consistent validation**: Same validation rules as other retention policies
- **Unified reporting**: Combined status reporting with cache and XMLTV retention
- **Automatic defaults**: Smart defaults based on system usage patterns

### Error Handling

- **Malformed timestamps**: Assigns to current period or skips
- **Empty files**: No rotation needed
- **Permission errors**: Logged but non-fatal
- **Disk space**: Checks available space before creating backups
- **Backup conflicts**: Adds numeric suffix if filename exists
- **Configuration errors**: Falls back to safe defaults with warnings

The system is designed to be robust and fail gracefully while providing clear feedback about any issues.

## See Also

- **[CACHE_RETENTION_POLICIES.md](CACHE_RETENTION_POLICIES.md)** - Complete unified cache and retention policy guide
- **[README.md](README.md)** - Main user guide with configuration examples
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and retention policy updates
