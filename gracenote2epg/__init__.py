"""
gracenote2epg - North America TV Guide Grabber

A modular Python implementation for downloading TV guide data from
tvlistings.gracenote.com with intelligent caching and TVheadend integration.
"""

__version__ = "1.0"
__author__ = "th0ma7"
__license__ = "GPL-3.0"

from .gracenote2epg_args import ArgumentParser
from .gracenote2epg_config import ConfigManager
from .gracenote2epg_downloader import OptimizedDownloader
from .gracenote2epg_parser import GuideParser
from .gracenote2epg_tvheadend import TvheadendClient
from .gracenote2epg_utils import CacheManager, TimeUtils
from .gracenote2epg_xmltv import XmltvGenerator

__all__ = [
    'ArgumentParser',
    'ConfigManager',
    'OptimizedDownloader',
    'GuideParser',
    'TvheadendClient',
    'CacheManager',
    'TimeUtils',
    'XmltvGenerator',
]
