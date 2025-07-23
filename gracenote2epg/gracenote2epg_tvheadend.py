#!/usr/bin/env python3
"""
TVHeadend Manager Module
Manages connection and data retrieval from TVHeadend
"""

import logging
import time
import requests
from requests.auth import HTTPDigestAuth
from typing import Dict, Optional, Tuple


class TVHeadendManager:
    """
    Manager for TVHeadend interactions
    """

    def __init__(self, host: str = "127.0.0.1", port: str = "9981",
                 username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize TVHeadend manager

        Args:
            host: TVHeadend IP address or hostname
            port: TVHeadend port
            username: Username (optional)
            password: Password (optional)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"http://{host}:{port}"
        self.channels = {}
        self.is_available = None

    def test_connection(self, timeout: int = 5) -> bool:
        """
        Test connection to TVHeadend

        Args:
            timeout: Timeout in seconds

        Returns:
            True if TVHeadend is accessible, False otherwise
        """
        try:
            test_url = f"{self.base_url}/api/serverinfo"
            if self.username and self.password:
                response = requests.get(test_url,
                                      auth=HTTPDigestAuth(self.username, self.password),
                                      timeout=timeout)
            else:
                response = requests.get(test_url, timeout=timeout)

            response.raise_for_status()
            self.is_available = True
            logging.info("TVHeadend connection test successful")
            return True

        except Exception as e:
            self.is_available = False
            logging.warning("TVHeadend connection test failed: %s", str(e))
            return False

    def get_channels(self, max_retries: int = 2, retry_delay: int = 5,
                    timeout: int = 10) -> Tuple[Dict[int, str], bool]:
        """
        Retrieve channel list from TVHeadend

        Args:
            max_retries: Maximum number of attempts
            retry_delay: Delay between attempts in seconds
            timeout: Timeout for each request

        Returns:
            Tuple (channel dictionary {number: name}, success)
        """
        channels_url = (f"{self.base_url}/api/channel/grid?all=1&limit=999999999"
                       f"&sort=name&filter=[{{\"type\":\"boolean\",\"value\":true,"
                       f"\"field\":\"enabled\"}}]")

        for attempt in range(max_retries + 1):
            try:
                if self.username and self.password:
                    logging.info('TVHeadend access using username and password... (attempt %d/%d)',
                               attempt + 1, max_retries + 1)
                    response = requests.get(channels_url,
                                          auth=HTTPDigestAuth(self.username, self.password),
                                          timeout=timeout)
                else:
                    logging.info('TVHeadend anonymous access... (attempt %d/%d)',
                               attempt + 1, max_retries + 1)
                    response = requests.get(channels_url, timeout=timeout)

                response.raise_for_status()

                logging.info('Accessing TVHeadend channel list from: %s', self.base_url)
                channels_data = response.json()

                if 'entries' not in channels_data:
                    raise ValueError('Invalid TVHeadend response format - missing "entries" field')

                channels = {}
                for ch in channels_data['entries']:
                    channel_name = ch.get('name', 'Unknown')
                    channel_num = ch.get('number', 0)
                    if channel_num:  # Avoid empty/null channel numbers
                        channels[channel_num] = channel_name

                self.channels = channels
                logging.info('%d TVHeadend channels found', len(channels))
                return channels, True

            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                if attempt < max_retries:
                    logging.warning('TVHeadend connection failed (attempt %d/%d): %s',
                                  attempt + 1, max_retries + 1, str(e))
                    logging.info('Retrying in %d seconds...', retry_delay)
                    time.sleep(retry_delay)
                else:
                    logging.warning('TVHeadend connection failed after %d attempts: %s',
                                  max_retries + 1, str(e))
                    return {}, False

            except requests.exceptions.HTTPError as e:
                logging.warning('TVHeadend HTTP error: %s', str(e))
                return {}, False

            except (ValueError, KeyError, TypeError) as e:
                logging.warning('TVHeadend response parsing error: %s', str(e))
                return {}, False

            except Exception as e:
                logging.warning('Unexpected error accessing TVHeadend: %s', str(e))
                return {}, False

        return {}, False

    def get_channel_by_number(self, channel_number: int) -> Optional[str]:
        """
        Get channel name by number

        Args:
            channel_number: Channel number

        Returns:
            Channel name or None if not found
        """
        return self.channels.get(channel_number)

    def get_all_channels(self) -> Dict[int, str]:
        """
        Return all loaded channels

        Returns:
            Dictionary of channels {number: name}
        """
        return self.channels.copy()

    def is_tvheadend_available(self) -> Optional[bool]:
        """
        Return TVHeadend availability status

        Returns:
            True if available, False if not available, None if not tested
        """
        return self.is_available


class TVHeadendConfig:
    """
    Configuration manager for TVHeadend
    Allows automatic disabling of TVH features
    """

    def __init__(self):
        self.tvhmatch = 'true'
        self.chmatch = 'true'
        self.auto_disabled = False

    def disable_tvh_features(self, reason: str = "TVHeadend not available"):
        """
        Automatically disable TVHeadend features

        Args:
            reason: Reason for disabling
        """
        self.tvhmatch = 'false'
        self.chmatch = 'false'
        self.auto_disabled = True

        logging.info('TVHeadend features disabled automatically: %s', reason)
        logging.info('  - tvhmatch: %s', self.tvhmatch)
        logging.info('  - chmatch: %s', self.chmatch)

    def restore_tvh_features(self):
        """
        Restore TVHeadend features
        """
        if self.auto_disabled:
            self.tvhmatch = 'true'
            self.chmatch = 'true'
            self.auto_disabled = False
            logging.info('TVHeadend features restored')

    def get_config_dict(self) -> Dict[str, str]:
        """
        Return configuration as dictionary

        Returns:
            Dictionary with TVH parameters
        """
        return {
            'tvhmatch': self.tvhmatch,
            'chmatch': self.chmatch,
            'auto_disabled': str(self.auto_disabled)
        }


def create_tvheadend_manager(tvhurl: str, tvhport: str, usern: Optional[str] = None,
                           passw: Optional[str] = None) -> TVHeadendManager:
    """
    Factory function to create a TVHeadend manager

    Args:
        tvhurl: TVHeadend URL
        tvhport: TVHeadend port
        usern: Username (optional)
        passw: Password (optional)

    Returns:
        TVHeadendManager instance
    """
    return TVHeadendManager(host=tvhurl, port=tvhport, username=usern, password=passw)


# Compatibility function to replace old tvhMatchGet
def tvhMatchGet(tvhurl: str, tvhport: str, usern: Optional[str] = None,
               passw: Optional[str] = None, tvh_config: Optional[TVHeadendConfig] = None) -> Dict[int, str]:
    """
    Compatibility function to replace old tvhMatchGet

    Args:
        tvhurl: TVHeadend URL
        tvhport: TVHeadend port
        usern: Username (optional)
        passw: Password (optional)
        tvh_config: TVHeadend configuration (optional)

    Returns:
        Dictionary of channels {number: name}
    """
    manager = create_tvheadend_manager(tvhurl, tvhport, usern, passw)

    # Test connection first
    if not manager.test_connection():
        if tvh_config:
            tvh_config.disable_tvh_features("Connection test failed")
        return {}

    # Retrieve channels
    channels, success = manager.get_channels()

    if not success and tvh_config:
        tvh_config.disable_tvh_features("Failed to retrieve channels")

    return channels


if __name__ == "__main__":
    # Usage example
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Test with default parameters
    manager = TVHeadendManager()

    if manager.test_connection():
        channels, success = manager.get_channels()
        if success:
            print(f"Found {len(channels)} channels:")
            for num, name in sorted(channels.items()):
                print(f"  {num}: {name}")
        else:
            print("Failed to retrieve channels")
    else:
        print("TVHeadend is not available")
        config = TVHeadendConfig()
        config.disable_tvh_features("Test connection failed")
        print(f"Configuration: {config.get_config_dict()}")
