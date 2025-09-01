# Gracenote2EPG Download System Architecture

## Overview

The Gracenote2EPG download system features a unified, strategy-based architecture designed for efficient parallel downloads of TV guide data and series details from Gracenote's API. The system intelligently manages worker allocation, respects rate limits, and provides adaptive performance optimization.

---

## Core Architecture

```
UnifiedDownloadManager
    ├── Centralized worker pool management (ThreadPoolExecutor)
    ├── Strategy-based allocation per task type (guide, series)
    ├── Intelligent adaptive mode (performance feedback)
    ├── Real-time monitoring (EventDrivenMonitor)
    └── Unified API for all downloads
```

### Key Components

- **UnifiedDownloadManager**: Single interface managing all download types with dynamic worker allocation
- **WorkerPool**: Precise ThreadPoolExecutor management with consistent worker counts
- **AdaptiveStrategy**: Task-specific performance monitoring and automatic adjustments
- **EventDrivenMonitor**: Real-time performance tracking and statistics
- **RateLimiter**: Task-aware rate limiting to prevent server overload

---

## Download Strategies

The system uses predefined strategies that optimize worker allocation and rate limiting:

| Strategy      | Guide Workers | Series Workers | Rate Limit      | Best For                       |
|---------------|---------------|----------------|-----------------|--------------------------------|
| conservative  | 2-3           | 1-2            | 1.5-3 req/s     | Shared connections, low bandwidth |
| balanced      | 4-6           | 2-3            | 2.5-5 req/s     | Standard home setups           |
| aggressive    | 6-10          | 3-4            | 4-8 req/s       | Dedicated servers, high bandwidth |

**Configuration:**
```bash
# CLI argument
gracenote2epg --strategy balanced

# Environment variable
export GRACENOTE_WORKER_STRATEGY=balanced
```

---

## Adaptive Behavior

The adaptive system continuously monitors performance and adjusts worker counts based on:

- **Success rate**: Increases workers when >95% success rate
- **Response times**: Reduces workers when average >5.0s
- **Rate limiting**: Immediate reduction on 429 errors
- **Task type**: Different thresholds for guide vs series downloads

### Adaptive Logic Example
```python
# Guide downloads: More aggressive scaling (larger files)
if task_type == 'guide' and success_rate > 0.95 and avg_time < 2.0:
    increase_workers(increment=2)

# Series downloads: Conservative scaling (rate-limit sensitive)
elif task_type == 'series' and success_rate > 0.98 and avg_time < 1.5:
    increase_workers(increment=1)
```

---

## Worker Management

### Precise Pool Control
- Worker counts always match actual ThreadPoolExecutor configuration
- No discrepancies between reported and actual worker usage
- Clean pool recreation when adaptive adjustments are needed

### Task-Specific Allocation
- **Guide blocks**: Larger files (50-200KB), can utilize more workers
- **Series details**: Smaller files (5-20KB), more rate-limit sensitive

---

## Configuration

### Python API
```python
from gracenote2epg.downloader.parallel import UnifiedDownloadManager

manager = UnifiedDownloadManager(
    max_workers=6,
    worker_strategy='balanced',
    enable_adaptive=True,
    enable_monitoring=True
)

# Download guide blocks
results = manager.download_guide_blocks(guide_tasks)

# Download series details
results = manager.download_series_details(series_list)
```

### Environment Variables
```bash
# Core settings
export GRACENOTE_WORKER_STRATEGY=balanced
export GRACENOTE_MAX_WORKERS=4
export GRACENOTE_ENABLE_ADAPTIVE=true

# Monitoring
export GRACENOTE_ENABLE_MONITORING=true
export GRACENOTE_MONITORING_WEB_API=true
export GRACENOTE_MONITORING_PORT=9989
```

### Command Line
```bash
# Basic usage
gracenote2epg --strategy balanced --workers 4

# With monitoring
gracenote2epg --strategy aggressive --workers 8 --enable-monitoring

# Sequential mode
gracenote2epg --no-parallel
```

---

## Monitoring and Statistics

