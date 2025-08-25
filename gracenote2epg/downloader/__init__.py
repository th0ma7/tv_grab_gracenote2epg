"""
gracenote2epg.downloader - Unified download system

Provides all downloading capabilities through a clean, modular interface.
Supports both single-worker (sequential-like) and multi-worker (parallel) operations.
"""

from .base import OptimizedDownloader
from .parallel import (
    ParallelDownloadManager,
    AdaptiveParallelDownloader,
    RateLimiter,
    DownloadTask
)
from .monitoring import (
    RealTimeMonitor,
    ProgressBar,
    PerformanceAnalyzer,
    MetricsExporter,
    DownloadMetric
)

__all__ = [
    # Base downloader
    'OptimizedDownloader',
    
    # Parallel downloading
    'ParallelDownloadManager',
    'AdaptiveParallelDownloader', 
    'RateLimiter',
    'DownloadTask',
    
    # Monitoring and metrics
    'RealTimeMonitor',
    'ProgressBar',
    'PerformanceAnalyzer',
    'MetricsExporter',
    'DownloadMetric',
]


def create_download_system(
    max_workers: int = 4,
    enable_monitoring: bool = False,
    enable_adaptive: bool = True,
    base_delay: float = 0.8,
    min_delay: float = 0.4
):
    """
    Factory function to create a complete download system
    
    Args:
        max_workers: Maximum number of parallel workers (1 = sequential behavior)
        enable_monitoring: Enable real-time monitoring
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
    
    # Create parallel manager
    parallel_manager = ParallelDownloadManager(
        max_workers=max_workers,
        max_retries=3,
        base_delay=base_delay/2,
        enable_rate_limiting=True
    )
    
    # Create monitor if requested
    monitor = None
    if enable_monitoring:
        monitor = RealTimeMonitor(enable_console=True)
    
    return base_downloader, parallel_manager, monitor


def get_performance_config(max_workers: int = None) -> dict:
    """
    Get optimized performance configuration based on worker count
    
    Args:
        max_workers: Number of workers (None = auto-detect)
        
    Returns:
        Dictionary with performance settings
    """
    import os
    
    # Auto-detect workers if not specified
    if max_workers is None:
        max_workers = min(4, max(1, os.cpu_count() // 2))
    
    # Optimize settings based on worker count
    if max_workers == 1:
        # Sequential-like behavior
        return {
            'max_workers': 1,
            'enable_adaptive': False,
            'enable_monitoring': False,
            'rate_limit': 2.0,  # Conservative rate
            'base_delay': 1.0,
            'min_delay': 0.5,
        }
    elif max_workers <= 3:
        # Light parallelism
        return {
            'max_workers': max_workers,
            'enable_adaptive': True,
            'enable_monitoring': False,
            'rate_limit': 5.0,
            'base_delay': 0.8,
            'min_delay': 0.4,
        }
    else:
        # Full parallelism
        return {
            'max_workers': max_workers,
            'enable_adaptive': True,
            'enable_monitoring': True,
            'rate_limit': 8.0,
            'base_delay': 0.6,
            'min_delay': 0.3,
        }
