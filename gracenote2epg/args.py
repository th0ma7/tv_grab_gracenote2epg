"""
gracenote2epg.args - Command line argument parsing for unified architecture

Enhanced argument parsing with worker strategy support and clean performance options.
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import Optional


class ArgumentParser:
    """Command line argument parser with unified architecture support"""

    # Validation patterns
    DAYS_PATTERN = re.compile(r"^[1-9]$|^1[0-4]$")  # 1-14 days
    REFRESH_PATTERN = re.compile(r"^[0-9]+$|^[1-9][0-9]+$")  # 0-999 hours
    CA_CODE_PATTERN = re.compile(r"^[A-Z][0-9][A-Z][ ]?[0-9][A-Z][0-9]$")  # Canadian postal
    US_CODE_PATTERN = re.compile(r"^[0-9]{5}$")  # US ZIP code

    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self):
        """Create the argument parser with unified architecture options"""
        parser = argparse.ArgumentParser(
            prog="gracenote2epg",
            description="North America TV guide grabber with unified strategy-based parallel downloads",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  gracenote2epg --capabilities
  gracenote2epg --days 7 --zip 92101
  gracenote2epg --hours 12 --postal J3B1M4 --warning --console --output guide.xml
  gracenote2epg --show-lineup --postal J3B1M4                  # Test lineup detection
  gracenote2epg --show-lineup --zip 90210                      # Test US ZIP code
  gracenote2epg --show-lineup --code "J3B 1M4"                 # Test with space
  gracenote2epg --show-lineup --zip 90210 --debug              # Detailed debug output
  gracenote2epg --days 7 --zip 92101 --langdetect false
  gracenote2epg --days 7 --zip 92101 --lineupid auto           # Auto-detection with required ZIP
  gracenote2epg --days 7 --lineupid CAN-OTAJ3B1M4              # Deduces postal J3B1M4
  gracenote2epg --days 7 --lineupid USA-OTA90210               # Deduces ZIP 90210
  gracenote2epg --days 7 --zip 92101 --lineupid CAN-OTAJ3B1M4  # Error: inconsistent
  gracenote2epg --days 7 --zip 92101 --norefresh
  gracenote2epg --days 7 --zip 92101 --refresh 24
  gracenote2epg --hours 18 --zip 92101 --cachedir /tmp/test-cache

Unified Performance Options:
  gracenote2epg --days 7 --zip 92101 --strategy balanced --workers 6
  gracenote2epg --days 7 --zip 92101 --strategy conservative   # Gentle on servers
  gracenote2epg --days 7 --zip 92101 --strategy aggressive     # Maximum performance
  gracenote2epg --days 7 --zip 92101 --no-parallel             # Force sequential
  gracenote2epg --days 7 --zip 92101 --workers 8               # Custom worker count
  gracenote2epg --days 7 --zip 92101 --no-adaptive             # Disable adaptive behavior
  gracenote2epg --days 7 --zip 92101 --rate-limit 10           # Limit to 10 requests/second

Monitoring Options:
  gracenote2epg --days 7 --zip 92101 --monitoring              # Enable real-time monitoring
  gracenote2epg --days 7 --zip 92101 --monitoring --web-api    # Include web API
  gracenote2epg --days 7 --zip 92101 --monitoring-port 8080    # Custom monitoring port

  Environment variables (override defaults):
    GRACENOTE_WORKER_STRATEGY=conservative/balanced/aggressive  Worker allocation strategy
    GRACENOTE_MAX_WORKERS=4                    Number of parallel workers (1-10)
    GRACENOTE_ENABLE_ADAPTIVE=true/false       Enable/disable adaptive behavior
    GRACENOTE_ENABLE_MONITORING=true/false     Enable/disable real-time monitoring
    GRACENOTE_MONITORING_WEB_API=true/false    Enable/disable monitoring web API
    GRACENOTE_MONITORING_PORT=9989             Monitoring web API port

Worker Strategies:
  conservative    Gentle on servers: guide 2-3 workers, series 1-2 workers, low rate limits
  balanced        Optimal for most users: guide 4-6 workers, series 2-3 workers, moderate rates
  aggressive      Maximum performance: guide 6-10 workers, series 3-4 workers, high rates

Testing and Validation:
  --show-lineup           Show auto-detected lineup parameters and validation URL
                          Must be combined with --zip, --postal, or --code
                          Useful for testing different postal/ZIP codes before configuration
                          Exits immediately after showing results (no download)
                          Use --debug for detailed technical information

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

LineupID Configuration:
  --lineupid      Override lineup configuration from command line
                  Examples: auto, CAN-OTAJ3B1M4, CAN-0005993-X
                  Supports all formats: auto-detection, tvtv.com format, complete provider format
                  Location extraction: OTA lineups automatically provide postal/ZIP codes
                  (e.g., CAN-OTAJ3B1M4 provides postal code J3B1M4)

Location Intelligence:
  When using OTA lineups, postal/ZIP codes are automatically extracted:
  - CAN-OTAJ3B1M4 → postal code J3B1M4 (Canada)
  - USA-OTA90210 → ZIP code 90210 (United States)
  If both --lineupid and --zip/--postal are provided, they must be consistent

Duration Options:
  --days          Download N complete days (1-14, traditional option)
  --hours         Download N hours (3,6,9,12,15,18,21,24, must be multiple of 3)
                  Note: --days and --hours are mutually exclusive

Cache Control:
  --cachedir      Use custom cache directory (overrides default cache location)
                  Useful for testing, benchmarking, or isolating cache data

Performance Notes:
  • Unified architecture with strategy-based worker allocation
  • Adaptive mode automatically adjusts workers based on server response
  • Different strategies for guide blocks vs series details
  • Real-time monitoring provides detailed performance insights
  • Clean API without legacy compatibility overhead
            """,
        )

        # XMLTV baseline capabilities
        parser.add_argument(
            "--description", "-d", action="store_true", help="Show grabber description and exit"
        )

        parser.add_argument("--version", "-v", action="store_true", help="Show version and exit")

        parser.add_argument(
            "--capabilities", "-c", action="store_true", help="Show capabilities and exit"
        )

        # LineupID detection and testing
        parser.add_argument(
            "--show-lineup",
            action="store_true",
            help="Show auto-detected lineupID for configured postal/ZIP code and exit (testing mode)",
        )

        # Log level selection
        level_group = parser.add_mutually_exclusive_group()
        level_group.add_argument(
            "--warning", "-w", action="store_true", help="Only warnings and errors to file"
        )

        level_group.add_argument(
            "--debug", action="store_true", help="All debug information to file (very verbose)"
        )

        # Console output control
        console_group = parser.add_mutually_exclusive_group()
        console_group.add_argument(
            "--console",
            action="store_true",
            help="Display active log level to console (can combine with --warning/--debug)",
        )

        console_group.add_argument(
            "--quiet",
            "-q",
            action="store_true",
            help="No console output except XML, logs to file only",
        )

        # Output control
        parser.add_argument(
            "--output", "-o", type=Path, help="Redirect XMLTV output to specified file"
        )

        # Guide parameters - mutually exclusive duration options
        duration_group = parser.add_mutually_exclusive_group()
        duration_group.add_argument("--days", type=int, help="Number of days to download (1-14)")
        duration_group.add_argument("--hours", type=int, help="Number of hours to download (3,6,9,12,15,18,21,24, must be multiple of 3)")

        parser.add_argument("--offset", type=int, help="Start with data for day today plus X days")

        # Cache refresh control
        refresh_group = parser.add_mutually_exclusive_group()
        refresh_group.add_argument(
            "--norefresh",
            action="store_true",
            help="Don't refresh cached blocks (use all cached data, fastest)",
        )

        refresh_group.add_argument(
            "--refresh",
            type=int,
            metavar="HOURS",
            help="Refresh blocks from the first HOURS hours (default: 48, range: 0-168)",
        )

        # Language detection
        parser.add_argument(
            "--langdetect",
            type=str,
            choices=["true", "false"],
            help="Enable/disable automatic language detection (requires langdetect library)",
        )

        # Lineup configuration
        parser.add_argument(
            "--lineupid",
            type=str,
            help="Override lineup configuration (auto, CAN-OTAJ3B1M4, CAN-0005993-X, etc.)",
        )

        # Location codes
        location_group = parser.add_mutually_exclusive_group()
        location_group.add_argument("--zip", type=str, help="US ZIP code (5 digits)")
        location_group.add_argument("--postal", type=str, help="Canadian postal code (A1A 1A1)")
        location_group.add_argument("--code", type=str, help="US ZIP or Canadian postal code")

        # Configuration
        parser.add_argument("--config-file", type=Path, help="Configuration file path")
        parser.add_argument(
            "--basedir", type=Path, help="Base directory for config, cache, and logs"
        )
        parser.add_argument(
            "--cachedir", type=Path, help="Cache directory path (overrides basedir/cache, useful for testing/benchmarking)"
        )

        # Unified performance options with strategy support
        performance_group = parser.add_argument_group('Unified Performance Options')

        # Worker strategy selection
        performance_group.add_argument(
            "--strategy",
            type=str,
            choices=['conservative', 'balanced', 'aggressive'],
            help="Worker allocation strategy (conservative=gentle, balanced=optimal, aggressive=maximum)"
        )

        # Parallel control
        parallel_control = performance_group.add_mutually_exclusive_group()
        parallel_control.add_argument(
            "--parallel",
            action="store_true",
            default=None,
            help="Enable parallel downloading (default: enabled with strategy-based allocation)"
        )

        parallel_control.add_argument(
            "--no-parallel",
            action="store_true",
            default=None,
            help="Disable parallel downloading, use sequential mode"
        )

        # Worker count
        performance_group.add_argument(
            "--workers",
            type=int,
            metavar="N",
            choices=range(1, 11),
            help="Maximum parallel download workers (1-10, strategy determines allocation)"
        )

        # Adaptive behavior control
        adaptive_control = performance_group.add_mutually_exclusive_group()
        adaptive_control.add_argument(
            "--adaptive",
            action="store_true",
            default=None,
            help="Enable adaptive worker adjustment based on server response (default: enabled)"
        )

        adaptive_control.add_argument(
            "--no-adaptive",
            action="store_true",
            default=None,
            help="Disable adaptive worker adjustment, use fixed allocation from strategy"
        )

        # Rate limiting
        performance_group.add_argument(
            "--rate-limit",
            type=float,
            metavar="RPS",
            help="Override strategy rate limit (0.5-20 requests/second)"
        )

        # Monitoring options
        monitoring_group = parser.add_argument_group('Monitoring Options')

        monitoring_group.add_argument(
            "--monitoring",
            action="store_true",
            help="Enable real-time monitoring with console display"
        )

        monitoring_group.add_argument(
            "--web-api",
            action="store_true",
            help="Enable monitoring web API (requires --monitoring)"
        )

        monitoring_group.add_argument(
            "--monitoring-port",
            type=int,
            metavar="PORT",
            default=9989,
            help="Monitoring web API port (default: 9989)"
        )

        return parser

    def parse_args(self, args=None):
        """Parse command line arguments with unified architecture validation"""
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

        # Handle --show-lineup with debug mode support
        if args.show_lineup:
            location_code = args.zip or args.postal or args.code
            if not location_code:
                self.parser.error("--show-lineup requires one of: --zip, --postal, or --code")

            from .config import ConfigManager
            temp_config = ConfigManager(Path("temp"))

            debug_mode = args.debug if hasattr(args, "debug") else False

            if not temp_config.display_lineup_detection_test(location_code, debug_mode):
                sys.exit(1)

            sys.exit(0)

        # Validate arguments
        self._validate_args(args)

        # Process lineup and location
        self._process_lineup_and_location(args)

        # Normalize options
        self._normalize_langdetect(args)
        self._normalize_refresh(args)
        self._process_duration_options(args)
        self._validate_cachedir(args)

        # Process unified performance options
        self._process_unified_performance_options(args)

        # Process monitoring options
        self._process_monitoring_options(args)

        return args

    def _validate_args(self, args):
        """Validate argument values"""
        # Validate days parameter
        if args.days is not None:
            if not self.DAYS_PATTERN.match(str(args.days)):
                self.parser.error(f"Parameter [--days] must be 1-14, got: {args.days}")

        # Validate hours parameter
        if args.hours is not None:
            if args.hours < 3 or args.hours > 24:
                self.parser.error(f"Parameter [--hours] must be 3-24, got: {args.hours}")
            if args.hours % 3 != 0:
                self.parser.error(f"Parameter [--hours] must be multiple of 3 (3,6,9,12,15,18,21,24), got: {args.hours}")

        # Validate offset parameter
        if args.offset is not None:
            if not self.DAYS_PATTERN.match(str(args.offset)):
                self.parser.error(f"Parameter [--offset] must be 1-14, got: {args.offset}")

        # Validate refresh parameter
        if args.refresh is not None:
            if args.refresh < 0 or args.refresh > 168:
                self.parser.error(f"Parameter [--refresh] must be 0-168 hours, got: {args.refresh}")

        # Validate lineupid parameter
        if args.lineupid is not None:
            lineupid = args.lineupid.strip()
            if not lineupid:
                self.parser.error("Parameter [--lineupid] cannot be empty")

    def _process_duration_options(self, args):
        """Process --days vs --hours options"""
        if args.hours is not None:
            # Convert hours to days for internal use
            args.duration_hours = args.hours
            args.duration_days = args.hours / 24.0
            args.duration_source = "hours"
            logging.debug(f"Duration from --hours: {args.hours}h = {args.duration_days} days")

        elif args.days is not None:
            # Use days directly
            args.duration_hours = args.days * 24
            args.duration_days = float(args.days)
            args.duration_source = "days"
            logging.debug(f"Duration from --days: {args.days} days = {args.duration_hours}h")

        else:
            # No duration specified - will use config default
            args.duration_hours = None
            args.duration_days = None
            args.duration_source = None

        # Clean up original arguments
        del args.days
        del args.hours

    def _validate_cachedir(self, args):
        """Validate cache directory option"""
        if hasattr(args, 'cachedir') and args.cachedir:
            try:
                args.cachedir.parent.mkdir(parents=True, exist_ok=True)
                # Test write access
                test_file = args.cachedir.parent / ".write_test"
                test_file.touch()
                test_file.unlink()
            except Exception as e:
                self.parser.error(f"Cannot access cache directory parent {args.cachedir.parent}: {e}")

    def _process_lineup_and_location(self, args):
        """Process lineup and location arguments with intelligent extraction"""
        location_code = args.zip or args.postal or args.code
        lineupid = args.lineupid

        # Extract postal/ZIP from lineupid if it's an OTA format
        extracted_location = None
        if lineupid:
            extracted_location = self._extract_location_from_lineup(lineupid)

        # Validation and consistency logic
        if extracted_location and location_code:
            # Verify consistency
            clean_extracted = extracted_location.replace(" ", "").upper()
            clean_provided = location_code.replace(" ", "").upper()

            if clean_extracted != clean_provided:
                normalized_extracted = extracted_location.replace(" ", "")
                self.parser.error(
                    f"Inconsistent location codes: lineupid contains '{normalized_extracted}' "
                    f"but explicit location is '{location_code}'. They must match."
                )

            final_location = location_code
            args.location_source = "explicit"

        elif extracted_location and not location_code:
            final_location = extracted_location
            args.location_source = "extracted"
            logging.debug(f"Extracted location '{extracted_location}' from lineupid '{lineupid}'")

        elif location_code:
            final_location = location_code
            args.location_source = "explicit"

        else:
            final_location = None
            args.location_source = None

        # Validate the final location code
        if final_location:
            clean_code = final_location.replace(" ", "")
            if not (
                self.CA_CODE_PATTERN.match(final_location) or self.US_CODE_PATTERN.match(clean_code)
            ):
                source = (
                    "lineupid" if extracted_location and not location_code else "explicit parameter"
                )
                display_location = (
                    final_location.replace(" ", "")
                    if extracted_location and not location_code
                    else final_location
                )
                self.parser.error(
                    f"Invalid location code from {source}: {display_location}. "
                    "Expected US ZIP (12345) or Canadian postal (A1A1A1)"
                )

        # Store results
        if final_location:
            args.location_code = final_location.replace(" ", "")
        else:
            args.location_code = None

        args.original_lineupid = lineupid
        args.extracted_location = (
            extracted_location.replace(" ", "") if extracted_location else None
        )

        # Clean up individual fields
        del args.zip, args.postal, args.code

    def _extract_location_from_lineup(self, lineupid: str) -> Optional[str]:
        """Extract postal/ZIP code from lineup ID if it's in OTA format"""
        import re

        ota_pattern = re.compile(r"^(CAN|USA)-OTA([A-Z0-9]+)(?:-DEFAULT)?$", re.IGNORECASE)
        match = ota_pattern.match(lineupid.strip())

        if match:
            country = match.group(1).upper()
            location = match.group(2).upper()

            if country == "CAN":
                if re.match(r"^[A-Z][0-9][A-Z][0-9][A-Z][0-9]$", location):
                    return f"{location[:3]} {location[3:]}"
            elif country == "USA":
                if re.match(r"^[0-9]{5}$", location):
                    return location

        return None

    def _normalize_langdetect(self, args):
        """Normalize langdetect option"""
        if args.langdetect:
            args.langdetect = args.langdetect.lower() == "true"
        else:
            args.langdetect = None

    def _normalize_refresh(self, args):
        """Normalize refresh options"""
        if args.norefresh:
            args.refresh_hours = 0
        elif args.refresh is not None:
            args.refresh_hours = args.refresh
        else:
            args.refresh_hours = None

        # Clean up individual fields
        del args.norefresh
        if hasattr(args, "refresh"):
            del args.refresh

    def _process_unified_performance_options(self, args):
        """Process unified performance options with strategy support"""

        # Process parallel enable/disable
        if args.no_parallel:
            args.parallel_enabled = False
        elif args.parallel:
            args.parallel_enabled = True
        else:
            args.parallel_enabled = True  # Default enabled

        # Clean up redundant flags
        if hasattr(args, 'parallel'):
            del args.parallel
        if hasattr(args, 'no_parallel'):
            del args.no_parallel

        # Process adaptive mode - default enabled
        if hasattr(args, 'no_adaptive') and args.no_adaptive:
            args.adaptive_enabled = False
        elif hasattr(args, 'adaptive') and args.adaptive:
            args.adaptive_enabled = True
        else:
            args.adaptive_enabled = True  # Default enabled

        # Clean up redundant flags
        if hasattr(args, 'adaptive'):
            del args.adaptive
        if hasattr(args, 'no_adaptive'):
            del args.no_adaptive

        # Process worker strategy
        if hasattr(args, 'strategy') and args.strategy:
            args.worker_strategy = args.strategy
        else:
            args.worker_strategy = None  # Will be auto-determined

        # Clean up strategy arg
        if hasattr(args, 'strategy'):
            del args.strategy

        # Validate workers
        if args.workers is not None:
            if args.workers < 1:
                args.workers = 1
            elif args.workers > 10:
                self.parser.error("Maximum 10 workers allowed to prevent server overload")
        else:
            args.workers = None

        # Validate rate limit
        if args.rate_limit is not None:
            if args.rate_limit < 0.5:
                self.parser.error("Rate limit must be at least 0.5 requests per second")
            elif args.rate_limit > 20:
                self.parser.error("Rate limit cannot exceed 20 requests per second")
        else:
            args.rate_limit = None

        # Force sequential adjustments
        if not args.parallel_enabled:
            args.workers = 1
            args.worker_strategy = 'conservative'
            args.adaptive_enabled = False

        # Disable adaptive for single worker
        if args.workers == 1:
            args.adaptive_enabled = False

    def _process_monitoring_options(self, args):
        """Process monitoring options with validation"""

        # Set monitoring defaults with proper None handling
        args.enable_monitoring = getattr(args, 'monitoring', False)
        args.enable_web_api = getattr(args, 'web_api', False)

        # Handle monitoring_port properly - it might be None even with default=9989
        monitoring_port = getattr(args, 'monitoring_port', None)
        args.monitoring_port = monitoring_port if monitoring_port is not None else 9989

        # Validate web API requires monitoring
        if args.enable_web_api and not args.enable_monitoring:
            self.parser.error("--web-api requires --monitoring")

        # Validate monitoring port - now safe since we ensured it's not None
        if args.monitoring_port < 1024 or args.monitoring_port > 65535:
            self.parser.error(f"Monitoring port must be 1024-65535, got: {args.monitoring_port}")

        # Clean up monitoring arguments
        if hasattr(args, 'monitoring'):
            del args.monitoring
        if hasattr(args, 'web_api'):
            del args.web_api

    def get_logging_config(self, args):
        """Determine logging configuration from arguments"""
        config = {
            "level": "default",
            "console": False,
            "quiet": False,
        }

        if args.debug:
            config["level"] = "debug"
        elif args.warning:
            config["level"] = "warning"

        if args.console:
            config["console"] = True
        elif args.quiet:
            config["quiet"] = True

        return config

    def get_unified_config(self, args):
        """Get unified download configuration from parsed arguments"""
        return {
            'enabled': getattr(args, 'parallel_enabled', True),
            'max_workers': getattr(args, 'workers', None),
            'worker_strategy': getattr(args, 'worker_strategy', None),
            'enable_adaptive': getattr(args, 'adaptive_enabled', True),
            'rate_limit': getattr(args, 'rate_limit', None),
            'enable_monitoring': getattr(args, 'enable_monitoring', False),
            'enable_web_api': getattr(args, 'enable_web_api', False),
            'monitoring_port': getattr(args, 'monitoring_port', 9989),
        }

    def get_system_defaults(self, cachedir_override: Path = None):
        """Get system-specific default directories with cache override support"""
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
                base_dir = Path("/var/packages/tvheadend/target/var/epggrab/gracenote2epg")
            else:
                base_dir = Path("/var/packages/tvheadend/var/epggrab/gracenote2epg")

            logging.debug(f"Synology detected - DSM version: {dsm_version}, path: {base_dir}")

            # Verify the parent directory exists, fallback if not
            if not base_dir.parent.exists():
                logging.warning(f"Expected Synology TVheadend path {base_dir.parent} doesn't exist")

                for check_path in [
                    "/var/packages/tvheadend/var",
                    "/var/packages/tvheadend/target/var",
                ]:
                    if Path(check_path).exists():
                        logging.warning(f"Found alternative path: {check_path}")
                        base_dir = Path(check_path) / "epggrab" / "gracenote2epg"
                        break
                else:
                    logging.warning("No TVheadend paths found, using home directory")
                    base_dir = home / "gracenote2epg"

        else:
            # Standard Linux/Docker
            base_dir = home / "gracenote2epg"

        # Determine cache directory with override support
        if cachedir_override:
            cache_dir = cachedir_override
        else:
            cache_dir = base_dir / "cache"

        return {
            "base_dir": base_dir,
            "cache_dir": cache_dir,
            "conf_dir": base_dir / "conf",
            "log_dir": base_dir / "log",
            "config_file": base_dir / "conf" / "gracenote2epg.xml",
            "xmltv_file": cache_dir / "xmltv.xml",
            "log_file": base_dir / "log" / "gracenote2epg.log",
        }

    def create_directories_with_proper_permissions(self):
        """Create required directories with proper 755 permissions"""
        defaults = self.get_system_defaults()

        for directory in [defaults["cache_dir"], defaults["conf_dir"], defaults["log_dir"]]:
            try:
                directory.mkdir(parents=True, exist_ok=True, mode=0o755)
            except Exception:
                directory.mkdir(parents=True, exist_ok=True)

    def _detect_system_type(self):
        """Detect system type for default directories"""
        import platform

        # Check if Raspberry Pi
        device_tree_model = Path("/proc/device-tree/model")
        if device_tree_model.exists():
            try:
                with open(device_tree_model) as f:
                    if "raspberry" in f.read().lower():
                        return "raspberry"
            except Exception:
                pass

        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.exists():
            try:
                with open(cpuinfo) as f:
                    if "raspberry" in f.read().lower():
                        return "raspberry"
            except Exception:
                pass

        # Enhanced Synology detection
        if Path("/etc/synoinfo.conf").exists():
            return "synology"

        try:
            version_file = Path("/etc/VERSION")
            if version_file.exists():
                with open(version_file, "r") as f:
                    content = f.read().lower()
                    if "synology" in content or (
                        "majorversion=" in content and "buildnumber=" in content
                    ):
                        return "synology"
        except Exception:
            pass

        if (
            Path("/var/packages/tvheadend/var").exists()
            or Path("/var/packages/tvheadend/target/var").exists()
        ):
            return "synology"

        try:
            if "synology" in platform.uname().release.lower():
                return "synology"
        except Exception:
            pass

        return "linux"

    def _get_dsm_version(self):
        """Get Synology DSM version number"""
        import re

        try:
            version_file = Path("/etc/VERSION")
            if version_file.exists():
                with open(version_file, "r") as f:
                    content = f.read()

                major_match = re.search(r'majorversion="?(\d+)"?', content)
                build_match = re.search(r'buildnumber="?(\d+)"?', content)

                if major_match:
                    major_version = int(major_match.group(1))

                    if build_match:
                        return int(build_match.group(1))

                    # Fallback to major version mapping
                    if major_version >= 7:
                        return 50000  # DSM7+
                    elif major_version >= 6:
                        return 30000  # DSM6
                    else:
                        return 20000  # DSM5

        except Exception:
            pass

        # Fallback based on directory structure
        try:
            if (
                Path("/var/packages/tvheadend/var").exists()
                and not Path("/var/packages/tvheadend/target/var").exists()
            ):
                return 50000  # DSM7+
            elif Path("/var/packages/tvheadend/target/var").exists():
                return 30000  # DSM6
            elif Path("/var/packages/tvheadend/var").exists():
                return 50000  # DSM7+
        except Exception:
            pass

        return 50000  # Default to DSM7+

    def get_strategy_help(self) -> str:
        """Get detailed strategy help information"""
        return """
Worker Strategy Details:

CONSERVATIVE (gentle on servers):
  • Guide blocks: 2-3 workers, 3.0 req/s
  • Series details: 1-2 workers, 1.5 req/s
  • Best for: Shared connections, rate-limited environments
  • Adaptive: Minimal adjustments, prioritizes stability

BALANCED (optimal for most users):
  • Guide blocks: 4-6 workers, 5.0 req/s
  • Series details: 2-3 workers, 2.5 req/s
  • Best for: Standard home connections, typical usage
  • Adaptive: Moderate adjustments based on performance

AGGRESSIVE (maximum performance):
  • Guide blocks: 6-10 workers, 8.0 req/s
  • Series details: 3-4 workers, 4.0 req/s
  • Best for: Dedicated servers, high-bandwidth connections
  • Adaptive: Dynamic adjustments for optimal throughput

Strategy selection is automatic based on worker count if not specified.
Use environment variable GRACENOTE_WORKER_STRATEGY to override defaults.
"""

    def print_strategy_info(self):
        """Print strategy information and exit"""
        print(self.get_strategy_help())
        sys.exit(0)
