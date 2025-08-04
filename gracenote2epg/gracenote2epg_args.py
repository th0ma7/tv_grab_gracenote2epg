"""
gracenote2epg.gracenote2epg_args - Command line argument parsing

Handles all command-line arguments and validation for the gracenote2epg grabber.
Provides baseline XMLTV grabber capabilities.
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Optional, Any


class ArgumentParser:
    """Command line argument parser for gracenote2epg"""

    # Validation patterns
    DAYS_PATTERN = re.compile(r'^[1-9]$|^1[0-4]$')  # 1-14 days
    REFRESH_PATTERN = re.compile(r'^[0-9]+$|^[1-9][0-9]+$')  # 0-999 hours
    CA_CODE_PATTERN = re.compile(r'^[A-Z][0-9][A-Z][ ]?[0-9][A-Z][0-9]$')  # Canadian postal
    US_CODE_PATTERN = re.compile(r'^[0-9]{5}$')  # US ZIP code

    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self):
        """Create the argument parser with all options"""
        parser = argparse.ArgumentParser(
            prog='gracenote2epg',
            description='North America TV guide grabber (gracenote.com)',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  gracenote2epg --capabilities
  gracenote2epg --days 7 --zip 92101
  gracenote2epg --days 3 --postal J3B1M4 --warning --console --output guide.xml
  gracenote2epg --days 7 --zip 92101 --langdetect false
  gracenote2epg --days 7 --zip 92101 --norefresh
  gracenote2epg --days 7 --zip 92101 --refresh 24

Configuration:
  Default config: ~/gracenote2epg/conf/gracenote2epg.xml
  Default cache:  ~/gracenote2epg/cache/
  Default logs:   ~/gracenote2epg/log/

Logging Levels:
  (default)       Info, warnings and errors to file only, XML to console
  --warning       Only warnings and errors to file, XML to console
  --debug         All debug information to file only, XML to console
  --console       Display active log level to console (can combine with --warning/--debug)
  --quiet         No console output except XML, logs to file only

Cache Refresh Options:
  --norefresh     Don't refresh cached blocks (use all cached data)
  --refresh XX    Refresh blocks from the first XX hours (default: 48)

Language Detection:
  --langdetect    Enable/disable automatic language detection (requires langdetect library)
                  Default: auto-enabled if langdetect is installed, disabled otherwise
            """
        )

        # XMLTV baseline capabilities
        parser.add_argument(
            '--description', '-d',
            action='store_true',
            help='Show grabber description and exit'
        )

        parser.add_argument(
            '--version', '-v',
            action='store_true',
            help='Show version and exit'
        )

        parser.add_argument(
            '--capabilities', '-c',
            action='store_true',
            help='Show capabilities and exit'
        )

        # Log level selection (can be combined with --console)
        level_group = parser.add_mutually_exclusive_group()
        level_group.add_argument(
            '--warning', '-w',
            action='store_true',
            help='Only warnings and errors to file'
        )

        level_group.add_argument(
            '--debug',
            action='store_true',
            help='All debug information to file (very verbose)'
        )

        # Console output control (mutually exclusive)
        console_group = parser.add_mutually_exclusive_group()
        console_group.add_argument(
            '--console',
            action='store_true',
            help='Display active log level to console (can combine with --warning/--debug)'
        )

        console_group.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='No console output except XML, logs to file only'
        )

        # Output control
        parser.add_argument(
            '--output', '-o',
            type=Path,
            help='Redirect XMLTV output to specified file'
        )

        # Guide parameters
        parser.add_argument(
            '--days',
            type=int,
            help='Number of days to download (1-14)'
        )

        parser.add_argument(
            '--offset',
            type=int,
            help='Start with data for day today plus X days'
        )

        # Cache refresh control
        refresh_group = parser.add_mutually_exclusive_group()
        refresh_group.add_argument(
            '--norefresh',
            action='store_true',
            help='Don\'t refresh cached blocks (use all cached data, fastest)'
        )

        refresh_group.add_argument(
            '--refresh',
            type=int,
            metavar='HOURS',
            help='Refresh blocks from the first HOURS hours (default: 48, range: 0-168)'
        )

        # Language detection
        parser.add_argument(
            '--langdetect',
            type=str,
            choices=['true', 'false'],
            help='Enable/disable automatic language detection (requires langdetect library)'
        )

        # Location codes
        location_group = parser.add_mutually_exclusive_group()
        location_group.add_argument(
            '--zip',
            type=str,
            help='US ZIP code (5 digits)'
        )

        location_group.add_argument(
            '--postal',
            type=str,
            help='Canadian postal code (A1A 1A1)'
        )

        location_group.add_argument(
            '--code',
            type=str,
            help='US ZIP or Canadian postal code'
        )

        # Configuration
        parser.add_argument(
            '--config-file',
            type=Path,
            help='Configuration file path'
        )

        parser.add_argument(
            '--basedir',
            type=Path,
            help='Base directory for config, cache, and logs'
        )

        return parser

    def parse_args(self, args=None):
        """Parse command line arguments with validation"""
        args = self.parser.parse_args(args)

        # Handle special actions that exit immediately
        if args.description:
            print("North America (tvlistings.gracenote.com using gracenote2epg)")
            sys.exit(0)

        if args.version:
            from . import __version__
            print(__version__)
            sys.exit(0)

        if args.capabilities:
            print("baseline")
            sys.exit(0)

        # Validate arguments
        self._validate_args(args)

        # Normalize location codes
        self._normalize_location(args)

        # Normalize langdetect option
        self._normalize_langdetect(args)

        # Normalize refresh options
        self._normalize_refresh(args)

        return args

    def _validate_args(self, args):
        """Validate argument values"""
        # Validate days parameter
        if args.days is not None:
            if not self.DAYS_PATTERN.match(str(args.days)):
                self.parser.error(f"Parameter [--days] must be 1-14, got: {args.days}")

        # Validate offset parameter
        if args.offset is not None:
            if not self.DAYS_PATTERN.match(str(args.offset)):
                self.parser.error(f"Parameter [--offset] must be 1-14, got: {args.offset}")

        # Validate refresh parameter
        if args.refresh is not None:
            if args.refresh < 0 or args.refresh > 168:  # 0 to 7 days
                self.parser.error(f"Parameter [--refresh] must be 0-168 hours, got: {args.refresh}")

        # Validate location codes
        location_code = args.zip or args.postal or args.code
        if location_code:
            # Remove spaces for validation
            clean_code = location_code.replace(' ', '')

            if not (self.CA_CODE_PATTERN.match(location_code) or
                   self.US_CODE_PATTERN.match(clean_code)):
                self.parser.error(
                    f"Invalid location code: {location_code}. "
                    "Expected US ZIP (12345) or Canadian postal (A1A 1A1)"
                )

    def _normalize_location(self, args):
        """Normalize location code into a single field"""
        # Consolidate location codes into single field
        location_code = args.zip or args.postal or args.code
        if location_code:
            # Remove spaces from postal codes
            args.location_code = location_code.replace(' ', '')
        else:
            args.location_code = None

        # Clean up individual fields
        del args.zip, args.postal, args.code

    def _normalize_langdetect(self, args):
        """Normalize langdetect option"""
        if args.langdetect:
            args.langdetect = args.langdetect.lower() == 'true'
        else:
            args.langdetect = None  # Use config default

    def _normalize_refresh(self, args):
        """Normalize refresh options"""
        if args.norefresh:
            args.refresh_hours = 0  # No refresh
        elif args.refresh is not None:
            args.refresh_hours = args.refresh
        else:
            args.refresh_hours = None  # Use config default

        # Clean up individual fields
        del args.norefresh
        if hasattr(args, 'refresh'):
            del args.refresh

    def get_logging_config(self, args):
        """Determine logging configuration from arguments"""
        config = {
            'level': 'default',  # default, warning, debug
            'console': False,    # whether to show logs on console
            'quiet': False       # whether to suppress all console output except XML
        }

        if args.debug:
            config['level'] = 'debug'
        elif args.warning:
            config['level'] = 'warning'

        if args.console:
            config['console'] = True
        elif args.quiet:
            config['quiet'] = True

        return config

    def get_system_defaults(self):
        """Get system-specific default directories with proper DSM6/DSM7 path selection"""
        import platform
        import os
        from pathlib import Path

        home = Path.home()

        # Detect system type
        system_type = self._detect_system_type()

        if system_type == "raspberry":
            # Raspberry Pi - Kodi path if available
            kodi_path = home / "script.module.zap2epg" / "epggrab"
            if kodi_path.exists():
                base_dir = kodi_path
            else:
                base_dir = home / "gracenote2epg"

        elif system_type == "synology":
            # Synology NAS with proper DSM6/DSM7 path selection
            dsm_version = self._get_dsm_version()

            if dsm_version < 40000:
                # DSM6 and earlier: /var/packages/tvheadend/target/var/epggrab/gracenote2epg
                base_dir = Path("/var/packages/tvheadend/target/var/epggrab/gracenote2epg")
            else:
                # DSM7 and later: /var/packages/tvheadend/var/epggrab/gracenote2epg
                base_dir = Path("/var/packages/tvheadend/var/epggrab/gracenote2epg")

            # Add debug logging
            import logging
            logging.debug(f"Synology detected - DSM version: {dsm_version}")
            logging.debug(f"Selected path: {base_dir}")

            # Verify the parent directory exists, fallback if not
            if not base_dir.parent.exists():
                logging.warning(f"Expected Synology TVheadend path {base_dir.parent} doesn't exist")
                logging.warning("Available TVheadend paths:")
                for check_path in ["/var/packages/tvheadend/var", "/var/packages/tvheadend/target/var"]:
                    if Path(check_path).exists():
                        logging.warning(f"  Found: {check_path}")
                        # Use the available path
                        base_dir = Path(check_path) / "epggrab" / "gracenote2epg"
                        break
                else:
                    logging.warning("No TVheadend paths found, falling back to home directory")
                    base_dir = home / "gracenote2epg"

        else:
            # Standard Linux/Docker
            base_dir = home / "gracenote2epg"

        return {
            'base_dir': base_dir,
            'cache_dir': base_dir / "cache",
            'conf_dir': base_dir / "conf",
            'log_dir': base_dir / "log",
            'config_file': base_dir / "conf" / "gracenote2epg.xml",
            'xmltv_file': base_dir / "cache" / "xmltv.xml",
            'log_file': base_dir / "log" / "gracenote2epg.log"
        }

    def create_directories_with_proper_permissions(self):
        """Create required directories with proper 755 permissions"""
        defaults = self.get_system_defaults()

        # Create directories with 755 permissions (rwxr-xr-x)
        for directory in [defaults['cache_dir'], defaults['conf_dir'], defaults['log_dir']]:
            try:
                directory.mkdir(parents=True, exist_ok=True, mode=0o755)
            except Exception as e:
                # Fallback: create without mode specification (depends on umask)
                directory.mkdir(parents=True, exist_ok=True)

    def _detect_system_type(self):
        """Detect system type for default directories - FIXED for Synology"""
        import platform
        import os

        # Check if Raspberry Pi
        device_tree_model = Path("/proc/device-tree/model")
        if device_tree_model.exists():
            try:
                with open(device_tree_model) as f:
                    if "raspberry" in f.read().lower():
                        return "raspberry"
            except:
                pass

        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.exists():
            try:
                with open(cpuinfo) as f:
                    if "raspberry" in f.read().lower():
                        return "raspberry"
            except:
                pass

        # FIXED: Enhanced Synology detection

        # Method 1: Check for Synology-specific files (most reliable)
        if Path("/etc/synoinfo.conf").exists():
            return "synology"

        # Method 2: Check VERSION file for Synology content
        try:
            version_file = Path("/etc/VERSION")
            if version_file.exists():
                with open(version_file, 'r') as f:
                    content = f.read().lower()
                    if "synology" in content or ('majorversion=' in content and 'buildnumber=' in content):
                        return "synology"
        except:
            pass

        # Method 3: Check for TVheadend Synology directory structure (DSM6 or DSM7)
        if Path("/var/packages/tvheadend/var").exists() or Path("/var/packages/tvheadend/target/var").exists():
            return "synology"

        # Method 4: Original platform check (fallback)
        try:
            if "synology" in platform.uname().release.lower():
                return "synology"
        except:
            pass

        return "linux"

    def _get_dsm_version(self):
        """Get Synology DSM version number - FIXED with proper DSM6/DSM7 detection"""
        import re

        # Method 1: Parse /etc/VERSION file (most accurate)
        try:
            version_file = Path("/etc/VERSION")
            if version_file.exists():
                with open(version_file, 'r') as f:
                    content = f.read()

                # Extract major version and build number
                major_match = re.search(r'majorversion="?(\d+)"?', content)
                build_match = re.search(r'buildnumber="?(\d+)"?', content)

                if major_match:
                    major_version = int(major_match.group(1))

                    if build_match:
                        build_number = int(build_match.group(1))
                        # Return actual build number for precise version detection
                        return build_number

                    # Fallback to major version mapping if no build number
                    if major_version >= 7:
                        return 50000  # DSM7+ uses /var/packages/tvheadend/var/
                    elif major_version >= 6:
                        return 30000  # DSM6 uses /var/packages/tvheadend/target/var/
                    else:
                        return 20000  # DSM5 and older (if any)

        except Exception as e:
            pass

        # Method 2: Check directory structure as fallback to determine DSM version
        try:
            # DSM7+ path exists
            if Path("/var/packages/tvheadend/var").exists() and not Path("/var/packages/tvheadend/target/var").exists():
                return 50000  # DSM7+
            # DSM6 path exists
            elif Path("/var/packages/tvheadend/target/var").exists():
                return 30000  # DSM6
            # Both exist (transition case) - prefer newer structure
            elif Path("/var/packages/tvheadend/var").exists():
                return 50000  # DSM7+
        except:
            pass

        # Default to DSM7+ if detection fails
        return 50000
