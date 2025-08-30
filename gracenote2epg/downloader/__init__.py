"""
gracenote2epg.downloader - Clean download system with EventDrivenMonitor

Clean version without backward compatibility - uses direct class names.
"""

from .base import OptimizedDownloader
from .parallel import (
    ParallelDownloadManager,
    AdaptiveParallelDownloader,
    RateLimiter,
    DownloadTask
)
from .monitoring import (
    EventDrivenMonitor,
    EventType,
    MonitoringEvent,
    WorkerState,
    RealTimeStats,
    ProgressTracker,
    MonitoringMixin
)

__all__ = [
    # Base downloader
    'OptimizedDownloader',

    # Parallel downloading
    'ParallelDownloadManager',
    'AdaptiveParallelDownloader',
    'RateLimiter',
    'DownloadTask',

    # Event-driven monitoring
    'EventDrivenMonitor',
    'EventType',
    'MonitoringEvent',
    'WorkerState',
    'RealTimeStats',
    'ProgressTracker',
    'MonitoringMixin',
]


def create_download_system(
    max_workers: int = 4,
    enable_monitoring: bool = False,
    monitoring_config: dict = None,
    enable_adaptive: bool = True,
    base_delay: float = 0.8,
    min_delay: float = 0.4
):
    """
    Factory function to create a clean download system with EventDrivenMonitor

    Args:
        max_workers: Maximum number of parallel workers (1 = sequential behavior)
        enable_monitoring: Enable real-time event-driven monitoring
        monitoring_config: Configuration dict for monitoring (console, web_api, port, etc.)
        enable_adaptive: Enable adaptive worker adjustment
        base_delay: Base delay between requests
        min_delay: Minimum delay between requests

    Returns:
        Tuple of (base_downloader, parallel_manager, monitor)
    """
    # Create base downloader
    base_downloader = OptimizedDownloader(
        base_delay=base_delay,
        min_delay=min_delay
    )

    # Create monitor if requested
    monitor = None
    if enable_monitoring:
        config = monitoring_config or {}
        monitor = EventDrivenMonitor(
            enable_console=config.get('enable_console', True),
            enable_web_api=config.get('enable_web_api', False),
            web_port=config.get('web_port', 9989),
            metrics_file=config.get('metrics_file', None)
        )

    # Create parallel manager with integrated monitoring
    parallel_manager = ParallelDownloadManager(
        max_workers=max_workers,
        max_retries=3,
        base_delay=base_delay/2,
        enable_rate_limiting=True,
        monitor=monitor
    )

    # Connect base downloader to monitoring if available
    if monitor:
        def monitor_callback(event_type: str, worker_id: int, **data):
            if event_type == 'waf_detected':
                monitor.emit_event(EventType.WAF_DETECTED, worker_id, **data)
            elif event_type == 'rate_limit':
                monitor.emit_event(EventType.RATE_LIMIT_HIT, worker_id, **data)

        base_downloader.set_monitor_callback(monitor_callback)

    return base_downloader, parallel_manager, monitor


def get_performance_config(max_workers: int = None) -> dict:
    """
    Get optimized performance configuration for clean system

    Args:
        max_workers: Number of workers (None = auto-detect)

    Returns:
        Dictionary with performance settings including monitoring
    """
    import os

    # Auto-detect workers if not specified
    if max_workers is None:
        max_workers = min(4, max(1, os.cpu_count() // 2))

    # Base configuration
    base_config = {
        'max_workers': max_workers,
        'enable_adaptive': True,
        'base_delay': 0.8,
        'min_delay': 0.4,
    }

    # Monitoring configuration based on worker count and environment
    monitoring_config = {
        'enable_console': True,
        'enable_web_api': False,
        'web_port': 9989,
    }

    # Optimize settings based on worker count
    if max_workers == 1:
        # Sequential-like behavior
        base_config.update({
            'enable_adaptive': False,
            'rate_limit': 2.0,
            'base_delay': 1.0,
            'min_delay': 0.5,
        })
        monitoring_config['enable_monitoring'] = False

    elif max_workers <= 3:
        # Light parallelism
        base_config.update({
            'rate_limit': 5.0,
            'base_delay': 0.8,
            'min_delay': 0.4,
        })
        monitoring_config['enable_monitoring'] = True

    else:
        # Full parallelism
        base_config.update({
            'rate_limit': 8.0,
            'base_delay': 0.6,
            'min_delay': 0.3,
        })
        monitoring_config.update({
            'enable_monitoring': True,
            'enable_web_api': True,
        })

    # Override with environment variables
    if os.environ.get('GRACENOTE_ENABLE_MONITORING'):
        monitoring_config['enable_monitoring'] = (
            os.environ.get('GRACENOTE_ENABLE_MONITORING', 'false').lower() == 'true'
        )

    if os.environ.get('GRACENOTE_MONITORING_WEB_API'):
        monitoring_config['enable_web_api'] = (
            os.environ.get('GRACENOTE_MONITORING_WEB_API', 'false').lower() == 'true'
        )

    if os.environ.get('GRACENOTE_MONITORING_PORT'):
        try:
            monitoring_config['web_port'] = int(os.environ.get('GRACENOTE_MONITORING_PORT', '9989'))
        except ValueError:
            pass

    # Combine configurations
    base_config['monitoring_config'] = monitoring_config

    return base_config