### Real-Time Statistics
The system provides detailed, accurate statistics:

```python
stats = manager.get_detailed_statistics()

# Worker pool status
for task_type, pool_info in stats['active_pools'].items():
    print(f"{task_type}: {pool_info['current_workers']} workers active")
    print(f"Success rate: {pool_info['success_rate']:.1%}")
    print(f"Throughput: {pool_info['throughput_mbps']:.1f} MB/s")
```

### Web Monitoring API
When enabled, access real-time stats at: `http://localhost:9989/stats`

Example output:
```json
{
  "guide_downloads": {
    "active_workers": 4,
    "success_rate": 0.985,
    "avg_response_time": 1.8,
    "adaptive_status": "stable"
  },
  "series_downloads": {
    "active_workers": 2,
    "success_rate": 0.921,
    "rate_limited_count": 5,
    "adaptive_status": "recovered"
  }
}
```

---

## Performance Characteristics

### Typical Results by Strategy

| Metric                    | Conservative | Balanced  | Aggressive |
|---------------------------|--------------|-----------|------------|
| Worker utilization        | 70-80%       | 85-95%    | 90-98%     |
| Download consistency      | ✓            | ✓         | ✓          |
| Rate limit adaptation     | Gentle       | Smart     | Aggressive |
| Monitoring accuracy       | Excellent    | Excellent | Excellent  |
| Memory usage             | Low          | Moderate  | High       |

### Expected Improvements
- **Consistency**: 100% accurate worker reporting
- **Efficiency**: 15-30% better resource utilization
- **Reliability**: Reduced 429 errors through intelligent rate limiting
- **Monitoring**: Real-time accurate performance metrics

---

## Best Practices

### Strategy Selection
- **Conservative**: Use for shared connections, limited bandwidth, or unstable networks
- **Balanced**: Default choice for most home users with standard broadband
- **Aggressive**: Only for dedicated servers with high bandwidth and CPU resources

### Performance Optimization
- Enable adaptive mode for automatic tuning
- Monitor success rates and adjust strategy if needed
- Use monitoring API to understand your system's behavior
- Consider network and server capacity when choosing max workers

### Resource Management
- Guide downloads can handle more parallelism (larger files)
- Series downloads need conservative parallelism (rate-limit sensitive)
- Monitor memory usage with high worker counts
- Use sequential mode (`max_workers=1`) if resources are very limited

---

## Troubleshooting

### Common Issues

**High rate limiting (429 errors):**
- Reduce strategy level (aggressive → balanced → conservative)
- Enable adaptive mode to auto-adjust
- Check if other applications are using Gracenote API

**Poor performance:**
- Verify network connectivity and bandwidth
- Check if adaptive mode is reducing workers due to poor performance
- Consider increasing max_workers if resources allow

**Worker count inconsistencies:**
- This should not occur with the current architecture
- If seen, check logs and report as a bug

### Diagnostic Commands
```bash
# Enable debug logging
gracenote2epg --debug --console

# Test with monitoring
export GRACENOTE_ENABLE_MONITORING=true
gracenote2epg --strategy balanced --workers 4

# Sequential fallback
gracenote2epg --no-parallel
```

---

## FAQ

**Q: How do I choose the right strategy?**
A: Start with 'balanced'. Monitor success rates and adjust based on your network and server performance.

**Q: Can I use sequential downloads?**
A: Yes, use `--no-parallel` or set `GRACENOTE_MAX_WORKERS=1`.

**Q: How do I verify worker consistency?**
A: Check the monitoring statistics - reported workers should always match actual usage.

**Q: What's the difference between guide and series downloads?**
A: Guide blocks are larger files that can utilize more workers; series details are smaller and more sensitive to rate limiting.

**Q: How does adaptive mode work?**
A: It continuously monitors performance and automatically adjusts worker counts to maintain optimal throughput while respecting server limits.

---

**Note**: This architecture maximizes download efficiency while respecting Gracenote's servers. Always monitor your logs and adjust parameters based on observed server behavior and your specific environment.
