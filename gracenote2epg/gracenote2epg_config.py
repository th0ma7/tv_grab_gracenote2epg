"""
gracenote2epg.gracenote2epg_config - Configuration management

Handles XML configuration file parsing, validation, automatic cleanup,
and migration from older versions. Now includes simplified lineupid configuration
that automatically normalizes tvtv.com formats and detects device type.
"""

import logging
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple


class ConfigManager:
    """Manages gracenote2epg configuration file"""

    # Default configuration template
    DEFAULT_CONFIG = """<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <setting id="zipcode">92101</setting>
  <setting id="lineupid">auto</setting>
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
  <setting id="logrotate_enabled">true</setting>
  <setting id="logrotate_interval">weekly</setting>
  <setting id="logrotate_keep">14</setting>
</settings>"""

    # Valid settings and their types
    VALID_SETTINGS = {
        # Required settings
        'zipcode': str,

        # Single lineup setting
        'lineupid': str,

        # Basic settings
        'days': str,
        'redays': str,
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

        # Log rotation settings
        'logrotate_enabled': bool,
        'logrotate_interval': str,
        'logrotate_keep': str,
    }

    # DEPRECATED settings for migration
    DEPRECATED_SETTINGS = {
        'auto_lineup': 'lineupid',
        'lineupcode': 'lineupid',
        'lineup': 'lineupid',
        'device': 'lineupid'  # Auto-detected now
    }

    # Settings order for clean output
    SETTINGS_ORDER = [
        'zipcode', 'lineupid', 'days', 'redays', 'refresh',
        'slist', 'stitle', 'xdetails', 'xdesc', 'langdetect', 'epgenre', 'epicon',
        'tvhoff', 'usern', 'passw', 'tvhurl', 'tvhport', 'tvhmatch', 'chmatch',
        'logrotate_enabled', 'logrotate_interval', 'logrotate_keep'
    ]

    def __init__(self, config_file: Path):
        self.config_file = Path(config_file)
        self.settings: Dict[str, Any] = {}
        self.version: str = "5"  # Updated version for new simplified format

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
        """Parse XML configuration file with automatic migration"""
        try:
            tree = ET.parse(self.config_file)
            root = tree.getroot()

            logging.info('Reading configuration from: %s', self.config_file)

            # Get version - default to version 5 for new simplified format
            self.version = root.attrib.get('version', '5')
            logging.info('Configuration version: %s', self.version)

            # Parse settings
            settings_dict = {}
            valid_settings = {}
            deprecated_settings = []
            migration_needed = False

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
                elif setting_id in self.DEPRECATED_SETTINGS:
                    deprecated_settings.append(f'{setting_id} (migrated to {self.DEPRECATED_SETTINGS[setting_id]})')
                    migration_needed = True
                    # Handle migration
                    self._handle_deprecated_setting(setting_id, setting_value, valid_settings)
                elif setting_id.startswith('desc') and re.match(r'desc[0-9]{2}', setting_id):
                    deprecated_settings.append(f'{setting_id} (deprecated custom formatting)')
                elif setting_id == 'useragent':
                    deprecated_settings.append(f'{setting_id} (deprecated)')
                else:
                    deprecated_settings.append(f'{setting_id} (unknown)')
                    logging.warning('Unknown configuration setting: %s = %s', setting_id, setting_value)

            # Clean and migrate configuration if needed
            if deprecated_settings or migration_needed:
                self._clean_and_migrate_config(valid_settings, deprecated_settings)

            # Process settings with type conversion
            self._process_settings(valid_settings)

        except ET.ParseError as e:
            logging.error('Cannot parse configuration file %s: %s', self.config_file, e)
            raise
        except Exception as e:
            logging.error('Error reading configuration file %s: %s', self.config_file, e)
            raise

    def _handle_deprecated_setting(self, setting_id: str, setting_value: str, valid_settings: Dict[str, str]):
        """Handle migration of deprecated settings to new lineupid format"""
        if setting_id == 'auto_lineup':
            # If auto_lineup was false, we need to check for manual lineupcode
            if not self._parse_boolean(setting_value):
                # Will be handled when we process lineupcode
                pass
        elif setting_id == 'lineupcode':
            # Convert old lineupcode to new lineupid format
            if setting_value and setting_value != 'lineupId':
                # This was a manual lineup code
                valid_settings['lineupid'] = setting_value
                logging.info('Migrated lineupcode "%s" to lineupid', setting_value)
            else:
                # Default fallback to auto
                if 'lineupid' not in valid_settings:
                    valid_settings['lineupid'] = 'auto'
        elif setting_id in ['lineup', 'device']:
            # These are now auto-generated, no migration needed
            logging.debug('Deprecated setting %s will be auto-generated', setting_id)

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

        # Validate log rotation settings
        self._validate_logrotate_settings()

    def _set_defaults(self):
        """Set default values for missing settings"""
        # Check if langdetect is available for smart default
        langdetect_available = self._check_langdetect_available()

        defaults = {
            'lineupid': 'auto',  # SIMPLIFIED: Single lineup setting
            'days': '1',
            'redays': '1',
            'refresh': '48',
            'slist': '',
            'stitle': False,
            'xdetails': True,
            'xdesc': True,
            'langdetect': langdetect_available,
            'epgenre': '3',
            'epicon': '1',
            'tvhoff': True,
            'usern': '',
            'passw': '',
            'tvhurl': '127.0.0.1',
            'tvhport': '9981',
            'tvhmatch': True,
            'chmatch': True,
            'logrotate_enabled': True,
            'logrotate_interval': 'weekly',
            'logrotate_keep': '14',
        }

        for key, default_value in defaults.items():
            if key not in self.settings or self.settings[key] is None:
                self.settings[key] = default_value
                logging.debug('Set default: %s = %s', key, default_value)

    def _check_langdetect_available(self) -> bool:
        """Check if langdetect library is available"""
        try:
            import langdetect
            return True
        except ImportError:
            return False

    def _clean_and_migrate_config(self, valid_settings: Dict[str, str], deprecated_list: List[str]):
        """Clean and migrate configuration file"""
        try:
            if not deprecated_list:
                logging.debug('No deprecated settings found - configuration file is clean')
                return

            # Create backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{self.config_file}.backup.{timestamp}"
            shutil.copy2(self.config_file, backup_file)
            logging.info('Created configuration backup: %s', backup_file)

            # Write cleaned and migrated configuration
            self._write_clean_config(valid_settings)

            logging.info('Configuration cleaned and migrated successfully')
            logging.info('  Removed/migrated %d deprecated settings: %s',
                        len(deprecated_list), ', '.join(deprecated_list))
            logging.info('  Updated to version 5 with simplified lineupid configuration')

        except Exception as e:
            logging.error('Error cleaning configuration file: %s', str(e))
            logging.error('Continuing with existing configuration...')

    def _write_clean_config(self, valid_settings: Dict[str, str]):
        """Write cleaned configuration file"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write('<settings version="5">\n')  # Updated version

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

    def _validate_logrotate_settings(self):
        """Validate log rotation configuration settings"""
        # Validate logrotate_interval
        interval = self.settings.get('logrotate_interval', 'weekly').lower()
        valid_intervals = ['daily', 'weekly', 'monthly']

        if interval not in valid_intervals:
            logging.warning('Invalid log rotation interval "%s", using default "weekly"', interval)
            self.settings['logrotate_interval'] = 'weekly'
        else:
            self.settings['logrotate_interval'] = interval

        # Validate logrotate_keep
        keep_setting = self.settings.get('logrotate_keep', '14')
        try:
            keep_count = int(keep_setting)
            if keep_count < 0 or keep_count > 365:
                logging.warning('Invalid log rotation keep count %d, using default 14', keep_count)
                self.settings['logrotate_keep'] = '14'
            elif keep_count == 0:
                logging.info('Log rotation keep count set to 0 - unlimited backup files')
        except (ValueError, TypeError):
            logging.warning('Invalid log rotation keep setting "%s", using default 14', keep_setting)
            self.settings['logrotate_keep'] = '14'

    def display_lineup_detection_test(self, postal_code: str, debug_mode: bool = False) -> bool:
        """
        Display lineup detection test results - simplified by default, detailed in debug mode

        Args:
            postal_code: Postal/ZIP code to test
            debug_mode: Whether to show detailed debug information

        Returns:
            bool: True if valid postal code, False otherwise
        """
        # Validate postal code format
        is_valid, country, clean_postal = self.validate_postal_code_format(postal_code)

        if not is_valid:
            print(f"❌ ERROR: Invalid postal/ZIP code format: {postal_code}")
            print("   Expected formats:")
            print("   - US ZIP code: 90210")
            print("   - Canadian postal: J3B1M4 or J3B 1M4")
            return False

        # Get country info
        country_name = 'United States' if country == 'USA' else 'Canada'

        # Generate lineup IDs using new simplified method
        auto_lineup_config = self._get_auto_lineup_config(clean_postal, country)

        # Display results based on mode
        if debug_mode:
            # Mode debug: affichage simplifiÃ© mais avec infos techniques
            print("=" * 70)
            print("GRACENOTE2EPG - LINEUP DETECTION (DEBUG MODE)")
            print("=" * 70)
            self._display_debug_output(postal_code, clean_postal, country_name, country, auto_lineup_config)
        else:
            # Mode normal: affichage simplifiÃ©
            self._display_simple_output(auto_lineup_config, country, clean_postal)

        return True

    def validate_postal_code_format(self, postal_code: str) -> Tuple[bool, str, str]:
        """
        Validate postal code format and return country info

        Args:
            postal_code: Raw postal code input

        Returns:
            tuple: (is_valid, country_code, clean_postal)
        """
        clean_postal = postal_code.replace(' ', '').upper()

        if clean_postal.isdigit() and len(clean_postal) == 5:
            return True, 'USA', clean_postal
        elif re.match(r'^[A-Z][0-9][A-Z][0-9][A-Z][0-9]$', clean_postal):
            return True, 'CAN', clean_postal
        else:
            return False, '', clean_postal

    def _display_simple_output(self, lineup_config: Dict, country: str, clean_postal: str):
        """Display simplified output for normal mode"""
        print(f"🌐 GRACENOTE API URL PARAMETERS:")
        print(f"   lineupId={lineup_config['api_lineup_id']}")
        print(f"   country={country}")
        print(f"   postalCode={clean_postal}")
        print()

        print(f"✅ VALIDATION URLs (manual verification):")
        print(f"   Auto-generated: {lineup_config['tvtv_url']}")
        print(f"   Manual lookup:")
        if country == 'CAN':
            print(f"     1. Go to https://www.tvtv.ca/")
            print(f"     2. Enter postal code: {clean_postal}")
            print(f"     3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → URL shows lu{lineup_config['tvtv_lineup_id']}")
            print(f"     3b. For Cable/Sat: Select provider → URL shows lu{country}-[ProviderID]-X")
        else:
            print(f"     1. Go to https://www.tvtv.us/")
            print(f"     2. Enter ZIP code: {clean_postal}")
            print(f"     3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → URL shows lu{lineup_config['tvtv_lineup_id']}")
            print(f"     3b. For Cable/Sat: Select provider → URL shows lu{country}-[ProviderID]-X")
        print()

        print(f"🔗 GRACENOTE API URL FOR TESTING:")
        example_time = "1755432000"  # Example timestamp
        test_url = (
            f"https://tvlistings.gracenote.com/api/grid?"
            f"aid=orbebb&"
            f"country={country}&"
            f"postalCode={clean_postal}&"
            f"time={example_time}&"
            f"timespan=3&"
            f"isOverride=true&"
            f"userId=-&"
            f"lineupId={lineup_config['api_lineup_id']}&"
            f"headendId=lineupId"
        )
        print(f"   {test_url}")

    def _display_debug_output(self, postal_code: str, clean_postal: str, country_name: str,
                             country: str, lineup_config: Dict):
        """Display debug output with technical information"""
        print(f"📍 LOCATION INFORMATION:")
        print(f"   Normalized code:   {clean_postal}")
        print(f"   Detected country:  {country_name} ({country})")
        print()

        print(f"🌐 GRACENOTE API URL PARAMETERS:")
        print(f"   lineupId={lineup_config['api_lineup_id']}")
        print(f"   country={country}")
        print(f"   postalCode={clean_postal}")
        print()

        print(f"✅ VALIDATION URLs (manual verification):")
        print(f"   Auto-generated: {lineup_config['tvtv_url']}")
        print(f"   Note: OTA format is {lineup_config['tvtv_lineup_id']} (country + OTA + postal, no -DEFAULT suffix)")
        print(f"   Cable/Satellite providers use different format: {country}-[ProviderID]-X")
        print(f"   Manual lookup:")
        if country == 'CAN':
            print(f"     1. Go to https://www.tvtv.ca/")
            print(f"     2. Enter postal code: {clean_postal}")
            print(f"     3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → URL shows lu{lineup_config['tvtv_lineup_id']}")
            print(f"     3b. For Cable/Sat: Select provider → URL shows lu{country}-[ProviderID]-X")
        else:
            print(f"     1. Go to https://www.tvtv.us/")
            print(f"     2. Enter ZIP code: {clean_postal}")
            print(f"     3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → URL shows lu{lineup_config['tvtv_lineup_id']}")
            print(f"     3b. For Cable/Sat: Select provider → URL shows lu{country}-[ProviderID]-X")
        print()

        print(f"🔗 GRACENOTE API URLs FOR TESTING:")
        example_time = "1755432000"  # Example timestamp
        test_url = (
            f"https://tvlistings.gracenote.com/api/grid?"
            f"aid=orbebb&"
            f"country={country}&"
            f"postalCode={clean_postal}&"
            f"time={example_time}&"
            f"timespan=3&"
            f"isOverride=true&"
            f"userId=-&"
            f"lineupId={lineup_config['api_lineup_id']}&"
            f"headendId=lineupId"
        )
        print(f"   {test_url}")
        print()

        print(f"📊 GRACENOTE API - OTHER COMMON PARAMETERS:")
        print(f"   • &device=[-|X]                    Device type: - for Over-the-Air, X for cable/satellite")
        print(f"   • &pref=16%2C128                   Preference codes (16,128): channel lineup preferences")
        print(f"   • &timezone=America%2FNew_York     User timezone for schedule times (URL-encoded)")
        print(f"   • &languagecode=en-us              Content language: en-us, fr-ca, es-us, etc.")
        print(f"   • &TMSID=                          Tribune Media Services ID (legacy, usually empty)")
        print(f"   • &AffiliateID=lat                 Partner/affiliate identifier (lat=local affiliate)")
        print()

        print(f"💥 MANUAL DOWNLOAD:")
        print(f"⚠️  NOTE: Using browser-like headers to bypass AWS WAF")
        print()
        print(f"curl -s -H \"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\" \\")
        print(f"     -H \"Accept: application/json, text/html, application/xhtml+xml, */*\" \\")
        print(f"     \"{test_url}\" > out.json")
        print()

        print(f"🔧 RECOMMENDED CONFIGURATION:")
        country_full = 'Canada' if country == 'CAN' else 'United States'
        print(f"   <!-- Simplified configuration (auto-detection) -->")
        print(f"   <setting id=\"zipcode\">{clean_postal}</setting>")
        print(f"   <setting id=\"lineupid\">auto</setting>")
        print()
        print(f"   <!-- Alternative: Copy tvtv.com lineup ID directly -->")
        print(f"   <!-- <setting id=\"lineupid\">{lineup_config['tvtv_lineup_id']}</setting> -->")
        print()
        print(f"   <!-- For Cable/Satellite providers: -->")
        print(f"   <!-- <setting id=\"lineupid\">{country}-[ProviderID]-X</setting> -->")
        print(f"   <!-- Example: <setting id=\"lineupid\">{country}-0005993-X</setting> for Videotron -->")
        print()

        print("=" * 70)
        print("💡 NEXT STEPS:")
        print("1. Verify the validation URLs show your local channels")
        print("2. Update your gracenote2epg.xml with the recommended configuration")
        print("3. Run: tv_grab_gracenote2epg --days 1 --console")
        print("4. Look for 'Auto-detected lineupID' in the logs")
        print("5. Confirm no HTTP 400 errors in download attempts")
        print("=" * 70)

    def normalize_lineup_id(self, lineupid: str, country: str, postal_code: str) -> str:
        """
        Normalize lineup ID to API format

        Args:
            lineupid: Raw lineup ID from config (auto, tvtv format, or complete)
            country: Country code (USA/CAN)
            postal_code: Postal/ZIP code

        Returns:
            Normalized lineup ID for API use
        """
        if not lineupid or lineupid.lower() == "auto":
            # Auto-generate OTA lineup ID
            return f"{country}-OTA{postal_code}-DEFAULT"

        elif not lineupid.endswith("-DEFAULT") and not lineupid.endswith("-X"):
            # Format from tvtv.com (e.g. CAN-OTAJ3B1M4) → Add -DEFAULT for API
            return f"{lineupid}-DEFAULT"

        else:
            # Already complete format (e.g. CAN-OTAJ3B1M4-DEFAULT or CAN-0005993-X)
            return lineupid

    def detect_device_type(self, normalized_lineup_id: str) -> str:
        """
        Auto-detect device type from lineup ID

        Args:
            normalized_lineup_id: Normalized lineup ID

        Returns:
            Device type: "-" for OTA, "X" for cable/satellite
        """
        if "OTA" in normalized_lineup_id:
            return "-"  # Over-the-Air
        elif normalized_lineup_id.endswith("-X"):
            return "X"  # Cable/Satellite
        else:
            return "-"  # Default to OTA

    def generate_description(self, normalized_lineup_id: str, country: str) -> str:
        """
        Auto-generate description from lineup ID

        Args:
            normalized_lineup_id: Normalized lineup ID
            country: Country code

        Returns:
            Human-readable description
        """
        country_name = 'United States' if country == 'USA' else 'Canada'

        if "OTA" in normalized_lineup_id:
            return f"Local Over the Air Broadcast ({country_name})"
        elif normalized_lineup_id.endswith("-X"):
            return f"Cable/Satellite Provider ({country_name})"
        else:
            return f"TV Lineup ({country_name})"

    def get_lineup_config(self) -> Dict[str, str]:
        """Get lineup configuration with automatic normalization and detection"""
        lineupid = self.settings.get('lineupid', 'auto')
        postal_code = self.settings.get('zipcode', '')
        country = self.get_country()

        # Normalize lineup ID
        normalized_lineup_id = self.normalize_lineup_id(lineupid, country, postal_code)

        # Auto-detect device type
        device_type = self.detect_device_type(normalized_lineup_id)

        # Auto-generate description
        description = self.generate_description(normalized_lineup_id, country)

        # Determine if this was auto-detected
        auto_detected = not lineupid or lineupid.lower() == "auto"

        # REMOVED: Logging moved to log_config_summary() to avoid duplication

        return {
            'lineup_id': normalized_lineup_id,      # Full API format
            'headend_id': 'lineupId',               # Always literal 'lineupId' for API
            'device_type': device_type,             # Auto-detected device type
            'description': description,             # Auto-generated description
            'auto_detected': auto_detected,
            'original_config': lineupid,            # Original config value
            'country': country,
            'postal_code': postal_code
        }

    def _get_auto_lineup_config(self, postal_code: str, country: str) -> Dict[str, str]:
        """Get auto-generated lineup configuration for display purposes"""
        # Generate OTA lineup IDs
        base_lineup = f"OTA{postal_code}"
        tvtv_lineup_id = f"{country}-{base_lineup}"
        api_lineup_id = f"{country}-{base_lineup}-DEFAULT"

        # Generate tvtv.com URL
        if country == 'CAN':
            postal_for_url = postal_code.lower()
            tvtv_url = f"https://www.tvtv.ca/qc/saint-jean-sur-richelieu/{postal_for_url}/lu{tvtv_lineup_id}"
        else:
            tvtv_url = f"https://www.tvtv.us/ca/beverly-hills/{postal_code}/lu{tvtv_lineup_id}"

        return {
            'tvtv_lineup_id': tvtv_lineup_id,       # Format for tvtv.com
            'api_lineup_id': api_lineup_id,         # Format for API
            'tvtv_url': tvtv_url,                   # Complete tvtv.com URL
            'device_type': '-',                     # OTA device type
            'country': country,
            'postal_code': postal_code
        }

    def get_logrotate_config(self) -> Dict[str, Any]:
        """Get log rotation configuration"""
        return {
            'enabled': self.settings.get('logrotate_enabled', True),
            'interval': self.settings.get('logrotate_interval', 'weekly'),
            'keep_files': int(self.settings.get('logrotate_keep', '14'))
        }

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

        # Log simplified lineup configuration
        lineup_config = self.get_lineup_config()
        logging.info('  lineupid: %s → %s', lineup_config['original_config'], lineup_config['lineup_id'])
        logging.info('  device: %s (auto-detected)', lineup_config['device_type'])
        logging.info('  description: %s', lineup_config['description'])

        logging.info('  xdetails (download extended data): %s', self.settings.get('xdetails'))
        logging.info('  xdesc (use extended descriptions): %s', self.settings.get('xdesc'))
        logging.info('  langdetect (automatic language detection): %s', self.settings.get('langdetect'))

        # Log cache refresh configuration
        refresh_hours = self.get_refresh_hours()
        if refresh_hours == 0:
            logging.info('  refresh: disabled (use all cached data)')
        else:
            logging.info('  refresh: %d hours (refresh first %d hours of guide)', refresh_hours, refresh_hours)

        # Log rotation configuration
        logrotate_config = self.get_logrotate_config()
        if logrotate_config['enabled']:
            logging.info('  log rotation: enabled (%s, keep %d files)',
                        logrotate_config['interval'], logrotate_config['keep_files'])
        else:
            logging.info('  log rotation: disabled')

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
