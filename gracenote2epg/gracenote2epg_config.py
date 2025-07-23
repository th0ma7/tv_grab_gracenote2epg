#!/usr/bin/env python3
"""
Configuration management module for gracenote2epg
"""
import os
import sys
import logging
import xml.etree.ElementTree as ET


class GracenoteEPGConfig:
    """
    Configuration manager for gracenote2epg
    """

    def __init__(self, userdata_dir: str):
        """
        Initialize configuration

        Args:
            userdata_dir: User data directory
        """
        self.userdata = userdata_dir
        self.config = {
            'cacheDir': '',
            'userdata': userdata_dir,
            'stationList': None,
            'tvhmatch': 'false',
            'xdesc': 'false',
            'xdetails': 'false',
            'epicon': '1',
            'epgenre': '0',
            'stitle': 'false',
            'useragent': 'Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0',
            'xdescOrder': [],
            'use_tvh_filter': False,
            'tvh_channels': []
        }
        self.settings_dict = {}

    def validate_environment(self):
        """
        Validate critical environment variables

        Returns:
            tuple: (success: bool, error_message: str)
        """
        # Check ConfFile
        conf_file = os.environ.get('ConfFile')
        if not conf_file:
            return False, 'Environment variable ConfFile is not set'

        settings_file = os.path.join(self.userdata, conf_file)
        if not os.path.exists(settings_file):
            return False, f'Configuration file not found: {settings_file}'

        # Check other critical variables
        required_vars = ['ZipCode', 'Days', 'CacheDir', 'XMLTV']
        for var in required_vars:
            if not os.environ.get(var):
                logging.warning('Environment variable %s is not set', var)

        return True, ''

    def load_xml_settings(self):
        """
        Load settings from XML configuration file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conf_file = os.environ.get('ConfFile')
            settings_file = os.path.join(self.userdata, conf_file)

            logging.info('Loading configuration from: %s', settings_file)

            # Parse XML file
            settings = ET.parse(settings_file)
            root = settings.getroot()

            settings_found = root.findall('setting')
            if not settings_found:
                logging.error('No setting elements found in configuration file')
                return False

            # Extract settings
            for setting in settings_found:
                setting_str = setting.text
                if not setting_str:
                    setting_str = None
                setting_id = setting.get('id')
                if not setting_id:
                    continue
                self.settings_dict[setting_id] = setting_str

            logging.info('Successfully loaded %d configuration settings', len(self.settings_dict))
            return True

        except ET.ParseError as e:
            logging.error('Failed to parse XML configuration file: %s', e)
            return False
        except Exception as e:
            logging.exception('Exception loading XML settings: %s', str(e))
            return False

    def merge_environment_settings(self):
        """
        Merge environment settings with XML file settings
        """
        # Main parameters from environment or XML
        zipcode = os.environ.get('ZipCode') or self.settings_dict.get('zipcode')
        days = os.environ.get('Days') or self.settings_dict.get('days', '1')
        lineup = self.settings_dict.get('lineup')
        lineupcode = self.settings_dict.get('lineupcode')
        device = self.settings_dict.get('device', '-')
        redays = self.settings_dict.get('redays', '1')

        # Update configuration
        self.config.update({
            'zipcode': zipcode,
            'days': days,
            'lineup': lineup,
            'lineupcode': lineupcode,
            'device': device,
            'redays': redays,
            'stationList': self.settings_dict.get('slist'),
            'tvhmatch': self.settings_dict.get('tvhmatch', 'false'),
            'xdesc': self.settings_dict.get('xdesc', 'false'),
            'xdetails': self.settings_dict.get('xdetails', 'false'),
            'epicon': self.settings_dict.get('epicon', '1'),
            'epgenre': self.settings_dict.get('epgenre', '0'),
            'stitle': self.settings_dict.get('stitle', 'false'),
            'useragent': self.settings_dict.get('useragent',
                                               'Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0'),
            'cacheDir': os.path.join(self.userdata, os.environ.get('CacheDir', 'cache'))
        })

        # Validate postal code
        if not zipcode:
            logging.error('Critical configuration missing: zipcode')
            return False

        return True

    def detect_country(self):
        """
        Detect country based on postal code

        Returns:
            str: Country code ('USA' or 'CAN')
        """
        zipcode = self.config.get('zipcode', '')

        if zipcode and zipcode.isdigit():
            country = 'USA'
            logging.info('\tCountry: United States of America [%s]', country)
            logging.info('\tZIP code: %s', zipcode)
        elif zipcode:
            country = 'CAN'
            logging.info('\tCountry: Canada [%s]', country)
            logging.info('\tPostal code: %s', zipcode)
        else:
            country = 'USA'  # Default

        self.config['country'] = country
        return country

    def calculate_offset(self):
        """
        Calculate time offset

        Returns:
            float: Offset in days
        """
        offset = 0.0
        if "Offset" in os.environ:
            try:
                offset = float(os.environ.get('Offset'))
            except ValueError:
                offset = 0.0

        self.config['offset'] = offset
        return offset

    def setup_tvheadend_config(self, tvh_match_dict):
        """
        Configure TVHeadend integration

        Args:
            tvh_match_dict: TVHeadend channels dictionary
        """
        if self.settings_dict.get('tvhmatch') == 'true' and len(tvh_match_dict) > 0:
            tvh_channel_numbers = list(tvh_match_dict.keys())
            logging.info('TVHeadend integration ACTIVE with %d channels', len(tvh_channel_numbers))
            self.config['use_tvh_filter'] = True
            self.config['tvh_channels'] = tvh_channel_numbers
            self.config['tvhmatch'] = 'true'
        else:
            logging.info('TVHeadend integration DISABLED')
            self.config['use_tvh_filter'] = False
            self.config['tvhmatch'] = 'false'

    def get_config(self):
        """
        Return complete configuration

        Returns:
            dict: Configuration
        """
        return self.config.copy()

    def get_setting(self, key, default=None):
        """
        Get specific setting

        Args:
            key: Setting key
            default: Default value

        Returns:
            Setting value
        """
        return self.config.get(key, default)

    def get_xml_setting(self, key, default=None):
        """
        Get setting from XML settings

        Args:
            key: Setting key
            default: Default value

        Returns:
            Setting value
        """
        return self.settings_dict.get(key, default)

    def log_configuration(self):
        """
        Display configuration in logs
        """
        logging.info('Configuration loaded successfully')
        logging.info('Environment variables:')
        for var in ['ConfFile', 'ZipCode', 'Days', 'Offset', 'CacheDir', 'ConfDir', 'XMLTV']:
            logging.info('  %s: %s', var, os.environ.get(var))

        logging.info('Configuration parameters:')
        logging.info('\tTV Guide duration: %s days', self.config.get('days'))
        logging.info('\tLineup: %s', self.config.get('lineup'))
        logging.info('\tUser-Agent: %s', self.config.get('useragent')[:50] + '...')
        logging.info('\tCaching directory path: %s', self.config.get('cacheDir'))
        logging.info('\tTVHeadend integration: %s', self.config.get('tvhmatch'))


def create_config_manager(userdata_dir: str) -> GracenoteEPGConfig:
    """
    Factory function to create a configuration manager

    Args:
        userdata_dir: User data directory

    Returns:
        GracenoteEPGConfig instance
    """
    return GracenoteEPGConfig(userdata_dir)


def validate_environment_quick():
    """
    Quick validation of critical environment variables

    Returns:
        bool: True if environment is valid
    """
    critical_vars = ['ConfFile']
    for var in critical_vars:
        if not os.environ.get(var):
            logging.error('Critical environment variable %s is not set', var)
            return False
    return True
