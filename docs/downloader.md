# Gracenote2EPG Download System Architecture

## Overview

The gracenote2epg download system uses a unified parallel architecture designed to efficiently download TV guide data and series details from Gracenote's API while respecting rate limits and avoiding WAF (Web Application Firewall) blocks.

## System Components

### 1. Core Architecture

```
OptimizedDownloader (Base)
    ├── HTTP session management
    ├── Rate limiting & WAF detection
    ├── Adaptive delays & retries
    └── User-Agent rotation

ParallelDownloadManager
    ├── ThreadPoolExecutor management
    ├── Task distribution
    ├── Statistics collection
    └── Monitoring integration

EventDrivenMonitor
    ├── Real-time progress tracking
    ├── Worker state monitoring
    ├── Performance metrics
    └── Web API for external access
```

### 2. Worker Pool Management

#### WorkerPool Class
- **Purpose**: Manages ThreadPoolExecutor instances and worker states
- **Responsibility**: Track individual worker performance and status
- **Key Features**:
  - Worker state tracking (busy/idle, tasks completed)
  - Adaptive worker count adjustment
  - Performance metrics collection

#### Worker State Lifecycle
```
Worker Creation → Task Assignment → Execution → Completion → Reset
     ↓              ↓                ↓           ↓          ↓
  Worker ID=1    is_busy=True    Processing   Statistics  is_busy=False
                task_start_time   Content     Updated     task_reset()
```

### 3. Adaptive Behavior

#### What "Adaptive" Means

**Adaptive Mode** refers to the system's ability to automatically adjust its behavior based on real-time performance and server responses:

1. **Worker Count Adjustment**
   - Increases workers when performance is good (success rate >95%, response time <2s)
   - Decreases workers when encountering errors (429, WAF blocks, server overload)
   - Range: 1 to max_workers (typically 4-10)

2. **Rate Limiting Adaptation**
   - Starts at configured rate (e.g., 2 req/s)
   - Reduces aggressively on 429 errors (can drop to 0.2 req/s)
   - Gradually recovers when errors subside

3. **Delay Adjustment**
   - Base delay increases with consecutive failures
   - Random jitter prevents thundering herd
   - WAF blocks trigger longer delays (3-8 seconds)

#### Adaptive Triggers

| Condition | Action | Rationale |
|-----------|--------|-----------|
| HTTP 429 (Too Many Requests) | Reduce workers by 50%, lower rate limit | Server is overloaded |
| WAF Block (403, CAPTCHA) | Reduce to 1 worker, long delay | Avoid detection |
| Server Errors (502/503/504) | Reduce workers, lower rate | Server instability |
| High Success Rate (>95%) | Gradually increase workers | Capacity available |
| Consecutive Failures | Exponential backoff delays | Avoid hammering server |

## Current Implementation Issues

### 1. Worker Count Inconsistency

**Problem**: Logs report "2 workers" for series downloads, but 4 workers are actually active.

**Root Cause**: 
```python
# This only changes a variable, not the actual ThreadPoolExecutor
self.worker_pool.max_workers = effective_workers  # Changes limit
# But ThreadPoolExecutor was already created with 4 workers
ThreadPoolExecutor(max_workers=4)  # Still uses 4 workers
```

**Impact**: 
- Monitoring shows incorrect worker states
- Performance calculations are wrong
- Rate limiting assumptions are incorrect

### 2. Strategy Conflicts

**Current Strategy Issues**:
1. **Guide Downloads**: Claims to use 4 workers, actually uses 4 ✓
2. **Series Downloads**: Claims to use 2 workers, actually uses 4 ✗
3. **Adaptive Mode**: Enabled but not effectively working due to above issues

### 3. Monitoring Confusion

**Problem**: Real-time monitor tracks workers 1-4 from main pool, but series downloads might use different worker IDs from temporary pools.

## Recommended Architecture Changes

### 1. Unified Worker Strategy

**Proposal**: Use consistent worker counts with clear adaptive rules

```python
# Configuration examples
WORKER_STRATEGIES = {
    'conservative': {
        'guide_workers': 2,
        'series_workers': 1, 
        'adaptive': False
    },
    'balanced': {
        'guide_workers': 4,
        'series_workers': 2,
        'adaptive': True
    },
    'aggressive': {
        'guide_workers': 6,
        'series_workers': 4,
        'adaptive': True
    }
}
```

### 2. True Adaptive Implementation

**Enhanced Adaptive Logic**:
```python
class AdaptiveStrategy:
    def adjust_workers(self, task_type, current_performance):
        if task_type == 'guide':
            # Guide blocks are larger, can handle more workers
            return self.calculate_guide_workers(current_performance)
        elif task_type == 'series':
            # Series details are smaller, need fewer workers
            return self.calculate_series_workers(current_performance)
```

