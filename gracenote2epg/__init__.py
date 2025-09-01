"""
gracenote2epg - North America TV Guide Grabber

Unified architecture implementation with strategy-based parallel downloads,
intelligent worker allocation, and clean API design.

Key Features:
- Strategy-based worker allocation (conservative, balanced, aggressive)
- True adaptive behavior with task-specific optimization
- Unified download manager eliminating worker count inconsistencies
- Event-driven real-time monitoring system
- Clean API without legacy compatibility overhead
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional, List

__version__ = "2.0.0"
__author__ = "th0ma7"
__license__ = "GPL-3.0"
__architecture__ = "unified_strategy_based"

# Core modules
from .args import ArgumentParser
from .config import ConfigManager
from .language import LanguageDetector
from .tvheadend import TvheadendClient
from .utils import CacheManager, TimeUtils
from .xmltv import XmltvGenerator

# Unified download system
from .downloader import (
    OptimizedDownloader,
    UnifiedDownloadManager,
    AdaptiveStrategy,
    WorkerStrategy,
    PreciseWorkerPool,
    EventDrivenMonitor,
    create_download_system,
    get_performance_config,
    create_adaptive_strategy,
    get_recommended_strategy
)

# Unified parser system
from .parser.guide import UnifiedGuideParser

# i18n system
from .dictionaries import (
    get_category_translation,
    get_term_translation,
    get_language_display_name,
    get_available_languages,
    get_translation_statistics,
    reload_translations,
)

# Main exports - unified architecture
__all__ = [
    # Core system
    "ArgumentParser",
    "ConfigManager",
    "LanguageDetector",
    "TvheadendClient",
    "CacheManager",
    "TimeUtils",
    "XmltvGenerator",

    # Unified download system
    "OptimizedDownloader",
    "UnifiedDownloadManager",
    "AdaptiveStrategy",
    "WorkerStrategy",
    "PreciseWorkerPool",
    "EventDrivenMonitor",
    "create_download_system",
    "get_performance_config",
    "create_adaptive_strategy",
    "get_recommended_strategy",

    # Unified parser
    "UnifiedGuideParser",

    # i18n system
    "get_category_translation",
    "get_term_translation",
    "get_language_display_name",
    "get_available_languages",
    "get_translation_statistics",
    "reload_translations",
]


def create_gracenote_system(
    max_workers: int = 4,
    worker_strategy: str = "balanced",
    enable_adaptive: bool = True,
    enable_monitoring: bool = False,
    monitoring_config: dict = None,
    cache_dir: str = None,
    config_file: str = None
):
    """
    Factory function to create complete gracenote2epg system with unified architecture

    Args:
        max_workers: Number of parallel workers
        worker_strategy: Worker allocation strategy ("conservative", "balanced", "aggressive")
        enable_adaptive: Enable adaptive worker adjustment
        enable_monitoring: Enable real-time monitoring
        monitoring_config: Configuration dict for monitoring
        cache_dir: Cache directory path
        config_file: Configuration file path

    Returns:
        Tuple of (guide_parser, config_manager, cache_manager, download_manager)
    """
    # Initialize core components
    if cache_dir:
        cache_manager = CacheManager(Path(cache_dir))
    else:
        cache_manager = CacheManager(Path.home() / "gracenote2epg" / "cache")

    if config_file:
        config_manager = ConfigManager(Path(config_file))
    else:
        config_manager = ConfigManager(Path.home() / "gracenote2epg" / "conf" / "gracenote2epg.xml")

    # Create unified download system
    base_downloader, download_manager, monitor = create_download_system(
        max_workers=max_workers,
        worker_strategy=worker_strategy,
        enable_adaptive=enable_adaptive,
        enable_monitoring=enable_monitoring,
        monitoring_config=monitoring_config or {}
    )

    # Create unified parser with strategy-based architecture
    guide_parser = UnifiedGuideParser(
        cache_manager=cache_manager,
        base_downloader=base_downloader,
        max_workers=max_workers,
        worker_strategy=worker_strategy,
        enable_adaptive=enable_adaptive,
        enable_monitoring=enable_monitoring,
        monitoring_config=monitoring_config,
        download_manager=download_manager,
        monitor=monitor
    )

    return guide_parser, config_manager, cache_manager, download_manager


def get_system_info():
    """Get system information and capabilities with unified architecture details"""
    import platform

    # Get performance configuration
    perf_config = get_performance_config()

    return {
        'version': __version__,
        'author': __author__,
        'license': __license__,
        'architecture': __architecture__,
        'python_version': platform.python_version(),
        'platform': platform.platform(),
        'cpu_count': os.cpu_count(),
        'recommended_workers': perf_config.get('max_workers', 4),
        'recommended_strategy': get_recommended_strategy(perf_config.get('max_workers', 4)),
        'available_strategies': ['conservative', 'balanced', 'aggressive'],
        'features': [
            'Strategy-based worker allocation',
            'True adaptive behavior with task-specific optimization',
            'Unified download manager with consistent worker tracking',
            'Event-driven real-time monitoring',
            'Precise ThreadPoolExecutor management',
            'Intelligent caching with cleanup policies',
            'Multi-language support with automatic detection',
            'TVheadend integration',
            'Web API for external monitoring'
        ],
        'improvements': [
            'Eliminated worker count inconsistencies',
            'Separate strategies for guide vs series downloads',
            'True adaptive behavior implementation',
            'Clean API without legacy compatibility',
            'Enhanced monitoring with worker verification'
        ]
    }


def get_monitoring_status():
    """Get current monitoring configuration and availability"""
    # Check environment configuration
    monitoring_enabled = os.environ.get('GRACENOTE_ENABLE_MONITORING', 'false').lower() == 'true'
    web_api_enabled = os.environ.get('GRACENOTE_MONITORING_WEB_API', 'false').lower() == 'true'
    monitoring_port = int(os.environ.get('GRACENOTE_MONITORING_PORT', '9989'))

    return {
        'monitoring_available': True,
        'monitoring_enabled': monitoring_enabled,
        'web_api_enabled': web_api_enabled,
        'monitoring_port': monitoring_port,
        'architecture': 'event_driven_unified',
        'environment_vars': {
            'GRACENOTE_ENABLE_MONITORING': os.environ.get('GRACENOTE_ENABLE_MONITORING'),
            'GRACENOTE_MONITORING_WEB_API': os.environ.get('GRACENOTE_MONITORING_WEB_API'),
            'GRACENOTE_MONITORING_PORT': os.environ.get('GRACENOTE_MONITORING_PORT'),
        }
    }


def get_strategy_info():
    """Get detailed information about available worker strategies"""
    return {
        'available_strategies': ['conservative', 'balanced', 'aggressive'],
        'strategy_details': {
            'conservative': {
                'description': 'Gentle on servers, stable performance',
                'guide_workers': '2-3 workers',
                'series_workers': '1-2 workers',
                'rate_limits': 'Low (1.5-3.0 req/s)',
                'best_for': 'Shared connections, rate-limited environments',
                'adaptive_behavior': 'Minimal adjustments, prioritizes stability'
            },
            'balanced': {
                'description': 'Optimal for most users',
                'guide_workers': '4-6 workers',
                'series_workers': '2-3 workers',
                'rate_limits': 'Moderate (2.5-5.0 req/s)',
                'best_for': 'Standard home connections, typical usage',
                'adaptive_behavior': 'Moderate adjustments based on performance'
            },
            'aggressive': {
                'description': 'Maximum performance',
                'guide_workers': '6-10 workers',
                'series_workers': '3-4 workers',
                'rate_limits': 'High (4.0-8.0 req/s)',
                'best_for': 'Dedicated servers, high-bandwidth connections',
                'adaptive_behavior': 'Dynamic adjustments for optimal throughput'
            }
        },
        'selection_guidelines': {
            'cpu_cores_1_2': 'conservative',
            'cpu_cores_3_4': 'balanced',
            'cpu_cores_5_plus': 'aggressive',
            'shared_connection': 'conservative',
            'dedicated_server': 'aggressive',
            'typical_home': 'balanced'
        }
    }


def diagnose_configuration(config_file: str = None) -> dict:
    """
    Diagnose current configuration and provide optimization recommendations

    Args:
        config_file: Optional config file path

    Returns:
        Diagnosis report with recommendations
    """
    # System capabilities
    cpu_count = os.cpu_count()
    recommended_workers = min(6, max(2, cpu_count // 2))
    recommended_strategy = get_recommended_strategy(recommended_workers)

    # Environment analysis
    env_config = {
        'GRACENOTE_WORKER_STRATEGY': os.environ.get('GRACENOTE_WORKER_STRATEGY'),
        'GRACENOTE_MAX_WORKERS': os.environ.get('GRACENOTE_MAX_WORKERS'),
        'GRACENOTE_ENABLE_ADAPTIVE': os.environ.get('GRACENOTE_ENABLE_ADAPTIVE'),
        'GRACENOTE_ENABLE_MONITORING': os.environ.get('GRACENOTE_ENABLE_MONITORING'),
    }

    # Configuration file analysis
    config_analysis = {'status': 'not_found'}
    if config_file:
        config_path = Path(config_file)
    else:
        config_path = Path.home() / "gracenote2epg" / "conf" / "gracenote2epg.xml"

    if config_path.exists():
        try:
            config_manager = ConfigManager(config_path)
            # Load minimal config to analyze
            config = config_manager.load_config()
            config_analysis = {
                'status': 'found',
                'path': str(config_path),
                'zipcode': config.get('zipcode', 'not_set'),
                'lineupid': config.get('lineupid', 'auto'),
                'days': config.get('days', '1'),
                'extended_details': config.get('xdetails', False),
                'version': getattr(config_manager, 'version', 'unknown')
            }
        except Exception as e:
            config_analysis = {
                'status': 'error',
                'path': str(config_path),
                'error': str(e)
            }

    # Generate recommendations
    recommendations = []

    if cpu_count >= 8:
        recommendations.append(f"High-performance system detected ({cpu_count} cores): consider 'aggressive' strategy with 6-8 workers")
    elif cpu_count >= 4:
        recommendations.append(f"Standard system ({cpu_count} cores): 'balanced' strategy with 4-6 workers optimal")
    else:
        recommendations.append(f"Limited system ({cpu_count} cores): 'conservative' strategy recommended")

    if not env_config['GRACENOTE_ENABLE_MONITORING']:
        if recommended_workers > 2:
            recommendations.append("Enable monitoring for performance insight: GRACENOTE_ENABLE_MONITORING=true")

    if not env_config['GRACENOTE_WORKER_STRATEGY']:
        recommendations.append(f"Set optimal strategy: GRACENOTE_WORKER_STRATEGY={recommended_strategy}")

    if config_analysis['status'] == 'found':
        if config_analysis.get('zipcode') == 'not_set':
            recommendations.append("Configure zipcode in config file for proper operation")
        if not config_analysis.get('extended_details', False):
            recommendations.append("Enable extended details (xdetails=true) for richer program information")

    return {
        'system_capabilities': {
            'cpu_count': cpu_count,
            'recommended_workers': recommended_workers,
            'recommended_strategy': recommended_strategy
        },
        'environment_config': env_config,
        'configuration_file': config_analysis,
        'recommendations': recommendations,
        'architecture_info': {
            'version': __version__,
            'architecture': __architecture__,
            'strategies_available': ['conservative', 'balanced', 'aggressive'],
            'monitoring_system': 'EventDrivenMonitor',
            'worker_management': 'PreciseWorkerPool with strategy-based allocation'
        }
    }


def create_optimal_system_for_environment() -> tuple:
    """
    Create optimally configured system based on current environment

    Returns:
        Tuple of (guide_parser, config_manager, cache_manager, performance_config)
    """
    # Analyze system capabilities
    cpu_count = os.cpu_count()
    recommended_workers = min(6, max(2, cpu_count // 2))
    recommended_strategy = get_recommended_strategy(recommended_workers)

    # Check for high-performance indicators
    if cpu_count >= 8 and os.environ.get('GRACENOTE_HIGH_PERFORMANCE', '').lower() == 'true':
        # High-performance configuration
        max_workers = 8
        strategy = 'aggressive'
        enable_monitoring = True
        enable_web_api = True
    elif cpu_count >= 4:
        # Standard configuration
        max_workers = recommended_workers
        strategy = recommended_strategy
        enable_monitoring = recommended_workers > 2
        enable_web_api = False
    else:
        # Conservative configuration for limited systems
        max_workers = 2
        strategy = 'conservative'
        enable_monitoring = False
        enable_web_api = False

    # Override with environment variables
    if os.environ.get('GRACENOTE_WORKER_STRATEGY'):
        env_strategy = os.environ.get('GRACENOTE_WORKER_STRATEGY')
        if env_strategy in ['conservative', 'balanced', 'aggressive']:
            strategy = env_strategy

    if os.environ.get('GRACENOTE_MAX_WORKERS'):
        try:
            env_workers = int(os.environ.get('GRACENOTE_MAX_WORKERS'))
            if 1 <= env_workers <= 10:
                max_workers = env_workers
        except ValueError:
            pass

    # Create system with optimal configuration
    monitoring_config = {
        'enable_console': True,
        'enable_web_api': enable_web_api,
        'web_port': 9989
    }

    guide_parser, config_manager, cache_manager, download_manager = create_gracenote_system(
        max_workers=max_workers,
        worker_strategy=strategy,
        enable_adaptive=max_workers > 1,
        enable_monitoring=enable_monitoring,
        monitoring_config=monitoring_config
    )

    performance_config = {
        'max_workers': max_workers,
        'worker_strategy': strategy,
        'enable_adaptive': max_workers > 1,
        'enable_monitoring': enable_monitoring,
        'optimization_level': 'high' if max_workers >= 6 else 'standard' if max_workers >= 3 else 'conservative'
    }

    return guide_parser, config_manager, cache_manager, performance_config


def validate_unified_system() -> dict:
    """Validate that the unified system works correctly"""
    try:
        # Test system creation with different strategies
        test_results = {}

        for strategy in ['conservative', 'balanced', 'aggressive']:
            try:
                # Create minimal system for testing
                base_downloader, download_manager, monitor = create_download_system(
                    max_workers=4,
                    worker_strategy=strategy,
                    enable_adaptive=True,
                    enable_monitoring=False
                )

                # Test strategy configuration
                strategy_info = download_manager.adaptive_strategy.get_strategy_info()

                # Verify strategy loaded correctly
                if strategy_info['name'] == strategy:
                    test_results[strategy] = 'success'
                else:
                    test_results[strategy] = f'mismatch: expected {strategy}, got {strategy_info["name"]}'

                # Cleanup
                download_manager.cleanup()
                base_downloader.close()

            except Exception as e:
                test_results[strategy] = f'error: {str(e)}'

        # Test component integration
        integration_tests = {}

        try:
            # Test UnifiedDownloadManager creation
            manager = UnifiedDownloadManager(max_workers=2, worker_strategy='balanced')
            integration_tests['UnifiedDownloadManager'] = 'success'
            manager.cleanup()
        except Exception as e:
            integration_tests['UnifiedDownloadManager'] = f'error: {str(e)}'

        try:
            # Test AdaptiveStrategy creation
            strategy = create_adaptive_strategy('balanced', 4, True)
            integration_tests['AdaptiveStrategy'] = 'success'
            strategy.cleanup()
        except Exception as e:
            integration_tests['AdaptiveStrategy'] = f'error: {str(e)}'

        try:
            # Test PreciseWorkerPool creation
            pool = PreciseWorkerPool(initial_workers=2, max_workers=4)
            integration_tests['PreciseWorkerPool'] = 'success'
            pool.cleanup()
        except Exception as e:
            integration_tests['PreciseWorkerPool'] = f'error: {str(e)}'

        # Overall result
        all_success = (
            all(result == 'success' for result in test_results.values()) and
            all(result == 'success' for result in integration_tests.values())
        )

        return {
            'status': 'success' if all_success else 'issues_detected',
            'message': 'All unified system components validated successfully' if all_success else 'Some issues detected',
            'strategy_tests': test_results,
            'integration_tests': integration_tests,
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


def get_performance_tips() -> List[str]:
    """Get performance optimization tips for unified architecture"""
    return [
        "Choose strategy based on your system: conservative (1-2 cores), balanced (3-4 cores), aggressive (5+ cores)",
        "Enable adaptive mode for automatic optimization based on server response",
        "Use monitoring to observe worker efficiency and identify bottlenecks",
        "Conservative strategy is best for shared networks or rate-limited environments",
        "Aggressive strategy maximizes performance on dedicated servers with high bandwidth",
        "Monitor WAF blocks and 429 errors - reduce strategy aggressiveness if frequent",
        "Enable web API monitoring for detailed performance analysis: GRACENOTE_MONITORING_WEB_API=true",
        "Cache directory on fast storage (SSD) improves overall performance",
        "Increase refresh hours (--refresh) for better cache utilization on repeat runs",
        "Use --debug logging to identify specific performance bottlenecks"
    ]


# System diagnostic functions
def run_system_diagnostics():
    """Run comprehensive system diagnostics"""
    print("=" * 60)
    print(f"GRACENOTE2EPG UNIFIED SYSTEM DIAGNOSTICS")
    print("=" * 60)

    # System info
    system_info = get_system_info()
    print(f"Version: {system_info['version']}")
    print(f"Architecture: {system_info['architecture']}")
    print(f"Platform: {system_info['platform']}")
    print(f"CPU cores: {system_info['cpu_count']}")
    print(f"Recommended: {system_info['recommended_workers']} workers, '{system_info['recommended_strategy']}' strategy")

    # Configuration analysis
    print("\n" + "=" * 60)
    print("CONFIGURATION ANALYSIS")
    print("=" * 60)

    config_diag = diagnose_configuration()

    print("System capabilities:")
    caps = config_diag['system_capabilities']
    print(f"  CPU cores: {caps['cpu_count']}")
    print(f"  Recommended workers: {caps['recommended_workers']}")
    print(f"  Recommended strategy: {caps['recommended_strategy']}")

    print("\nEnvironment configuration:")
    env_config = config_diag['environment_config']
    for key, value in env_config.items():
        status = "SET" if value else "default"
        print(f"  {key}: {value or 'not set'} ({status})")

    print("\nConfiguration file:")
    config_file = config_diag['configuration_file']
    print(f"  Status: {config_file['status']}")
    if config_file['status'] == 'found':
        print(f"  Path: {config_file['path']}")
        print(f"  Zipcode: {config_file['zipcode']}")
        print(f"  LineupID: {config_file['lineupid']}")

    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)

    for i, rec in enumerate(config_diag['recommendations'], 1):
        print(f"{i}. {rec}")

    # Performance tips
    print("\n" + "=" * 60)
    print("PERFORMANCE TIPS")
    print("=" * 60)

    tips = get_performance_tips()
    for i, tip in enumerate(tips[:5], 1):  # Show top 5 tips
        print(f"{i}. {tip}")

    # Validation
    print("\n" + "=" * 60)
    print("SYSTEM VALIDATION")
    print("=" * 60)

    validation = validate_unified_system()
    print(f"Status: {validation['status']}")
    print(f"Message: {validation['message']}")

    if validation['status'] != 'success':
        print("\nIssues detected:")
        for component, result in validation.get('integration_tests', {}).items():
            if result != 'success':
                print(f"  {component}: {result}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Run diagnostics when module is executed directly
    run_system_diagnostics()
