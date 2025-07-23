#!/usr/bin/env python3
"""
Package gracenote2epg - TV Guide grabber for TVHeadend (Version 4.0)

Complete modular architecture:
- gracenote2epg_config: Configuration management
- gracenote2epg_tvheadend: TVHeadend integration
- gracenote2epg_downloader: Gracenote data downloading
- gracenote2epg_parser: Gracenote data parsing
- gracenote2epg_xmltv: XMLTV file generation
- gracenote2epg_utils: Utility functions
- gracenote2epg_args: CLI argument management
"""

__version__ = "4.0"
__author__ = "gracenote2epg team"

# Main imports to facilitate package usage
from .gracenote2epg_config import (
    GracenoteEPGConfig,
    create_config_manager,
    validate_environment_quick
)

from .gracenote2epg_tvheadend import (
    TVHeadendManager,
    TVHeadendConfig,
    tvhMatchGet,
    create_tvheadend_manager
)

from .gracenote2epg_downloader import (
    GracenoteDownloader,
    create_downloader,
    calculate_grid_times
)

from .gracenote2epg_parser import (
    parseStations,
    parseEpisodes,
    validateChannelNumber,
    shouldProcessStation,
    fix_icon_url
)

from .gracenote2epg_xmltv import (
    XMLTVGenerator,
    XMLTVValidator,
    create_xmltv_generator,
    generate_xmltv_from_schedule
)

from .gracenote2epg_utils import (
    convTime,
    convHTML,
    savepage,
    deleteOldCache,
    deleteOldShowCache,
    genShowList
)

from .gracenote2epg_args import (
    GracenoteEPGArgumentParser,
    create_argument_parser,
    main_with_args
)

# Export main classes and functions
__all__ = [
    # Configuration
    'GracenoteEPGConfig',
    'create_config_manager',
    'validate_environment_quick',

    # TVHeadend
    'TVHeadendManager',
    'TVHeadendConfig',
    'tvhMatchGet',
    'create_tvheadend_manager',

    # Downloading
    'GracenoteDownloader',
    'create_downloader',
    'calculate_grid_times',

    # Parsing
    'parseStations',
    'parseEpisodes',
    'validateChannelNumber',
    'shouldProcessStation',
    'fix_icon_url',

    # XMLTV
    'XMLTVGenerator',
    'XMLTVValidator',
    'create_xmltv_generator',
    'generate_xmltv_from_schedule',

    # Utilities
    'convTime',
    'convHTML',
    'savepage',
    'deleteOldCache',
    'deleteOldShowCache',
    'genShowList',

    # Arguments
    'GracenoteEPGArgumentParser',
    'create_argument_parser',
    'main_with_args'
]

def get_version():
    """Return package version"""
    return __version__

def get_module_info():
    """Return package module information"""
    return {
        'version': __version__,
        'author': __author__,
        'modules': [
            'gracenote2epg_config',
            'gracenote2epg_tvheadend',
            'gracenote2epg_downloader',
            'gracenote2epg_parser',
            'gracenote2epg_xmltv',
            'gracenote2epg_utils',
            'gracenote2epg_args'
        ],
        'description': 'TV Guide grabber for TVHeadend with modular architecture'
    }
