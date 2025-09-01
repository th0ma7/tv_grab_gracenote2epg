"""
gracenote2epg.downloader.parallel - Unified parallel download system

Clean modular parallel download system with unified worker strategies.
No legacy compatibility - clean API for optimal performance.

Architecture:
- UnifiedDownloadManager: Main coordinator with strategy-based worker management
- AdaptiveStrategy: Intelligent worker allocation for different task types
- PreciseWorkerPool: Accurate ThreadPoolExecutor management
- AdaptiveRateController: Smart rate limiting with WAF detection
- EventDrivenMonitor: Real-time monitoring and statistics
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Core components
from .tasks import (
    DownloadTask,
    DownloadResult,
    TaskMetrics,
    create_guide_task,
    create_series_task,
    validate_task_result
)

from .rate_limiting import (
    RateLimiter,
    WAFDetector,
    AdaptiveRateController
)

from .statistics import (
    DownloadStatistics,
    PerformanceCalculator,
    DetailedStatisticsReporter,
    ProgressTracker
)

from .worker_pool import (
    WorkerState,
    PreciseWorkerPool,
    AdaptiveWorkerManager
)

from .adaptive import (
    WorkerStrategy,
    AdaptiveStrategy,
    PerformanceMetric,
    create_adaptive_strategy,
    get_recommended_strategy
)

from .manager import (
    UnifiedDownloadManager
)

# Main exports - clean API
__all__ = [
    # Primary interface
    'UnifiedDownloadManager',

    # Strategy and adaptive behavior
    'AdaptiveStrategy',
    'WorkerStrategy',
    'PerformanceMetric',
    'create_adaptive_strategy',
    'get_recommended_strategy',

    # Worker management
    'PreciseWorkerPool',
    'WorkerState',
    'AdaptiveWorkerManager',

    # Task management
    'DownloadTask',
    'DownloadResult',
    'TaskMetrics',
    'create_guide_task',
    'create_series_task',
    'validate_task_result',

    # Rate limiting and protection
    'RateLimiter',
    'WAFDetector',
    'AdaptiveRateController',

    # Statistics and monitoring
    'DownloadStatistics',
    'PerformanceCalculator',
    'DetailedStatisticsReporter',
    'ProgressTracker',
]

# Clean aliases for main components
DownloadManager = UnifiedDownloadManager
WorkerPool = PreciseWorkerPool

# System information
__version__ = "3.0.0-unified"
__architecture__ = "event_driven_unified"

# Configuration helpers
def create_download_system(
    max_workers: int = 4,
    worker_strategy: str = "balanced",
    enable_adaptive: bool = True,
    enable_monitoring: bool = False,
    monitoring_config: dict = None
) -> tuple:
    """
    Factory function to create unified download system

    Args:
        max_workers: Maximum number of parallel workers
        worker_strategy: Worker allocation strategy ("conservative", "balanced", "aggressive")
        enable_adaptive: Enable adaptive worker adjustment
        enable_monitoring: Enable real-time monitoring
        monitoring_config: Monitoring configuration

    Returns:
        Tuple of (download_manager, adaptive_strategy, monitor)
    """
    from ..monitoring import EventDrivenMonitor

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

    # Create adaptive strategy
    adaptive_strategy = create_adaptive_strategy(
        strategy_name=worker_strategy,
        max_workers=max_workers,
        enable_adaptive=enable_adaptive
    )

    # Create unified download manager
    download_manager = UnifiedDownloadManager(
        max_workers=max_workers,
        max_retries=3,
        base_delay=0.5,
        enable_rate_limiting=True,
        enable_adaptive=enable_adaptive,
        worker_strategy=worker_strategy,
        monitor=monitor
    )

    return download_manager, adaptive_strategy, monitor


def get_optimal_configuration(task_type: str, max_workers: int = None) -> dict:
    """
    Get optimal configuration for specific task type

    Args:
        task_type: Task type ("guide_block" or "series_details")
        max_workers: Maximum workers constraint

    Returns:
        Optimal configuration dictionary
    """
    import os

    # Auto-detect workers if not specified
    if max_workers is None:
        max_workers = min(6, max(2, os.cpu_count() // 2))

    # Get recommended strategy
    strategy_name = get_recommended_strategy(max_workers)

    # Create strategy to get configuration
    strategy = create_adaptive_strategy(strategy_name, max_workers, True)
    task_strategy = strategy.get_worker_strategy(task_type)

    return {
        'strategy_name': strategy_name,
        'max_workers': max_workers,
        'task_specific': {
            'initial_workers': task_strategy.initial_workers,
            'max_workers': task_strategy.max_workers,
            'rate_limit': task_strategy.rate_limit,
            'timeout': task_strategy.timeout,
            'conservative': task_strategy.conservative
        },
        'adaptive_enabled': True,
        'monitoring_recommended': max_workers > 2
    }


def validate_system() -> dict:
    """Validate that all unified system components work correctly"""
    try:
        # Test unified manager instantiation
        manager = UnifiedDownloadManager(max_workers=2, enable_adaptive=False)

        # Test adaptive strategy
        strategy = create_adaptive_strategy("balanced", 4, True)

        # Test worker pool
        pool = PreciseWorkerPool(initial_workers=2, max_workers=4)

        # Test task creation
        guide_task = DownloadTask(
            task_id="test_guide",
            url="http://example.com",
            task_type="guide_block"
        )

        series_task = DownloadTask(
            task_id="test_series",
            url="http://example.com",
            task_type="series_details",
            data="programSeriesID=test"
        )

        # Test rate controller
        rate_controller = AdaptiveRateController(initial_rate=2.0)

        # Test statistics
        stats = DownloadStatistics()

        # Cleanup
        manager.cleanup()
        strategy.cleanup()
        pool.cleanup()

        return {
            'status': 'success',
            'message': 'All unified system components validated successfully',
            'components_tested': [
                'UnifiedDownloadManager',
                'AdaptiveStrategy',
                'PreciseWorkerPool',
                'DownloadTask (guide_block)',
                'DownloadTask (series_details)',
                'AdaptiveRateController',
                'DownloadStatistics'
            ],
            'architecture': __architecture__,
            'version': __version__
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f'Validation failed: {str(e)}',
            'error': str(e),
            'architecture': __architecture__,
            'version': __version__
        }


def get_optimal_system(task_profile: str = "mixed", max_workers: int = None) -> tuple:
    """
    Create optimally configured download system based on expected usage profile

    Args:
        task_profile: Expected usage ("guide_heavy", "series_heavy", "mixed")
        max_workers: Maximum workers (None = auto-detect)

    Returns:
        Tuple of (downloader, manager, monitor) optimally configured
    """
    # Get optimal configuration
    config = get_performance_config(max_workers, task_profile)

    # Create system with optimal settings
    return create_download_system(
        max_workers=config['max_workers'],
        worker_strategy=config['worker_strategy'],
        enable_adaptive=config['enable_adaptive'],
        enable_monitoring=config['monitoring_config']['enable_monitoring'],
        monitoring_config=config['monitoring_config'],
        base_delay=config['base_delay'],
        min_delay=config['min_delay']
    )


def get_performance_config(max_workers: int = None, task_profile: str = "mixed") -> dict:
    """
    Get optimized performance configuration for unified system

    Args:
        max_workers: Number of workers (None = auto-detect)
        task_profile: Expected task profile ("guide_heavy", "series_heavy", "mixed")

    Returns:
        Dictionary with optimal performance settings
    """
    import os

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


def diagnose_system() -> dict:
    """Diagnose system configuration and provide recommendations"""
    import os

    # Check environment configuration
    env_config = {
        'GRACENOTE_WORKER_STRATEGY': os.environ.get('GRACENOTE_WORKER_STRATEGY'),
        'GRACENOTE_MAX_WORKERS': os.environ.get('GRACENOTE_MAX_WORKERS'),
        'GRACENOTE_ENABLE_ADAPTIVE': os.environ.get('GRACENOTE_ENABLE_ADAPTIVE'),
        'GRACENOTE_ENABLE_MONITORING': os.environ.get('GRACENOTE_ENABLE_MONITORING'),
    }

    # System capabilities
    cpu_count = os.cpu_count()
    recommended_workers = min(6, max(2, cpu_count // 2))

    # Performance recommendations
    recommendations = []

    if cpu_count >= 8:
        recommendations.append("High-performance system: consider 'aggressive' strategy with 6-8 workers")
    elif cpu_count >= 4:
        recommendations.append("Standard system: 'balanced' strategy with 4-6 workers optimal")
    else:
        recommendations.append("Limited system: 'conservative' strategy with 2-3 workers recommended")

    if not env_config['GRACENOTE_ENABLE_MONITORING']:
        recommendations.append("Enable monitoring for better performance insight: GRACENOTE_ENABLE_MONITORING=true")

    return {
        'system_info': {
            'cpu_count': cpu_count,
            'recommended_workers': recommended_workers,
            'recommended_strategy': get_recommended_strategy(recommended_workers)
        },
        'environment_config': env_config,
        'recommendations': recommendations,
        'available_strategies': list(AdaptiveStrategy.STRATEGIES.keys()),
        'monitoring_available': True,
        'architecture': 'unified_event_driven'
    }


def get_system_info() -> dict:
    """Get unified system information"""
    return {
        'version': __version__,
        'architecture': __architecture__,
        'key_improvements': [
            'Unified worker strategies for different task types',
            'Precise ThreadPoolExecutor tracking',
            'True adaptive behavior with task-specific thresholds',
            'Eliminated worker count inconsistencies',
            'Clean API without legacy compatibility burden'
        ],
        'strategies_available': list(AdaptiveStrategy.STRATEGIES.keys()),
        'task_types_supported': ['guide_block', 'series_details'],
        'monitoring_integration': 'EventDrivenMonitor with real-time metrics'
    }


if __name__ == "__main__":
    # Self-test when module is run directly
    print("Testing unified parallel download system...")

    validation_result = validate_system()
    print(f"Validation: {validation_result['status']}")

    if validation_result['status'] == 'success':
        print(f"✓ All components working: {', '.join(validation_result['components_tested'][:3])}...")
    else:
        print(f"✗ Error: {validation_result['message']}")

    system_info = get_system_info()
    print(f"\nSystem: {system_info['architecture']} v{system_info['version']}")
    print(f"Strategies: {', '.join(system_info['strategies_available'])}")
