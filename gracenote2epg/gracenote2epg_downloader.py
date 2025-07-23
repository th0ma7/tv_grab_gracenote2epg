#!/usr/bin/env python3
"""
Gracenote data download module
"""
import os
import time
import gzip
import logging
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, Tuple

from .gracenote2epg_utils import savepage, deleteOldCache


class GracenoteDownloader:
    """
    Manager for downloading Gracenote data
    """

    def __init__(self, config: dict):
        """
        Initialize the downloader

        Args:
            config: gracenote2epg configuration
        """
        self.config = config
        self.base_url = "http://tvlistings.gracenote.com/api/grid"
        self.download_count = 0
        self.error_count = 0

    def build_url(self, gridtime: int) -> str:
        """
        Build download URL for a given time

        Args:
            gridtime: Grid timestamp

        Returns:
            str: Complete URL
        """
        lineup_id = self.config.get('lineupcode', '')
        if lineup_id and lineup_id != 'lineupId':
            lineup_param = lineup_id
        else:
            lineup_param = ''

        country = self.config.get('country', 'USA')
        device = self.config.get('device', '-')
        zipcode = self.config.get('zipcode', '')

        url = (f'{self.base_url}?'
               f'aid=orbebb'
               f'&lineupId={lineup_param}'
               f'&timespan=3'
               f'&headendId={lineup_param}'
               f'&country={country}'
               f'&device={device}'
               f'&postalCode={zipcode}'
               f'&time={int(gridtime)}'
               f'&isOverride=true'
               f'&pref=-'
               f'&userId=-')

        return url

    def get_headers(self) -> dict:
        """
        Return HTTP headers for requests

        Returns:
            dict: HTTP headers
        """
        return {
            'User-Agent': self.config.get('useragent',
                                        'Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0'),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def download_guide_data(self, gridtime: int, timeout: int = 30,
                          delay_between_requests: float = 1.0) -> Tuple[bool, Optional[bytes]]:
        """
        Download guide data for a given time

        Args:
            gridtime: Grid timestamp
            timeout: Timeout in seconds
            delay_between_requests: Delay between requests

        Returns:
            Tuple (success: bool, data: bytes or None)
        """
        try:
            url = self.build_url(gridtime)
            headers = self.get_headers()

            logging.info('Downloading guide data for: %i', int(gridtime))
            logging.debug('Request URL: %s', url)

            req = urllib.request.Request(url, data=None, headers=headers)

            # Delay between requests to avoid server overload
            if delay_between_requests > 0:
                time.sleep(delay_between_requests)

            response = urllib.request.urlopen(req, timeout=timeout)
            save_content = response.read()

            self.download_count += 1
            logging.info('Successfully downloaded guide data for: %i', int(gridtime))

            return True, save_content

        except urllib.error.HTTPError as e:
            self.error_count += 1
            logging.error('HTTP error downloading guide data for %i: %s (status: %d)',
                         int(gridtime), str(e), e.code)
            return False, None

        except urllib.error.URLError as e:
            self.error_count += 1
            logging.error('URL error downloading guide data for %i: %s',
                         int(gridtime), str(e))
            return False, None

        except Exception as e:
            self.error_count += 1
            logging.error('Could not download guide data for: %i - %s',
                         int(gridtime), str(e))
            return False, None

    def save_to_cache(self, gridtime: int, data: bytes) -> bool:
        """
        Save data to cache

        Args:
            gridtime: Grid timestamp
            data: Data to save

        Returns:
            bool: True if successful
        """
        try:
            filename = str(int(gridtime)) + '.json.gz'
            cache_dir = self.config.get('cacheDir')

            if not cache_dir:
                logging.error('Cache directory not configured')
                return False

            savepage(filename, data, cache_dir)
            logging.debug('Saved guide data to cache: %s', filename)
            return True

        except Exception as e:
            logging.error('Failed to save guide data to cache: %s', str(e))
            return False

    def download_and_cache(self, gridtime: int) -> bool:
        """
        Download and cache data for a given time

        Args:
            gridtime: Grid timestamp

        Returns:
            bool: True if successful
        """
        success, data = self.download_guide_data(gridtime)
        if success and data:
            return self.save_to_cache(gridtime, data)
        return False

    def file_exists_in_cache(self, gridtime: int) -> bool:
        """
        Check if file already exists in cache

        Args:
            gridtime: Grid timestamp

        Returns:
            bool: True if file exists
        """
        filename = str(int(gridtime)) + '.json.gz'
        cache_dir = self.config.get('cacheDir')
        if not cache_dir:
            return False

        file_path = os.path.join(cache_dir, filename)
        return os.path.exists(file_path)

    def get_cached_file_path(self, gridtime: int) -> str:
        """
        Return cached file path

        Args:
            gridtime: Grid timestamp

        Returns:
            str: File path
        """
        filename = str(int(gridtime)) + '.json.gz'
        cache_dir = self.config.get('cacheDir')
        return os.path.join(cache_dir, filename)

    def read_cached_file(self, gridtime: int) -> Optional[str]:
        """
        Read file from cache

        Args:
            gridtime: Grid timestamp

        Returns:
            str: File content or None if error
        """
        try:
            file_path = self.get_cached_file_path(gridtime)

            if not os.path.exists(file_path):
                return None

            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                content = f.read()

            logging.debug('Successfully read cached file: %s', os.path.basename(file_path))
            return content

        except Exception as e:
            logging.warning('Error reading cached file for %i: %s', gridtime, str(e))
            # Remove corrupted file
            try:
                file_path = self.get_cached_file_path(gridtime)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logging.info('Removed corrupted cache file: %s', os.path.basename(file_path))
            except:
                pass
            return None

    def cleanup_old_cache(self, gridtime_start: int, redays: str):
        """
        Clean up old cache files

        Args:
            gridtime_start: Start timestamp
            redays: Number of days to keep
        """
        cache_dir = self.config.get('cacheDir')
        if cache_dir:
            deleteOldCache(gridtime_start, redays, cache_dir)

    def ensure_cache_directory(self) -> bool:
        """
        Ensure cache directory exists

        Returns:
            bool: True if successful
        """
        try:
            cache_dir = self.config.get('cacheDir')
            if not cache_dir:
                logging.error('Cache directory not configured')
                return False

            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)
                logging.info('Created cache directory: %s', cache_dir)

            return True

        except Exception as e:
            logging.error('Failed to create cache directory: %s', str(e))
            return False

    def get_download_stats(self) -> Tuple[int, int]:
        """
        Return download statistics

        Returns:
            Tuple (download count, error count)
        """
        return self.download_count, self.error_count

    def reset_stats(self):
        """
        Reset statistics
        """
        self.download_count = 0
        self.error_count = 0


def create_downloader(config: dict) -> GracenoteDownloader:
    """
    Factory function to create a downloader

    Args:
        config: gracenote2epg configuration

    Returns:
        GracenoteDownloader instance
    """
    return GracenoteDownloader(config)


def calculate_grid_times(grid_start: int, day_hours: int, interval: int = 10800) -> list:
    """
    Calculate list of grid timestamps to download

    Args:
        grid_start: Start timestamp
        day_hours: Number of hours per day
        interval: Interval between grids (seconds)

    Returns:
        list: List of timestamps
    """
    grid_times = []
    gridtime = grid_start

    for count in range(day_hours):
        grid_times.append(gridtime)
        gridtime += interval

    return grid_times
