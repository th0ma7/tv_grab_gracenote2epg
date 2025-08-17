# Log Rotation in gracenote2epg

gracenote2epg includes a built-in log rotation system that automatically manages log files without interfering with log monitoring tools like `tail -f`.

## Features

- **Built-in rotation**: No external logrotate configuration needed
- **`tail -f` compatible**: Uses copytruncate strategy to maintain file monitoring
- **Multi-period support**: Intelligent daily, weekly, or monthly rotation with content analysis
- **Content-based analysis**: Analyzes actual log content instead of file timestamps for accurate rotation
- **Automatic cleanup**: Configurable retention of backup files
- **Visible rotation messages**: Clear reporting of rotation activities in logs
- **Seamless operation**: Rotation happens transparently during startup

## Configuration

Log rotation is configured in `gracenote2epg.xml`:

```xml
<!-- Log rotation settings -->
<setting id="logrotate_enabled">true</setting>     <!-- Enable/disable rotation -->
<setting id="logrotate_interval">weekly</setting>  <!-- Frequency: daily, weekly, monthly -->
<setting id="logrotate_keep">14</setting>          <!-- Number of backup files to keep -->
```

### Configuration Options

| Setting | Values | Default | Description |
|---------|--------|---------|-------------|
| `logrotate_enabled` | `true`/`false` | `true` | Enable or disable log rotation |
| `logrotate_interval` | `daily`/`weekly`/`monthly` | `weekly` | How often to rotate logs |
| `logrotate_keep` | Number (0-365) | `14` | Backup files to keep (0 = unlimited) |

## How It Works

### Multi-Period Rotation

gracenote2epg now uses an intelligent **multi-period rotation system** that:

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

**Enhanced**: The rotation system performs intelligent startup analysis:

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

Old backup files are automatically removed based on the `logrotate_keep` setting:

- **keep=14**: Keeps 14 most recent backup files
- **keep=0**: Unlimited backups (manual cleanup required)
- **keep=30**: Keeps 30 most recent backup files

## Usage Examples

### Enable Weekly Rotation (Default)
```xml
<setting id="logrotate_enabled">true</setting>
<setting id="logrotate_interval">weekly</setting>
<setting id="logrotate_keep">14</setting>
```

**Result**: Rotates every Monday, keeps 14 weeks of backups (~3.5 months)

### Daily Rotation for High-Volume Logging
```xml
<setting id="logrotate_enabled">true</setting>
<setting id="logrotate_interval">daily</setting>
<setting id="logrotate_keep">30</setting>
```

**Result**: Rotates daily at midnight, keeps 30 days of backups

### Monthly Rotation for Low-Volume Systems
```xml
<setting id="logrotate_enabled">true</setting>
<setting id="logrotate_interval">monthly</setting>
<setting id="logrotate_keep">12</setting>
```

**Result**: Rotates monthly, keeps 1 year of backups

### Disable Rotation
```xml
<setting id="logrotate_enabled">false</setting>
```

**Result**: Single log file grows indefinitely (requires manual management)

## Monitoring Log Rotation

### Visible Rotation Messages

Log rotation activities are now clearly reported in the current log:

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
2025/08/17 01:49:14 INFO     ============================================================
2025/08/17 01:49:14 INFO     gracenote2epg session started - Version 1.4
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

**Check if rotation parameters are in your configuration**:
```bash
grep -i logrotate ~/gracenote2epg/conf/gracenote2epg.xml
```

If nothing appears, add these parameters to your `gracenote2epg.xml`:
```xml
<setting id="logrotate_enabled">true</setting>
<setting id="logrotate_interval">weekly</setting>
<setting id="logrotate_keep">14</setting>
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
1. **Add rotation parameters** to your configuration (see above)
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

### Disk Space Issues

**Check log directory size**:
```bash
du -sh ~/gracenote2epg/log/
```

**Reduce backup count**:
```xml
<setting id="logrotate_keep">7</setting>  <!-- Keep only 1 week -->
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

### Custom Rotation Times

The rotation happens at:
- **Daily**: 00:00:00 (midnight)
- **Weekly**: Sunday 00:00:00 (start of week)
- **Monthly**: 1st day 00:00:00 (start of month)

These times are not configurable to maintain simplicity and predictability.

### Integration with System Logrotate

If you prefer system logrotate, disable built-in rotation:

```xml
<setting id="logrotate_enabled">false</setting>
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

**Note**: System logrotate won't have the intelligent multi-period content analysis.

## Performance Impact

- **Rotation operation**: < 10 seconds typically for multi-week analysis
- **Content analysis**: Minimal CPU usage (regex-based timestamp parsing)
- **Disk I/O**: Efficient (separate backup writes + single main file rebuild)
- **Memory usage**: Minimal (processes log line by line)
- **Log monitoring**: No interruption to `tail -f` or monitoring tools

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

### Error Handling

- **Malformed timestamps**: Assigns to current period or skips
- **Empty files**: No rotation needed
- **Permission errors**: Logged but non-fatal
- **Disk space**: Checks available space before creating backups
- **Backup conflicts**: Adds numeric suffix if filename exists

The system is designed to be robust and fail gracefully while providing clear feedback about any issues.
