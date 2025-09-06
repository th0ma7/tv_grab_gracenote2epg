"""
gracenote2epg.gracenote2epg_config - Configuration management

Handles XML configuration file parsing, validation, automatic cleanup,
and migration from older versions. Now includes simplified lineupid configuration
that automatically normalizes tvtv.com formats and detects device type.
Updated with unified retention policies for logs and XMLTV backups.
"""

import logging
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class ConfigManager:
    """Manages gracenote2epg configuration file"""

    # Default configuration template with unified cache and retention policies
    DEFAULT_CONFIG = """<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <!-- Basic guide settings -->
  <setting id="zipcode">92101</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">7</setting>

  <!-- Station filtering -->
  <setting id="slist"></setting>
  <setting id="stitle">false</setting>

  <!-- Extended details and language detection -->
  <setting id="xdetails">true</setting>
  <setting id="xdesc">true</setting>
  <setting id="langdetect">true</setting>

  <!-- Display options -->
  <setting id="epgenre">3</setting>
  <setting id="epicon">1</setting>

  <!-- TVheadend integration -->
  <setting id="tvhoff">true</setting>
  <setting id="usern"></setting>
  <setting id="passw"></setting>
  <setting id="tvhurl">127.0.0.1</setting>
  <setting id="tvhport">9981</setting>
  <setting id="tvhmatch">true</setting>
  <setting id="chmatch">true</setting>

  <!-- Cache and retention policies -->
  <setting id="redays">7</setting>
  <setting id="refresh">48</setting>
  <setting id="logrotate">true</setting>
  <setting id="relogs">30</setting>
  <setting id="rexmltv">7</setting>
</settings>"""

    # Valid settings and their types
    VALID_SETTINGS = {
        # Required settings
        "zipcode": str,
        # Single lineup setting
        "lineupid": str,
        # Basic settings
        "days": str,
        # Station filtering
        "slist": str,
        "stitle": bool,
        # Extended details
        "xdetails": bool,
        "xdesc": bool,
        "langdetect": bool,
        # Display options
        "epgenre": str,
        "epicon": str,
        # TVheadend integration
        "tvhoff": bool,
        "usern": str,
        "passw": str,
        "tvhurl": str,
        "tvhport": str,
        "tvhmatch": bool,
        "chmatch": bool,
        # Cache and retention policies
        "redays": str,
        "refresh": str,
        "logrotate": str,
        "relogs": str,
        "rexmltv": str,
    }

    # DEPRECATED settings for simplified removal (no migration)
    DEPRECATED_SETTINGS = {
        "auto_lineup": "lineupid",
        "lineupcode": "lineupid",
        "lineup": "lineupid",
        "device": "lineupid",  # Auto-detected now
        # Old log rotation settings
        "logrotate_enabled": "logrotate",
        "logrotate_interval": "logrotate",
        "logrotate_keep": "relogs",
        # Intermediate version settings
        "log_rotation": "logrotate",
        "log_retention": "relogs",
        "xmltv_backup_retention": "rexmltv",
    }

    # Settings order for clean output
    SETTINGS_ORDER = [
        "zipcode",
        "lineupid",
        "days",
        "slist",
        "stitle",
        "xdetails",
        "xdesc",
        "langdetect",
        "epgenre",
        "epicon",
        "tvhoff",
        "usern",
        "passw",
        "tvhurl",
        "tvhport",
        "tvhmatch",
        "chmatch",
        "redays",
        "refresh",
        "logrotate",
        "relogs",
        "rexmltv",
    ]

    def __init__(self, config_file: Path):
        self.config_file = Path(config_file)
        self.settings: Dict[str, Any] = {}
        self.version: str = "5"  # Updated version for new unified format
        self.zipcode_extracted_from_lineupid: bool = False  # Track zipcode extraction for logging
        self.config_changes: Dict[str, str] = {}  # Track command line changes for clean logging
        self._backup_file_created: Optional[str] = None  # Track backup file creation
        self._original_file_settings: Dict[str, Any] = {}  # Store original config file values

    def load_config(
        self,
        location_code: Optional[str] = None,
        location_source: str = "explicit",
        location_extracted_from: Optional[str] = None,
        days: Optional[int] = None,
        langdetect: Optional[bool] = None,
        refresh_hours: Optional[int] = None,
        lineupid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Load and validate configuration file"""

        # Initialize backup tracking
        self._backup_file_created = None

        # Create default config if doesn't exist
        if not self.config_file.exists():
            self._create_default_config()

        # Parse configuration
        self._parse_config_file()

        # Store original values from config file before any command line modifications
        self._original_file_settings = self.settings.copy()

        # Track original values for clearer logging
        original_zipcode = self.settings.get("zipcode", "").strip()
        original_lineupid = self.settings.get("lineupid", "auto").strip()

        # Track changes for logging
        self.config_changes = {}
        self.zipcode_extracted_from_lineupid = False

        # Override with command line arguments (TEMPORARY for this execution only)
        if location_code:
            if not original_zipcode:  # Empty in config
                if location_source == "extracted" and location_extracted_from:
                    self.config_changes["zipcode"] = (
                        f"(empty) → {location_code} (extracted from {location_extracted_from})"
                    )
                else:
                    self.config_changes["zipcode"] = (
                        f"(empty) → {location_code} (from command line)"
                    )
            elif original_zipcode != location_code:
                if location_source == "extracted" and location_extracted_from:
                    self.config_changes["zipcode"] = (
                        f"{original_zipcode} → {location_code} (extracted from {location_extracted_from})"
                    )
                    # Configuration mismatch detected and resolved
                    logging.warning("Configuration mismatch detected and resolved:")
                    logging.warning("  Configured zipcode: %s", original_zipcode)
                    # Normalize display (remove spaces)
                    normalized_location = location_code.replace(" ", "")
                    logging.warning(
                        "  LineupID contains: %s (from %s)",
                        normalized_location,
                        location_extracted_from,
                    )
                    logging.warning(
                        "  Resolution: Using zipcode from lineupid (%s takes precedence)",
                        location_extracted_from,
                    )
                else:
                    self.config_changes["zipcode"] = (
                        f"{original_zipcode} → {location_code} (overridden)"
                    )
            self.settings["zipcode"] = location_code

        if days:
            original_days = self.settings.get("days", "1")
            if original_days != str(days):
                self.config_changes["days"] = f"{original_days} → {days}"
            self.settings["days"] = str(days)

        if langdetect is not None:
            original_langdetect = self.settings.get("langdetect", True)
            if original_langdetect != langdetect:
                self.config_changes["langdetect"] = f"{original_langdetect} → {langdetect}"
            self.settings["langdetect"] = langdetect

        if refresh_hours is not None:
            original_refresh = self.settings.get("refresh", "48")
            if original_refresh != str(refresh_hours):
                self.config_changes["refresh"] = f"{original_refresh} → {refresh_hours}"
            self.settings["refresh"] = str(refresh_hours)

        if lineupid is not None:
            if original_lineupid != lineupid:
                self.config_changes["lineupid"] = f"{original_lineupid} → {lineupid}"
            self.settings["lineupid"] = lineupid

        # Validate configuration consistency before processing
        self._validate_config_consistency()

        # Validate required settings
        self._validate_config()

        # Set defaults for missing settings (this will update config file if needed)
        # This uses the ORIGINAL file values, not the command line modified ones
        self._set_defaults()

        return self.settings

    def _validate_config_consistency(self):
        """Validate configuration consistency between zipcode and lineupid"""
        zipcode = self.settings.get("zipcode", "").strip()
        lineupid = self.settings.get("lineupid", "auto").strip()

        # If lineupid is not 'auto', check for consistency with zipcode
        if lineupid.lower() != "auto":
            extracted_location = self._extract_location_from_lineupid(lineupid)

            if extracted_location and zipcode:
                # Both zipcode in config and extractable location from lineupid
                clean_extracted = extracted_location.replace(" ", "").upper()
                clean_zipcode = zipcode.replace(" ", "").upper()

                if clean_extracted != clean_zipcode:
                    logging.error("Configuration mismatch detected:")
                    logging.error("  Configured zipcode: %s", zipcode)
                    # Normalize display (remove spaces)
                    normalized_extracted = extracted_location.replace(" ", "")
                    logging.error(
                        "  LineupID contains: %s (extracted from %s)",
                        normalized_extracted,
                        lineupid,
                    )
                    logging.error("  These must match for consistent operation")
                    raise ValueError(
                        f'Configuration mismatch: zipcode "{zipcode}" conflicts with '
                        f'lineupid "{lineupid}" (contains {normalized_extracted}). '
                        "Either use auto-detection with zipcode or ensure consistency."
                    )
                else:
                    logging.debug(
                        'Configuration consistency verified: zipcode "%s" matches lineupid "%s"',
                        zipcode,
                        lineupid,
                    )

            elif extracted_location and not zipcode:
                # Lineupid contains location but no zipcode configured - auto-extract
                self.settings.get("zipcode", "").strip()
                self.settings["zipcode"] = extracted_location.replace(" ", "")
                self.zipcode_extracted_from_lineupid = True
                # Normalize display (remove spaces)
                normalized_extracted = extracted_location.replace(" ", "")
                self.config_changes["zipcode"] = (
                    f"(empty) → {normalized_extracted} (extracted from {lineupid})"
                )
                # Normalize display (remove spaces)
                logging.info(
                    "Auto-extracted zipcode from lineupid: %s → %s", lineupid, normalized_extracted
                )

    def _extract_location_from_lineupid(self, lineupid: str) -> Optional[str]:
        """Extract postal/ZIP code from lineup ID if it's in OTA format"""
        # Pattern for OTA lineups: COUNTRY-OTA<LOCATION>[-DEFAULT]
        ota_pattern = re.compile(r"^(CAN|USA)-OTA([A-Z0-9]+)(?:-DEFAULT)?$", re.IGNORECASE)

        match = ota_pattern.match(lineupid.strip())
        if match:
            country = match.group(1).upper()
            location = match.group(2).upper()

            # Validate extracted location format
            if country == "CAN":
                # Canadian postal: should be A1A1A1 format
                if re.match(r"^[A-Z][0-9][A-Z][0-9][A-Z][0-9]$", location):
                    # Format as A1A 1A1 (with space)
                    return f"{location[:3]} {location[3:]}"
            elif country == "USA":
                # US ZIP: should be 5 digits
                if re.match(r"^[0-9]{5}$", location):
                    return location

        return None

    def _create_default_config(self):
        """Create default configuration file with proper permissions"""
        logging.info("Creating default configuration: %s", self.config_file)

        # Ensure directory exists with 755 permissions (rwxr-xr-x)
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        except Exception:
            # Fallback: create without mode specification (depends on umask)
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Write default configuration
        with open(self.config_file, "w", encoding="utf-8") as f:
            f.write(self.DEFAULT_CONFIG)

    def _parse_config_file(self):
        """Parse XML configuration file with simplified cleanup and automatic ordering"""
        try:
            tree = ET.parse(self.config_file)
            root = tree.getroot()

            logging.info("Reading configuration from: %s", self.config_file)

            # Get version - default to version 5 for new unified format
            self.version = root.attrib.get("version", "5")
            logging.info("Configuration version: %s", self.version)

            # Parse settings with simplified validation
            valid_settings = {}
            deprecated_settings = []
            unknown_settings = []
            migration_needed = False

            # Track original order for comparison
            original_order = []

            for setting in root.findall("setting"):
                setting_id = setting.get("id")
                original_order.append(setting_id)

                # Get value based on version
                if self.version == "2":
                    setting_value = setting.text
                else:
                    # Version 3+: try 'value' attribute first, then text
                    setting_value = setting.get("value")
                    if setting_value is None:
                        setting_value = setting.text
                    if setting_value == "":
                        setting_value = None

                logging.debug("Config setting: %s = %s", setting_id, setting_value)

                # Categorize settings - SIMPLIFIED
                if setting_id in self.VALID_SETTINGS:
                    # Valid setting - keep as-is
                    valid_settings[setting_id] = setting_value

                elif setting_id in self.DEPRECATED_SETTINGS:
                    # Deprecated setting - mark for removal (no migration)
                    deprecated_settings.append(setting_id)
                    migration_needed = True
                    logging.debug("Deprecated setting found: %s (will be removed)", setting_id)

                elif setting_id.startswith("desc") and re.match(r"desc[0-9]{2}", setting_id):
                    # Old description formatting - mark for removal
                    deprecated_settings.append(setting_id)
                    migration_needed = True

                elif setting_id == "useragent":
                    # Old useragent setting - mark for removal
                    deprecated_settings.append(setting_id)
                    migration_needed = True

                else:
                    # Unknown setting - mark for removal
                    unknown_settings.append(setting_id)
                    migration_needed = True
                    logging.warning(
                        "Unknown configuration setting: %s = %s (will be removed)",
                        setting_id,
                        setting_value,
                    )

            # Store valid settings in self.settings FIRST
            self._process_settings(valid_settings)

            # Check if ordering needs to be corrected
            ordering_needed = self._check_ordering_needed(original_order, valid_settings)

            # Clean/reorder configuration if needed, but preserve existing values
            if migration_needed or ordering_needed:
                all_removed = deprecated_settings + unknown_settings
                reason = []
                if all_removed:
                    reason.append(f"removed {len(all_removed)} deprecated/unknown settings")
                if ordering_needed:
                    reason.append("reordered settings for consistency")

                logging.info("Configuration update needed: %s", ", ".join(reason))
                self._clean_and_migrate_config(valid_settings, all_removed, ordering_needed)

        except ET.ParseError as e:
            logging.error("Cannot parse configuration file %s: %s", self.config_file, e)
            raise
        except Exception as e:
            logging.error("Error reading configuration file %s: %s", self.config_file, e)
            raise

    def _check_ordering_needed(
        self, original_order: List[str], valid_settings: Dict[str, str]
    ) -> bool:
        """Check if configuration settings need to be reordered"""
        # Filter original order to only include valid settings
        current_valid_order = [
            setting_id for setting_id in original_order if setting_id in valid_settings
        ]

        # Get expected order for valid settings
        expected_order = [
            setting_id for setting_id in self.SETTINGS_ORDER if setting_id in valid_settings
        ]

        # Add any valid settings not in SETTINGS_ORDER (alphabetically)
        remaining_settings = sorted(
            [setting_id for setting_id in valid_settings if setting_id not in self.SETTINGS_ORDER]
        )
        expected_order.extend(remaining_settings)

        # Compare orders
        if current_valid_order != expected_order:
            logging.debug("Settings order differs from recommended:")
            logging.debug("  Current:  %s", current_valid_order)
            logging.debug("  Expected: %s", expected_order)
            return True

        return False

    def _process_settings(self, settings_dict: Dict[str, str]):
        """Process and type-convert settings"""
        for setting_id, setting_value in settings_dict.items():
            if setting_id in self.VALID_SETTINGS:
                expected_type = self.VALID_SETTINGS[setting_id]

                if expected_type == bool:
                    self.settings[setting_id] = self._parse_boolean(setting_value)
                elif expected_type == str:
                    self.settings[setting_id] = setting_value if setting_value is not None else ""
                else:
                    self.settings[setting_id] = setting_value

                logging.debug(
                    "Processed setting: %s = %s (%s)",
                    setting_id,
                    self.settings[setting_id],
                    expected_type.__name__,
                )

    def _parse_boolean(self, value: Any) -> bool:
        """Parse boolean values from configuration"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def _validate_config(self):
        """Validate required configuration settings with enhanced error messages"""
        # Check required zipcode
        zipcode = self.settings.get("zipcode", "").strip()
        if not zipcode:
            logging.error("Zipcode is required but not found in configuration")
            logging.error("Available settings: %s", list(self.settings.keys()))
            raise ValueError("Missing required zipcode in configuration")

        # Enhanced validation for auto-detection lineup
        lineupid = self.settings.get("lineupid", "auto").strip().lower()
        if lineupid == "auto":
            # Validate zipcode format for auto-detection
            clean_code = zipcode.replace(" ", "")
            is_valid_us = clean_code.isdigit() and len(clean_code) == 5
            is_valid_ca = bool(re.match(r"^[A-Z][0-9][A-Z][0-9][A-Z][0-9]$", clean_code))

            if not (is_valid_us or is_valid_ca):
                logging.error("Auto-detection (lineupid=auto) requires a valid ZIP/postal code")
                logging.error('Current zipcode: "%s"', zipcode)
                logging.error("Expected formats:")
                logging.error("  - US ZIP code: 90210")
                logging.error("  - Canadian postal: J3B1M4 or J3B 1M4")
                raise ValueError(
                    f'Invalid zipcode "{zipcode}" for auto-detection. '
                    "Auto-detection requires valid US ZIP (12345) or Canadian postal (A1A1A1)"
                )

            logging.debug('Zipcode "%s" validated for auto-detection', zipcode)

        # Validate refresh hours
        refresh_setting = self.settings.get("refresh", "48")
        try:
            refresh_hours = int(refresh_setting)
            if refresh_hours < 0 or refresh_hours > 168:
                logging.warning("Invalid refresh hours %d, using default 48", refresh_hours)
                self.settings["refresh"] = "48"
        except (ValueError, TypeError):
            logging.warning('Invalid refresh setting "%s", using default 48', refresh_setting)
            self.settings["refresh"] = "48"

        # Validate cache and retention policies
        self._validate_cache_and_retention_policies()

    def _set_defaults(self):
        """Set default values for missing settings and update config file if needed"""
        # Check if langdetect is available for smart default
        langdetect_available = self._check_langdetect_available()

        defaults = {
            "lineupid": "auto",  # Simplified single lineup setting
            "days": "1",
            "slist": "",
            "stitle": False,
            "xdetails": True,
            "xdesc": True,
            "langdetect": langdetect_available,
            "epgenre": "3",
            "epicon": "1",
            "tvhoff": True,
            "usern": "",
            "passw": "",
            "tvhurl": "127.0.0.1",
            "tvhport": "9981",
            "tvhmatch": True,
            "chmatch": True,
            # Cache and retention policies - CORRECTED DEFAULTS
            "redays": "1",  # Will be validated to be >= days
            "refresh": "48",
            "logrotate": "true",  # true = daily by default
            "relogs": "30",  # 30 days by default (NOT 98!)
            "rexmltv": "7",  # 7 days by default
        }

        # Check what's missing from the ORIGINAL config file (not current self.settings)
        original_settings = getattr(self, "_original_file_settings", self.settings)

        added_defaults = []
        settings_to_add = {}

        for key, default_value in defaults.items():
            # Check if missing from ORIGINAL file settings
            if key not in original_settings or original_settings[key] is None:
                # Add to current settings for this execution
                if key not in self.settings:
                    self.settings[key] = default_value

                # Track for file update
                settings_to_add[key] = default_value
                added_defaults.append(f"{key}={default_value}")
                logging.debug("Set default: %s = %s", key, default_value)

        # If we added defaults, update the configuration file AND notify user
        if added_defaults:
            logging.info("Added missing settings with defaults: %s", ", ".join(added_defaults))

            # Update the configuration file to include ONLY the new defaults
            self._update_config_with_missing_defaults(settings_to_add)

            # User notification about the upgrade
            self._notify_config_upgrade(added_defaults)

    def _update_config_with_missing_defaults(self, new_settings: Dict[str, Any]):
        """Update the configuration file to include ONLY newly added default settings"""
        try:
            # Re-read the original config file to get the unmodified values
            tree = ET.parse(self.config_file)
            root = tree.getroot()

            # Get existing settings to preserve their ORIGINAL values (not from self.settings)
            existing_settings = {}
            for setting in root.findall("setting"):
                setting_id = setting.get("id")

                # Get value based on version (same logic as in _parse_config_file)
                if self.version == "2":
                    setting_value = setting.text
                else:
                    setting_value = setting.get("value")
                    if setting_value is None:
                        setting_value = setting.text
                    if setting_value == "":
                        setting_value = None

                # Only include valid settings that we want to preserve
                if setting_id in self.VALID_SETTINGS:
                    existing_settings[setting_id] = setting_value

            # Add only the truly new settings (those not in original file)
            for key, value in new_settings.items():
                if key not in existing_settings:
                    existing_settings[key] = (
                        str(value)
                        if not isinstance(value, bool)
                        else ("true" if value else "false")
                    )
                    logging.debug(
                        "Adding new setting to config file: %s = %s", key, existing_settings[key]
                    )

            # Write the complete configuration with preserved original values
            self._write_clean_config(existing_settings)

            logging.info(
                "Configuration file updated: preserved %d existing settings, added %d new settings",
                len(existing_settings) - len(new_settings),
                len(new_settings),
            )

        except Exception as e:
            logging.error("Error updating configuration file with defaults: %s", str(e))

    def _notify_config_upgrade(self, added_defaults: List[str]):
        """Notify user about configuration upgrade with visible warning"""
        # Simplified warning message with documentation reference
        backup_file = getattr(self, "_backup_file_created", None)

        logging.warning("=" * 60)
        logging.warning("CONFIGURATION UPGRADED TO VERSION 5")
        if backup_file:
            logging.warning("Backup created: %s", backup_file)
        logging.warning("Updated settings: %s", self.config_file)
        logging.warning("Documentation: https://github.com/th0ma7/gracenote2epg")
        logging.warning("=" * 60)

    def _check_langdetect_available(self) -> bool:
        """Check if langdetect library is available"""
        try:
            return True
        except ImportError:
            return False

    def _clean_and_migrate_config(
        self,
        valid_settings: Dict[str, str],
        removed_settings: List[str],
        ordering_needed: bool = False,
    ):
        """Clean and reorder configuration file - ENHANCED VERSION"""
        try:
            # Create backup only if we're making changes
            if removed_settings or ordering_needed:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{self.config_file}.backup.{timestamp}"
                shutil.copy2(self.config_file, backup_file)
                logging.info("Created configuration backup: %s", backup_file)

                # Store backup file path for user notification
                self._backup_file_created = backup_file

            # Write cleaned and ordered configuration
            self._write_clean_config(valid_settings)

            # Log what was done at INFO level (not WARNING)
            changes = []
            if removed_settings:
                changes.append(f"removed {len(removed_settings)} deprecated/unknown settings")
            if ordering_needed:
                changes.append("reordered settings for consistency")

            logging.info("Configuration updated successfully: %s", ", ".join(changes))

            if removed_settings:
                logging.info("  Removed settings: %s", ", ".join(removed_settings))

            logging.info("  Updated to version 5 with unified retention policies")

            # User notification about cleanup/migration - simplified
            if removed_settings:
                self._notify_config_cleanup(removed_settings)

        except Exception as e:
            logging.error("Error updating configuration file: %s", str(e))
            logging.error("Continuing with existing configuration...")

    def _notify_config_cleanup(self, removed_settings: List[str]):
        """Notify user about configuration cleanup"""
        # Log at INFO level instead of WARNING - this is normal operation
        logging.info(
            "Configuration cleanup: removed %d deprecated settings: %s",
            len(removed_settings),
            ", ".join(removed_settings),
        )
        # Don't duplicate backup message - it's already shown in the main upgrade message

    def _write_clean_config(self, valid_settings: Dict[str, str]):
        """Write configuration file in proper order with nice formatting"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write('<settings version="5">\n')

            # Group settings with comments for better readability
            sections = [
                ("Basic guide settings", ["zipcode", "lineupid", "days"]),
                ("Station filtering", ["slist", "stitle"]),
                ("Extended details and language detection", ["xdetails", "xdesc", "langdetect"]),
                ("Display options", ["epgenre", "epicon"]),
                (
                    "TVheadend integration",
                    ["tvhoff", "tvhurl", "tvhport", "tvhmatch", "chmatch", "usern", "passw"],
                ),
                (
                    "Cache and retention policies",
                    ["redays", "refresh", "logrotate", "relogs", "rexmltv"],
                ),
            ]

            written_settings = set()

            for section_name, section_settings in sections:
                # Check if this section has any settings to write
                has_settings = any(setting_id in valid_settings for setting_id in section_settings)

                if has_settings:
                    f.write(f"\n  <!-- {section_name} -->\n")

                    for setting_id in section_settings:
                        if setting_id in valid_settings:
                            value = valid_settings[setting_id]
                            if value is not None and str(value).strip():
                                f.write(f'  <setting id="{setting_id}">{value}</setting>\n')
                            else:
                                f.write(f'  <setting id="{setting_id}"></setting>\n')
                            written_settings.add(setting_id)

            # Write any remaining settings not in predefined sections (alphabetically)
            remaining_settings = sorted(
                [setting_id for setting_id in valid_settings if setting_id not in written_settings]
            )

            if remaining_settings:
                f.write("\n  <!-- Other settings -->\n")
                for setting_id in remaining_settings:
                    value = valid_settings[setting_id]
                    if value is not None and str(value).strip():
                        f.write(f'  <setting id="{setting_id}">{value}</setting>\n')
                    else:
                        f.write(f'  <setting id="{setting_id}"></setting>\n')

            f.write("</settings>\n")

    def _validate_cache_and_retention_policies(self):
        """Validate unified cache and retention policy configuration settings"""
        # Validate logrotate
        logrotate = self.settings.get("logrotate", "true").lower().strip()
        valid_rotations = ["true", "false", "daily", "weekly", "monthly"]

        if logrotate not in valid_rotations:
            logging.warning('Invalid logrotate value "%s", using default "true"', logrotate)
            self.settings["logrotate"] = "true"
        else:
            self.settings["logrotate"] = logrotate

        # Validate relogs (log retention)
        relogs = self.settings.get("relogs", "30").strip()
        if not self._validate_retention_value(relogs):
            logging.warning('Invalid relogs value "%s", using default "30"', relogs)
            self.settings["relogs"] = "30"

        # Validate rexmltv (XMLTV backup retention)
        rexmltv = self.settings.get("rexmltv", "7").strip()
        if not self._validate_retention_value(rexmltv):
            logging.warning('Invalid rexmltv value "%s", using default "7"', rexmltv)
            self.settings["rexmltv"] = "7"

        # Validate redays >= days
        try:
            days = int(self.settings.get("days", "1"))
            redays = int(self.settings.get("redays", str(days)))

            if redays < days:
                logging.warning(
                    "redays (%d) must be >= days (%d), adjusting redays to %d", redays, days, days
                )
                self.settings["redays"] = str(days)
            # Remove the excessive warning - just log at debug level
            elif redays > days * 3:  # Reasonable upper limit
                logging.debug(
                    "redays (%d) is much higher than days (%d) - see documentation for optimization tips",
                    redays,
                    days,
                )

        except (ValueError, TypeError):
            # Set redays to match days if invalid
            days = int(self.settings.get("days", "1"))
            self.settings["redays"] = str(days)
            logging.warning("Invalid redays value, setting to match days (%d)", days)

    def _validate_retention_value(self, value: str) -> bool:
        """Validate retention value: must be number (days) or weekly/monthly/quarterly/unlimited"""
        if not value:
            return False

        # Check if it's a number (days)
        try:
            days = int(value)
            return 0 <= days <= 3650  # 0 to 10 years seems reasonable
        except ValueError:
            pass

        # Check if it's a valid period
        valid_periods = ["weekly", "monthly", "quarterly", "unlimited"]
        return value.lower() in valid_periods

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
        country_name = "United States" if country == "USA" else "Canada"

        # Generate lineup IDs using new simplified method
        auto_lineup_config = self._get_auto_lineup_config(clean_postal, country)

        # Display results using unified function
        self._display_lineup_output(
            postal_code, clean_postal, country_name, country, auto_lineup_config, debug_mode
        )

        return True

    def _display_lineup_output(
        self,
        postal_code: str,
        clean_postal: str,
        country_name: str,
        country: str,
        lineup_config: Dict,
        debug_mode: bool = False
    ):
        """
        Display lineup detection output - unified function for both simple and debug modes

        Args:
            postal_code: Original postal code input
            clean_postal: Normalized postal code
            country_name: Full country name
            country: Country code (USA/CAN)
            lineup_config: Auto-generated lineup configuration
            debug_mode: Whether to show debug information
        """
        # Calculate current time rounded to nearest 3-hour block
        import time
        from datetime import datetime

        now = datetime.now().replace(microsecond=0, second=0, minute=0)
        # Round to nearest 3-hour block (0, 3, 6, 9, 12, 15, 18, 21)
        standard_hour = (now.hour // 3) * 3
        standard_dt = now.replace(hour=standard_hour)
        example_time = str(int(time.mktime(standard_dt.timetuple())))

        # Header (different for debug mode)
        if debug_mode:
            print("=" * 70)
            print("GRACENOTE2EPG - LINEUP DETECTION (DEBUG MODE)")
            print("=" * 70)
            print(f"📍 LOCATION INFORMATION:")
            print(f"   Normalized code:   {clean_postal}")
            print(f"   Detected country:  {country_name} ({country})")
            print()

        # API parameters
        print(f"🌍 GRACENOTE API URL PARAMETERS:")
        print(f"   lineupId={lineup_config['api_lineup_id']}")
        print(f"   country={country}")
        print(f"   postalCode={clean_postal}")
        print()

        # Validation URLs
        print(f"✅ VALIDATION URLs (manual verification):")
        print(f"   Auto-generated: {lineup_config['tvtv_url']}")

        if debug_mode:
            print(
                f"   Note: OTA format is {lineup_config['tvtv_lineup_id']} "
                f"(country + OTA + postal, no -DEFAULT suffix)"
            )
            print(f"   Cable/Satellite providers use different format: {country}-[ProviderID]-X")

        print(f"   Manual lookup:")
        if country == "CAN":
            print(f"     1. Go to https://www.tvtv.ca/")
            print(f"     2. Enter postal code: {clean_postal}")
            print(
                f"     3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → "
                f"URL shows lu{lineup_config['tvtv_lineup_id']}"
            )
            print(f"     3b. For Cable/Sat: Select provider → URL shows lu{country}-[ProviderID]-X")
        else:
            print(f"     1. Go to https://www.tvtv.us/")
            print(f"     2. Enter ZIP code: {clean_postal}")
            print(
                f"     3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → "
                f"URL shows lu{lineup_config['tvtv_lineup_id']}"
            )
            print(f"     3b. For Cable/Sat: Select provider → URL shows lu{country}-[ProviderID]-X")
        print()

        # API test URL
        print(f"🔗 GRACENOTE API URL FOR TESTING:")

        if debug_mode:
            # Show the human-readable time for debugging
            print(f"   Using current block: {standard_dt.strftime('%Y-%m-%d %H:00')} "
                  f"(timestamp: {example_time})")

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

        # Debug-only sections
        if debug_mode:
            print(f"📊 GRACENOTE API - OTHER COMMON PARAMETERS:")
            print(
                f"   • &device=[-|X]                    "
                f"Device type: - for Over-the-Air, X for cable/satellite"
            )
            print(
                f"   • &pref=16%2C128                   "
                f"Preference codes (16,128): channel lineup preferences"
            )
            print(
                f"   • &timezone=America%2FNew_York     "
                f"User timezone for schedule times (URL-encoded)"
            )
            print(f"   • &languagecode=en-us              Content language: en-us, fr-ca, es-us, etc.")
            print(
                f"   • &TMSID=                          "
                f"Tribune Media Services ID (legacy, usually empty)"
            )
            print(
                f"   • &AffiliateID=lat                 "
                f"Partner/affiliate identifier (lat=local affiliate)"
            )
            print()

            print(f"💾 MANUAL DOWNLOAD:")
            print(f"⚠️  NOTE: Using browser-like headers to bypass AWS WAF")
            print()
            print(
                f'curl -s -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                f'AppleWebKit/537.36" \\'
            )
            print(f'     -H "Accept: application/json, text/html, application/xhtml+xml, */*" \\')
            print(f'     "{test_url}" > out.json')
            print()

            print(f"🔧 RECOMMENDED CONFIGURATION:")
            country_full = "Canada" if country == "CAN" else "United States"
            print(f"   <!-- Simplified configuration (auto-detection) -->")
            print(f'   <setting id="zipcode">{clean_postal}</setting>')
            print(f'   <setting id="lineupid">auto</setting>')
            print()
            print(f"   <!-- Alternative: Copy tvtv.com lineup ID directly -->")
            print(f"   <!-- <setting id=\"lineupid\">{lineup_config['tvtv_lineup_id']}</setting> -->")
            print()
            print(f"   <!-- For Cable/Satellite providers: -->")
            print(f'   <!-- <setting id="lineupid">{country}-[ProviderID]-X</setting> -->')
            print(
                f'   <!-- Example: <setting id="lineupid">{country}-0005993-X</setting> '
                f'for Videotron -->'
            )
            print()

            print("=" * 70)
            print("💡 NEXT STEPS:")
            print("1. Verify the validation URLs show your local channels")
            print("2. Update your gracenote2epg.xml with the recommended configuration")
            print("3. Run: tv_grab_gracenote2epg --days 1 --console")
            print("4. Look for 'Auto-detected lineupID' in the logs")
            print("5. Confirm no HTTP 400 errors in download attempts")
            print("=" * 70)
            print()

        # Documentation link (always shown)
        print("📖 DOCUMENTATION:")
        print("   https://github.com/th0ma7/gracenote2epg/blob/main/docs/lineup-configuration.md")

    def validate_postal_code_format(self, postal_code: str) -> Tuple[bool, str, str]:
        """
        Validate postal code format and return country info

        Args:
            postal_code: Raw postal code input

        Returns:
            tuple: (is_valid, country_code, clean_postal)
        """
        clean_postal = postal_code.replace(" ", "").upper()

        if clean_postal.isdigit() and len(clean_postal) == 5:
            return True, "USA", clean_postal
        elif re.match(r"^[A-Z][0-9][A-Z][0-9][A-Z][0-9]$", clean_postal):
            return True, "CAN", clean_postal
        else:
            return False, "", clean_postal

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
        country_name = "United States" if country == "USA" else "Canada"

        if "OTA" in normalized_lineup_id:
            return f"Local Over the Air Broadcast ({country_name})"
        elif normalized_lineup_id.endswith("-X"):
            return f"Cable/Satellite Provider ({country_name})"
        else:
            return f"TV Lineup ({country_name})"

    def get_lineup_config(self) -> Dict[str, str]:
        """Get lineup configuration with automatic normalization and detection"""
        lineupid = self.settings.get("lineupid", "auto")
        postal_code = self.settings.get("zipcode", "")
        country = self.get_country()

        # Normalize lineup ID
        normalized_lineup_id = self.normalize_lineup_id(lineupid, country, postal_code)

        # Auto-detect device type
        device_type = self.detect_device_type(normalized_lineup_id)

        # Auto-generate description
        description = self.generate_description(normalized_lineup_id, country)

        # Determine if this was auto-detected
        auto_detected = not lineupid or lineupid.lower() == "auto"

        return {
            "lineup_id": normalized_lineup_id,  # Full API format
            "headend_id": "lineupId",  # Always literal 'lineupId' for API
            "device_type": device_type,  # Auto-detected device type
            "description": description,  # Auto-generated description
            "auto_detected": auto_detected,
            "original_config": lineupid,  # Original config value
            "country": country,
            "postal_code": postal_code,
        }

    def _get_auto_lineup_config(self, postal_code: str, country: str) -> Dict[str, str]:
        """Get auto-generated lineup configuration for display purposes"""
        # Generate OTA lineup IDs
        base_lineup = f"OTA{postal_code}"
        tvtv_lineup_id = f"{country}-{base_lineup}"
        api_lineup_id = f"{country}-{base_lineup}-DEFAULT"

        # Generate tvtv.com URL
        if country == "CAN":
            postal_for_url = postal_code.lower()
            tvtv_url = f"https://www.tvtv.ca/qc/saint-jean-sur-richelieu/{postal_for_url}/lu{tvtv_lineup_id}"
        else:
            tvtv_url = f"https://www.tvtv.us/ca/beverly-hills/{postal_code}/lu{tvtv_lineup_id}"

        return {
            "tvtv_lineup_id": tvtv_lineup_id,  # Format for tvtv.com
            "api_lineup_id": api_lineup_id,  # Format for API
            "tvtv_url": tvtv_url,  # Complete tvtv.com URL
            "device_type": "-",  # OTA device type
            "country": country,
            "postal_code": postal_code,
        }

    def get_retention_config(self) -> Dict[str, Any]:
        """Get unified cache and retention configuration"""
        # Parse logrotate setting
        logrotate = self.settings.get("logrotate", "true").lower()

        # Convert to rotation configuration
        if logrotate == "false":
            rotation_enabled = False
            rotation_interval = "daily"  # Default when disabled
        elif logrotate == "true":
            rotation_enabled = True
            rotation_interval = "daily"  # Default when true
        elif logrotate in ["daily", "weekly", "monthly"]:
            rotation_enabled = True
            rotation_interval = logrotate
        else:
            rotation_enabled = True
            rotation_interval = "daily"  # Fallback

        # Parse retention values and convert to days
        log_retention_days = self._parse_retention_to_days(
            self.settings.get("relogs", "30"), rotation_interval
        )

        xmltv_retention_days = self._parse_retention_to_days(
            self.settings.get("rexmltv", "7"), "daily"  # XMLTV backups are always daily
        )

        return {
            # Log rotation configuration
            "enabled": rotation_enabled,
            "interval": rotation_interval,
            "keep_files": self._days_to_keep_files(log_retention_days, rotation_interval),
            # Extended retention information
            "log_retention_days": log_retention_days,
            "xmltv_retention_days": xmltv_retention_days,
            # Original settings for logging
            "logrotate_setting": self.settings.get("logrotate", "true"),
            "relogs_setting": self.settings.get("relogs", "30"),
            "rexmltv_setting": self.settings.get("rexmltv", "7"),
        }

    def _parse_retention_to_days(self, retention_value: str, interval: str) -> int:
        """Convert retention setting to number of days"""
        retention_value = retention_value.strip().lower()

        # Handle numeric values (days)
        try:
            return int(retention_value)
        except ValueError:
            pass

        # Handle period-based retention
        if retention_value == "weekly":
            return 7
        elif retention_value == "monthly":
            return 30
        elif retention_value == "quarterly":
            return 90
        elif retention_value == "unlimited":
            return 0  # 0 means unlimited
        else:
            # Default based on interval
            if interval == "daily":
                return 30
            elif interval == "weekly":
                return 90  # ~3 months
            elif interval == "monthly":
                return 365  # 1 year
            else:
                return 30

    def _days_to_keep_files(self, retention_days: int, interval: str) -> int:
        """Convert retention days to number of backup files to keep"""
        if retention_days == 0:
            return 0  # Unlimited

        if interval == "daily":
            return retention_days
        elif interval == "weekly":
            return max(1, retention_days // 7)
        elif interval == "monthly":
            return max(1, retention_days // 30)
        else:
            return retention_days

    def get_country(self) -> str:
        """Determine country from zipcode format"""
        zipcode = self.settings.get("zipcode", "")
        if zipcode.isdigit():
            return "USA"
        else:
            return "CAN"

    def needs_extended_download(self) -> bool:
        """Determine if extended details download is needed"""
        return self.settings.get("xdetails", False) or self.settings.get("xdesc", False)

    def get_station_list(self) -> Optional[List[str]]:
        """Get explicit station list if configured"""
        slist = self.settings.get("slist", "")
        if slist and slist.strip():
            return [s.strip() for s in slist.split(",") if s.strip()]
        return None

    def get_refresh_hours(self) -> int:
        """Get cache refresh hours from configuration"""
        try:
            return int(self.settings.get("refresh", "48"))
        except (ValueError, TypeError):
            logging.warning("Invalid refresh setting, using default 48 hours")
            return 48

    def log_config_summary(self):
        """Log configuration summary with improved clarity"""
        logging.info("Configuration values processed:")

        # Enhanced zipcode logging with cleaner format
        zipcode = self.settings.get("zipcode")
        if "zipcode" in getattr(self, "config_changes", {}):
            change_info = self.config_changes["zipcode"]
            logging.info("  zipcode: %s", change_info)
        else:
            logging.info("  zipcode: %s", zipcode)

        # Enhanced lineup configuration logging with cleaner format
        lineup_config = self.get_lineup_config()
        original_lineupid = lineup_config["original_config"]
        final_lineup_id = lineup_config["lineup_id"]

        if "lineupid" in getattr(self, "config_changes", {}):
            change_info = self.config_changes["lineupid"]
            logging.info("  lineupid: %s", change_info)
        elif lineup_config["auto_detected"]:
            logging.info("  lineupid: %s → %s (auto-detection)", original_lineupid, final_lineup_id)
        else:
            # Standard case - just show the transformation
            logging.info("  lineupid: %s → %s", original_lineupid, final_lineup_id)

        # Country information (moved up and with auto-detected note)
        country = self.get_country()
        country_name = "Canada" if country == "CAN" else "United States of America"
        logging.info("  country: %s [%s] (auto-detected from zipcode)", country_name, country)

        # Move device type to debug level only with explanation
        logging.debug(
            "  device: %s (auto-detected for optional &device= URL parameter)",
            lineup_config["device_type"],
        )

        logging.info("  description: %s", lineup_config["description"])

        logging.info("  xdetails (download extended data): %s", self.settings.get("xdetails"))
        logging.info("  xdesc (use extended descriptions): %s", self.settings.get("xdesc"))
        logging.info(
            "  langdetect (automatic language detection): %s", self.settings.get("langdetect")
        )

        # Log cache and retention configuration
        refresh_hours = self.get_refresh_hours()
        redays = int(self.settings.get("redays", "1"))

        logging.info("Cache and retention policies:")
        if refresh_hours == 0:
            logging.info("  refresh: disabled (use all cached data)")
        else:
            logging.info(
                "  refresh: %d hours (refresh first %d hours of guide)",
                refresh_hours,
                refresh_hours,
            )

        logging.info("  redays: %d days (cache retention period)", redays)

        # Log unified retention configuration
        retention_config = self.get_retention_config()
        if retention_config["enabled"]:
            logging.info(
                "  logrotate: enabled (%s, %d days retention)",
                retention_config["interval"],
                retention_config["log_retention_days"],
            )
        else:
            logging.info("  logrotate: disabled")

        logging.info(
            "  rexmltv: %d days (XMLTV backup retention)", retention_config["xmltv_retention_days"]
        )

        # Log configuration logic
        xdetails = self.settings.get("xdetails", False)
        xdesc = self.settings.get("xdesc", False)
        langdetect = self.settings.get("langdetect", False)

        if xdesc and not xdetails:
            logging.info("xdesc=true detected - automatically enabling extended details download")
        elif xdetails and not xdesc:
            logging.info("xdetails=true - downloading extended data but using basic descriptions")
        elif xdetails and xdesc:
            logging.info("Both xdetails and xdesc enabled - full extended functionality")
        else:
            logging.info("Extended features disabled - using basic guide data only")

        if langdetect:
            logging.info("Language detection enabled - will auto-detect French/English/Spanish")
        else:
            logging.info("Language detection disabled - all content will be marked as English")
