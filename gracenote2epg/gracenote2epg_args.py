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
  gracenote2epg --days 7 --zip 92101 --debug
  gracenote2epg --days 3 --postal J3B1M4 --quiet --output guide.xml

Configuration:
  Default config: ~/gracenote2epg/conf/gracenote2epg.xml
  Default cache:  ~/gracenote2epg/cache/
  Default logs:   ~/gracenote2epg/log/
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

        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Suppress progress information (errors only)'
        )

        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging with detailed statistics'
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

    def get_system_defaults(self):
        """Get system-specific default directories"""
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
            # Synology NAS
            if self._get_dsm_version() < 40000:
                # DSM6
                base_dir = Path("/var/packages/tvheadend/target/var/epggrab/gracenote2epg")
            else:
                # DSM7
                base_dir = Path("/var/packages/tvheadend/var/epggrab/gracenote2epg")

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

    def _detect_system_type(self):
        """Detect system type for default directories"""
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

        # Check if Synology
        if "synology" in platform.uname().release.lower():
            return "synology"

        return "linux"

    def _get_dsm_version(self):
        """Get Synology DSM version number"""
        import platform
        try:
            # Extract version from uname
            uname_release = platform.uname().release
            # Format: "DSM-7.1.1-42962" or similar
            version_match = re.search(r'#(\d+)', uname_release)
            if version_match:
                return int(version_match.group(1))
        except:
            pass
        return 50000  # Default to DSM7+ behavior
