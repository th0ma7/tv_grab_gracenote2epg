"""
gracenote2epg - North America TV Guide Grabber

A modular Python implementation for downloading TV guide data from
tvlistings.gracenote.com with unified parallel download architecture,
intelligent caching and TVheadend integration.

Unified Architecture:
- Single download method that scales from sequential (1 worker) to parallel (N workers)
- Modular organization with downloader/ and parser/ submodules
- Simplified maintenance with consistent interfaces
- Event-driven real-time monitoring system
"""

__version__ = "2.0.0"
__author__ = "th0ma7"
__license__ = "GPL-3.0"

# Core modules
from .args import ArgumentParser
from .config import ConfigManager
from .language import LanguageDetector
from .tvheadend import TvheadendClient
from .utils import CacheManager, TimeUtils
from .xmltv import XmltvGenerator

# Unified download system (refactored imports)
from .downloader import (
    OptimizedDownloader,
    ParallelDownloadManager,
    AdaptiveParallelDownloader,
    EventDrivenMonitor,
    create_download_system,
    get_performance_config
)

# Unified parser system
from .parser.guide import UnifiedGuideParser

# Backward compatibility alias
GuideParser = UnifiedGuideParser

# i18n system
from .dictionaries import (
    get_category_translation,
    get_term_translation,
    get_language_display_name,
    get_available_languages,
    get_translation_statistics,
    reload_translations,
)

# Main exports - updated for unified architecture
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
    "ParallelDownloadManager",
    "AdaptiveParallelDownloader",
    "EventDrivenMonitor",
    "create_download_system",
    "get_performance_config",

    # Unified parser
    "UnifiedGuideParser",
    "GuideParser",  # Backward compatibility alias

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
    enable_monitoring: bool = False,
    monitoring_config: dict = None,
    cache_dir: str = None,
    config_file: str = None
):
    """
    Factory function to create a complete gracenote2epg system with unified monitoring

    Args:
        max_workers: Number of parallel workers (1 = sequential behavior)
        enable_monitoring: Enable real-time monitoring
        monitoring_config: Configuration dict for monitoring
        cache_dir: Cache directory path
        config_file: Configuration file path

    Returns:
        Tuple of (guide_parser, config_manager, cache_manager)
    """
    from pathlib import Path

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
    base_downloader, parallel_manager, monitor = create_download_system(
        max_workers=max_workers,
        enable_monitoring=enable_monitoring,
        monitoring_config=monitoring_config or {}
    )

    # Create unified parser with monitoring integration
    guide_parser = UnifiedGuideParser(
        cache_manager=cache_manager,
        base_downloader=base_downloader,
        max_workers=max_workers,
        enable_monitoring=enable_monitoring,
        monitoring_config=monitoring_config
    )

    return guide_parser, config_manager, cache_manager


def get_system_info():
    """Get system information and capabilities with unified architecture details"""
    import platform
    import os

    # Get performance configuration
    perf_config = get_performance_config()

    return {
        'version': __version__,
        'author': __author__,
        'license': __license__,
        'python_version': platform.python_version(),
        'platform': platform.platform(),
        'cpu_count': os.cpu_count(),
        'recommended_workers': perf_config.get('max_workers', 4),
        'architecture': 'unified_event_driven',
        'monitoring_system': 'EventDrivenMonitor',
        'features': [
            'Unified download architecture',
            'Event-driven real-time monitoring',
            'Adaptive concurrency control',
            'Intelligent caching',
            'Multi-language support',
            'TVheadend integration',
            'Web API for external monitoring'
        ]
    }


def get_monitoring_status():
    """Get current monitoring configuration and availability"""
    import os

    # Check environment configuration
    monitoring_enabled = os.environ.get('GRACENOTE_ENABLE_MONITORING', 'false').lower() == 'true'
    web_api_enabled = os.environ.get('GRACENOTE_MONITORING_WEB_API', 'false').lower() == 'true'
    monitoring_port = int(os.environ.get('GRACENOTE_MONITORING_PORT', '9989'))

    return {
        'monitoring_enabled': monitoring_enabled,
        'web_api_enabled': web_api_enabled,
        'monitoring_port': monitoring_port,
        'environment_vars': {
            'GRACENOTE_ENABLE_MONITORING': os.environ.get('GRACENOTE_ENABLE_MONITORING'),
            'GRACENOTE_MONITORING_WEB_API': os.environ.get('GRACENOTE_MONITORING_WEB_API'),
            'GRACENOTE_MONITORING_PORT': os.environ.get('GRACENOTE_MONITORING_PORT'),
        }
    }


# Legacy aliases for backward compatibility (to be removed in future version)
# These are kept to avoid breaking existing code during transition period
LegacyGuideParser = UnifiedGuideParser
LegacyParallelManager = ParallelDownloadManager
LegacyRealTimeMonitor = EventDrivenMonitor