### 3. Monitoring Improvements

**Enhanced Real-time Monitoring**:
- Track actual ThreadPoolExecutor worker usage
- Separate metrics for guide vs series downloads
- Clear indication of adaptive adjustments
- Historical performance trending

## Performance Characteristics

### Guide Block Downloads
- **Typical Size**: 50-200KB per block
- **Request Pattern**: Burst of 8-32 requests (1-4 days)
- **Optimal Workers**: 3-6 workers
- **Rate Sensitivity**: Medium (can handle higher rates)

### Series Detail Downloads  
- **Typical Size**: 5-20KB per request
- **Request Pattern**: 100-2000+ individual requests
- **Optimal Workers**: 1-3 workers
- **Rate Sensitivity**: High (prone to 429 errors)

### Server Behavior Observations
- **Peak Hours**: Higher chance of rate limiting
- **WAF Sensitivity**: Triggered by rapid requests from same IP
- **Optimal Rate**: ~2-5 requests/second sustained
- **Burst Tolerance**: Can handle short bursts up to 10 req/s

## Configuration Recommendations

### 1. Default Configuration
```python
DEFAULT_CONFIG = {
    'max_workers': 4,
    'adaptive_enabled': True,
    'guide_strategy': {
        'workers': 4,
        'rate_limit': 5.0,
        'burst_allowed': True
    },
    'series_strategy': {
        'workers': 2,  
        'rate_limit': 2.0,
        'conservative': True
    }
}
```

### 2. Environment-Based Overrides
```bash
# Conservative (shared/limited bandwidth)
GRACENOTE_STRATEGY=conservative

# Aggressive (dedicated server)
GRACENOTE_STRATEGY=aggressive

# Custom
GRACENOTE_GUIDE_WORKERS=6
GRACENOTE_SERIES_WORKERS=1
```

### 3. Adaptive Thresholds
```python
ADAPTIVE_THRESHOLDS = {
    'increase_workers': {
        'success_rate': 0.95,
        'avg_response_time': 2.0,
        'no_429_for_seconds': 60
    },
    'decrease_workers': {
        'success_rate': 0.80,
        'avg_response_time': 5.0,
        'consecutive_429s': 2
    }
}
```

## Monitoring Metrics

### Key Performance Indicators

1. **Throughput Metrics**
   - Requests per second
   - MB/s downloaded
   - Tasks completed per minute

2. **Quality Metrics**
   - Success rate percentage
   - Error rate breakdown (429, 403, 5xx)
   - Average response time

3. **Adaptive Metrics**
   - Worker count changes over time
   - Rate limit adjustments
   - WAF block frequency

4. **Resource Metrics**
   - CPU usage per worker
   - Memory consumption
   - Network utilization

### Sample Monitoring Output
```
Guide Downloads: 4 workers active
├── Success Rate: 98.5% (197/200)
├── Throughput: 4.2 MB/s
├── Avg Response: 0.85s
└── Adaptive Status: Stable

Series Downloads: 2 workers active  
├── Success Rate: 92.1% (1845/2003)
├── Throughput: 0.3 MB/s
├── Rate Limited: 5 times (adapted down)
└── Adaptive Status: Recovered
```

## Troubleshooting Guide

### Common Issues

1. **All workers showing idle during series downloads**
   - Cause: ThreadPoolExecutor using different worker pool
   - Solution: Use consistent worker tracking

2. **Frequent 429 errors**
   - Cause: Too aggressive rate or too many workers
   - Solution: Enable adaptive mode, reduce series workers

3. **WAF blocks**
   - Cause: Rapid requests, predictable patterns
   - Solution: Increase delays, rotate user agents

4. **Inconsistent performance**
   - Cause: Mixed adaptive strategies
   - Solution: Clear worker allocation strategy

### Debug Information

Enable detailed logging:
```bash
GRACENOTE_ENABLE_MONITORING=true
GRACENOTE_MONITORING_WEB_API=true
GRACENOTE_DEBUG_WORKERS=true
```

Access real-time metrics:
```bash
curl http://localhost:9989/stats | jq .
```

## Future Improvements

### 1. Machine Learning Integration
- Learn optimal worker counts based on time of day
- Predict server capacity based on historical data
- Automatic strategy selection

### 2. Distributed Downloads
- Multiple IP addresses
- Geographic distribution
- Load balancing across endpoints

### 3. Enhanced Monitoring
- Grafana dashboard integration
- Alert system for performance degradation
- Historical trend analysis

### 4. Smart Retry Logic
- Exponential backoff with jitter
- Circuit breaker pattern
- Queue priority based on content age

---

**Note**: This system is designed to be respectful of Gracenote's servers while maximizing efficiency. Always monitor your usage and adjust parameters based on observed server behavior and your specific use case.
