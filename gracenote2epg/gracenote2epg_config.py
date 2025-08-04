"""
gracenote2epg.gracenote2epg_config - Configuration management

Handles XML configuration file parsing, validation, automatic cleanup,
and migration from older versions.
"""

import logging
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set


class ConfigManager:
    """Manages gracenote2epg configuration file"""

    # Default configuration template
    DEFAULT_CONFIG = """<?xml version="1.0" encoding="utf-8"?>
<settings version="4">
  <setting id="zipcode">92101</setting>
  <setting id="lineupcode">lineupId</setting>
  <setting id="lineup">Local Over the Air Broadcast</setting>
  <setting id="device">-</setting>
  <setting id="days">7</setting>
  <setting id="redays">7</setting>
  <setting id="refresh">48</setting>
  <setting id="slist"></setting>
  <setting id="stitle">false</setting>
  <setting id="xdetails">true</setting>
  <setting id="xdesc">true</setting>
  <setting id="langdetect">true</setting>
  <setting id="epgenre">3</setting>
  <setting id="epicon">1</setting>
  <setting id="tvhoff">true</setting>
  <setting id="usern"></setting>
  <setting id="passw"></setting>
  <setting id="tvhurl">127.0.0.1</setting>
  <setting id="tvhport">9981</setting>
  <setting id="tvhmatch">true</setting>
  <setting id="chmatch">true</setting>
</settings>"""

    # Valid settings and their types
    VALID_SETTINGS = {
        # Required settings
        'zipcode': str,

        # Basic settings
        'lineupcode': str,
        'lineup': str,
        'device': str,
        'days': str,
        'redays': str,

        # Cache refresh settings
        'refresh': str,

        # Station filtering
        'slist': str,
        'stitle': bool,

        # Extended details
        'xdetails': bool,
        'xdesc': bool,
        'langdetect': bool,

        # Display options
        'epgenre': str,
        'epicon': str,

        # TVheadend integration
        'tvhoff': bool,
        'usern': str,
        'passw': str,
        'tvhurl': str,
        'tvhport': str,
        'tvhmatch': bool,
        'chmatch': bool,
    }

    # Settings order for clean output
    SETTINGS_ORDER = [
        'zipcode', 'lineupcode', 'lineup', 'device', 'days', 'redays', 'refresh',
        'slist', 'stitle', 'xdetails', 'xdesc', 'langdetect', 'epgenre', 'epicon',
        'tvhoff', 'usern', 'passw', 'tvhurl', 'tvhport', 'tvhmatch', 'chmatch'
    ]

    def __init__(self, config_file: Path):
        self.config_file = Path(config_file)
        self.settings: Dict[str, Any] = {}
        self.version: str = "4"

    def load_config(self, location_code: Optional[str] = None, days: Optional[int] = None,
                    langdetect: Optional[bool] = None, refresh_hours: Optional[int] = None) -> Dict[str, Any]:
        """Load and validate configuration file"""

        # Create default config if doesn't exist
        if not self.config_file.exists():
            self._create_default_config()

        # Parse configuration
        self._parse_config_file()

        # Override with command line arguments
        if location_code:
            self.settings['zipcode'] = location_code
            logging.info('Using zipcode from command line: %s', location_code)

        if days:
            self.settings['days'] = str(days)
            logging.info('Using days from command line: %s', days)

        if langdetect is not None:
            self.settings['langdetect'] = langdetect
            logging.info('Using langdetect from command line: %s', langdetect)

        if refresh_hours is not None:
            self.settings['refresh'] = str(refresh_hours)
            if refresh_hours == 0:
                logging.info('Cache refresh disabled from command line (--norefresh)')
            else:
                logging.info('Using refresh hours from command line: %s', refresh_hours)

        # Validate required settings
        self._validate_config()

        # Set defaults for missing settings
        self._set_defaults()

        return self.settings

    def _create_default_config(self):
        """Create default configuration file with proper permissions"""
        logging.info('Creating default configuration: %s', self.config_file)

        # Ensure directory exists with 755 permissions (rwxr-xr-x)
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        except Exception as e:
            # Fallback: create without mode specification (depends on umask)
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Write default configuration
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write(self.DEFAULT_CONFIG)

    def _parse_config_file(self):
        """Parse XML configuration file"""
        try:
            tree = ET.parse(self.config_file)
            root = tree.getroot()

            logging.info('Reading configuration from: %s', self.config_file)

            # Get version - default to version 4 for consistency
            self.version = root.attrib.get('version', '4')
            logging.info('Configuration version: %s', self.version)

            # Parse settings
            settings_dict = {}
            valid_settings = {}
            deprecated_settings = []

            for setting in root.findall('setting'):
                setting_id = setting.get('id')

                # Get value based on version
                if self.version == '2':
                    setting_value = setting.text
                else:
                    # Version 3+: try 'value' attribute first, then text
                    setting_value = setting.get('value')
                    if setting_value is None:
                        setting_value = setting.text
                    if setting_value == '':
                        setting_value = None

                settings_dict[setting_id] = setting_value
                logging.debug('Config setting: %s = %s', setting_id, setting_value)

                # Track valid vs deprecated settings
                if setting_id in self.VALID_SETTINGS:
                    valid_settings[setting_id] = setting_value
                elif setting_id.startswith('desc') and re.match(r'desc[0-9]{2}', setting_id):
                    deprecated_settings.append(f'{setting_id} (deprecated custom formatting)')
                elif setting_id == 'useragent':
                    deprecated_settings.append(f'{setting_id} (deprecated)')
                else:
                    deprecated_settings.append(f'{setting_id} (unknown)')
                    logging.warning('Unknown configuration setting: %s = %s', setting_id, setting_value)

            # Clean configuration if deprecated settings found
            if deprecated_settings:
                self._clean_config_file(valid_settings, deprecated_settings)

            # Process settings with type conversion
            self._process_settings(valid_settings)

        except ET.ParseError as e:
            logging.error('Cannot parse configuration file %s: %s', self.config_file, e)
            raise
        except Exception as e:
            logging.error('Error reading configuration file %s: %s', self.config_file, e)
            raise

    def _process_settings(self, settings_dict: Dict[str, str]):
        """Process and type-convert settings"""
        for setting_id, setting_value in settings_dict.items():
            if setting_id in self.VALID_SETTINGS:
                expected_type = self.VALID_SETTINGS[setting_id]

                if expected_type == bool:
                    self.settings[setting_id] = self._parse_boolean(setting_value)
                elif expected_type == str:
                    self.settings[setting_id] = setting_value if setting_value is not None else ''
                else:
                    self.settings[setting_id] = setting_value

                logging.debug('Processed setting: %s = %s (%s)',
                            setting_id, self.settings[setting_id], expected_type.__name__)

    def _parse_boolean(self, value: Any) -> bool:
        """Parse boolean values from configuration"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    def _validate_config(self):
        """Validate required configuration settings"""
        # Check required zipcode
        if not self.settings.get('zipcode'):
            logging.error('Zipcode is required but not found in configuration')
            logging.error('Available settings: %s', list(self.settings.keys()))
            raise ValueError('Missing required zipcode in configuration')

        # Validate refresh hours
        refresh_setting = self.settings.get('refresh', '48')
        try:
            refresh_hours = int(refresh_setting)
            if refresh_hours < 0 or refresh_hours > 168:
                logging.warning('Invalid refresh hours %d, using default 48', refresh_hours)
                self.settings['refresh'] = '48'
        except (ValueError, TypeError):
            logging.warning('Invalid refresh setting "%s", using default 48', refresh_setting)
            self.settings['refresh'] = '48'

    def _set_defaults(self):
        """Set default values for missing settings"""
        # Check if langdetect is available for smart default
        langdetect_available = self._check_langdetect_available()

        defaults = {
            'lineupcode': 'lineupId',
            'device': '-',
            'days': '1',
            'redays': '1',
            'refresh': '48',  # Default 48 hours refresh window
            'lineup': 'Local Over the Air Broadcast',
            'slist': '',
            'stitle': False,
            'xdetails': True,
            'xdesc': True,
            'langdetect': langdetect_available,  # Smart default based on availability
            'epgenre': '3',
            'epicon': '1',
            'tvhoff': True,
            'usern': '',
            'passw': '',
            'tvhurl': '127.0.0.1',
            'tvhport': '9981',
            'tvhmatch': True,
            'chmatch': True,
        }

        for key, default_value in defaults.items():
            if key not in self.settings or self.settings[key] is None:
                self.settings[key] = default_value
                if key == 'langdetect':
                    logging.debug('Set default langdetect: %s (based on availability)', default_value)
                else:
                    logging.debug('Set default: %s = %s', key, default_value)

    def _check_langdetect_available(self) -> bool:
        """Check if langdetect library is available"""
        try:
            import langdetect
            return True
        except ImportError:
            return False

    def _clean_config_file(self, valid_settings: Dict[str, str], deprecated_list: List[str]):
        """Clean configuration file by removing deprecated settings"""
        try:
            if not deprecated_list:
                logging.debug('No deprecated settings found - configuration file is clean')
                return

            # Create backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{self.config_file}.backup.{timestamp}"
            shutil.copy2(self.config_file, backup_file)
            logging.info('Created configuration backup: %s', backup_file)

            # Write cleaned configuration
            self._write_clean_config(valid_settings)

            logging.info('Configuration cleaned successfully')
            logging.info('  Removed %d deprecated/unknown settings: %s',
                        len(deprecated_list), ', '.join(deprecated_list))
            logging.info('  Kept %d valid settings', len(valid_settings))

        except Exception as e:
            logging.error('Error cleaning configuration file: %s', str(e))
            logging.error('Continuing with existing configuration...')

    def _write_clean_config(self, valid_settings: Dict[str, str]):
        """Write cleaned configuration file"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write(f'<settings version="{self.version or "4"}">\n')

            # Write settings in preferred order
            for setting_id in self.SETTINGS_ORDER:
                if setting_id in valid_settings:
                    value = valid_settings[setting_id]
                    if value is not None and str(value).strip():
                        f.write(f'  <setting id="{setting_id}">{value}</setting>\n')
                    else:
                        f.write(f'  <setting id="{setting_id}"></setting>\n')

            # Write any remaining settings not in ordered list
            for setting_id, value in valid_settings.items():
                if setting_id not in self.SETTINGS_ORDER:
                    if value is not None and str(value).strip():
                        f.write(f'  <setting id="{setting_id}">{value}</setting>\n')
                    else:
                        f.write(f'  <setting id="{setting_id}"></setting>\n')

            f.write('</settings>\n')

    def get_country(self) -> str:
        """Determine country from zipcode format"""
        zipcode = self.settings.get('zipcode', '')
        if zipcode.isdigit():
            return 'USA'
        else:
            return 'CAN'

    def needs_extended_download(self) -> bool:
        """Determine if extended details download is needed"""
        return self.settings.get('xdetails', False) or self.settings.get('xdesc', False)

    def get_station_list(self) -> Optional[List[str]]:
        """Get explicit station list if configured"""
        slist = self.settings.get('slist', '')
        if slist and slist.strip():
            return [s.strip() for s in slist.split(',') if s.strip()]
        return None

    def get_refresh_hours(self) -> int:
        """Get cache refresh hours from configuration"""
        try:
            return int(self.settings.get('refresh', '48'))
        except (ValueError, TypeError):
            logging.warning('Invalid refresh setting, using default 48 hours')
            return 48

    def log_config_summary(self):
        """Log configuration summary"""
        logging.info('Configuration values processed:')
        logging.info('  zipcode: %s', self.settings.get('zipcode'))
        logging.info('  lineup: %s', self.settings.get('lineup'))
        logging.info('  xdetails (download extended data): %s', self.settings.get('xdetails'))
        logging.info('  xdesc (use extended descriptions): %s', self.settings.get('xdesc'))
        logging.info('  langdetect (automatic language detection): %s', self.settings.get('langdetect'))

        # Log cache refresh configuration
        refresh_hours = self.get_refresh_hours()
        if refresh_hours == 0:
            logging.info('  refresh: disabled (use all cached data)')
        else:
            logging.info('  refresh: %d hours (refresh first %d hours of guide)', refresh_hours, refresh_hours)

        # Log configuration logic
        xdetails = self.settings.get('xdetails', False)
        xdesc = self.settings.get('xdesc', False)
        langdetect = self.settings.get('langdetect', False)

        if xdesc and not xdetails:
            logging.info('xdesc=true detected - automatically enabling extended details download')
        elif xdetails and not xdesc:
            logging.info('xdetails=true - downloading extended data but using basic descriptions')
        elif xdetails and xdesc:
            logging.info('Both xdetails and xdesc enabled - full extended functionality')
        else:
            logging.info('Extended features disabled - using basic guide data only')

        if langdetect:
            logging.info('Language detection enabled - will auto-detect French/English/Spanish')
        else:
            logging.info('Language detection disabled - all content will be marked as English')
