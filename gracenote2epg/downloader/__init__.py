"""
gracenote2epg.downloader - Unified download system with strategy-based architecture

Clean unified download system with intelligent worker strategies.
Provides optimal performance through task-specific worker allocation and true adaptive behavior.
"""

import logging
import os
from typing import Optional
from pathlib import Path

from .base import OptimizedDownloader
from .parallel import (
    UnifiedDownloadManager,
    AdaptiveStrategy,
    WorkerStrategy,
    PreciseWorkerPool,
    AdaptiveRateController,
    DownloadTask,
    create_adaptive_strategy,
    get_recommended_strategy,
    create_download_system as create_parallel_system
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
    # Core components
    'OptimizedDownloader',
    'UnifiedDownloadManager',

    # Strategy and adaptive behavior
    'AdaptiveStrategy',
    'WorkerStrategy',
    'create_adaptive_strategy',
    'get_recommended_strategy',

    # Worker management
    'PreciseWorkerPool',
    'AdaptiveRateController',
    'DownloadTask',

    # Monitoring system
    'EventDrivenMonitor',
    'EventType',
    'MonitoringEvent',
    'WorkerState',
    'RealTimeStats',
    'ProgressTracker',
    'MonitoringMixin',

    # Factory functions
    'create_download_system',
    'get_performance_config',
]


def create_download_system(
    max_workers: int = 4,
    worker_strategy: str = "balanced",
    enable_adaptive: bool = True,
    enable_monitoring: bool = False,
    monitoring_config: dict = None,
    base_delay: float = 0.5,
    min_delay: float = 0.25
):
    """
    Factory function to create unified download system with intelligent worker strategies

    Args:
        max_workers: Maximum number of parallel workers
        worker_strategy: Worker strategy ("conservative", "balanced", "aggressive")
        enable_adaptive: Enable adaptive worker adjustment
        enable_monitoring: Enable real-time event-driven monitoring
        monitoring_config: Configuration dict for monitoring
        base_delay: Base delay between requests
        min_delay: Minimum delay between requests

    Returns:
        Tuple of (downloader, manager, monitor)
    """
    # Create base downloader with optimized settings
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

    # Create unified download manager with strategy
    download_manager = UnifiedDownloadManager(
        max_workers=max_workers,
        max_retries=3,
        base_delay=base_delay,
        enable_rate_limiting=True,
        enable_adaptive=enable_adaptive,
        worker_strategy=worker_strategy,
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

    return base_downloader, download_manager, monitor


def get_performance_config(max_workers: int = None, task_profile: str = "mixed") -> dict:
    """
    Get optimized performance configuration for unified system

    Args:
        max_workers: Number of workers (None = auto-detect)
        task_profile: Expected task profile ("guide_heavy", "series_heavy", "mixed")

    Returns:
        Dictionary with optimal performance settings
    """
    # Auto-detect workers if not specified
    if max_workers is None:
        max_workers = min(6, max(2, os.cpu_count() // 2))

    # Get recommended strategy based on profile and worker count
    if task_profile == "guide_heavy":
        # Optimized for guide block downloads
        strategy = "aggressive" if max_workers >= 6 else "balanced"
        enable_adaptive = True
        monitoring_recommended = max_workers > 3

    elif task_profile == "series_heavy":
        # Optimized for series detail downloads
        strategy = "conservative" if max_workers <= 3 else "balanced"
        enable_adaptive = True
        monitoring_recommended = max_workers > 2

    else:  # mixed
        # Balanced for typical usage
        strategy = get_recommended_strategy(max_workers)
        enable_adaptive = max_workers > 1
        monitoring_recommended = max_workers > 2

    # Base configuration
    base_config = {
        'max_workers': max_workers,
        'worker_strategy': strategy,
        'enable_adaptive': enable_adaptive,
        'base_delay': 0.5,
        'min_delay': 0.25,
    }

    # Monitoring configuration
    monitoring_config = {
        'enable_monitoring': monitoring_recommended,
        'enable_console': True,
        'enable_web_api': max_workers > 4,  # Web API for complex setups
        'web_port': 9989,
    }

    # Override with environment variables
    if os.environ.get('GRACENOTE_WORKER_STRATEGY'):
        strategy_override = os.environ.get('GRACENOTE_WORKER_STRATEGY')
        if strategy_override in ['conservative', 'balanced', 'aggressive']:
            base_config['worker_strategy'] = strategy_override
        else:
            logging.warning("Invalid GRACENOTE_WORKER_STRATEGY '%s', using '%s'",
                           strategy_override, strategy)

    if os.environ.get('GRACENOTE_ENABLE_ADAPTIVE'):
        base_config['enable_adaptive'] = (
            os.environ.get('GRACENOTE_ENABLE_ADAPTIVE', 'true').lower() == 'true'
        )

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
