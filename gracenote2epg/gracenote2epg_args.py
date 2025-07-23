#!/usr/bin/env python3
"""
Command-line argument management module for gracenote2epg
Replaces the logic from the bash script tv_grab_gracenote2epg
"""

import os
import sys
import argparse
import re
import logging
import time
from typing import Tuple, Optional


class GracenoteEPGArgumentParser:
    """
    Command-line argument manager for gracenote2epg
    """

    def __init__(self):
        self.base_dir = self._detect_base_dir()
        self.cache_dir = os.path.join(self.base_dir, "cache")
        self.conf_dir = os.path.join(self.base_dir, "conf")
        self.log_dir = os.path.join(self.base_dir, "log")
        self.conf_file = os.path.join(self.conf_dir, "gracenote2epg.xml")
        self.log_file = os.path.join(self.log_dir, "gracenote2epg.log")
        self.xmltv_file = os.path.join(self.cache_dir, "xmltv.xml")

        # Validation patterns
        self.days_pattern = re.compile(r'^[1-9]$|^1[0-4]$')
        self.ca_code_pattern = re.compile(r'^[A-Z][0-9][A-Z][ ]?[0-9][A-Z][0-9]$')
        self.us_code_pattern = re.compile(r'^[0-9]{5}$')

        # Parsed arguments
        self.quiet = False
        self.country = ""
        self.zipcode = ""
        self.offset = ""
        self.days = ""

    def _detect_base_dir(self) -> str:
        """
        Detect base directory according to environment

        Returns:
            str: Base directory path
        """
        # Default path for RaspPi Kodi+TVH
        base_dir = os.path.join(os.path.expanduser("~"), "gracenote2epg")

        # If running on common linux under hts user
        try:
            import pwd
            if pwd.getpwnam('hts'):
                base_dir = os.path.join(os.path.expanduser("~"), "gracenote2epg")
        except (KeyError, ImportError):
            pass

        # If running on synology NAS check DSM version for proper path
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read()
                if 'synology' in version_info.lower():
                    # Use the local virtualenv python path
                    os.environ['PATH'] = '/var/packages/tvheadend/target/env/bin:' + os.environ.get('PATH', '')

                    # Extract DSM version
                    version_match = re.search(r'#(\d+)', version_info)
                    if version_match:
                        version_num = int(version_match.group(1))
                        if version_num < 40000:
                            # DSM6
                            base_dir = "/var/packages/tvheadend/target/var/epggrab"
                        else:
                            # DSM7
                            base_dir = "/var/packages/tvheadend/var/epggrab"
        except (FileNotFoundError, PermissionError):
            pass

        return base_dir

    def create_directories(self):
        """
        Create necessary working directories
        """
        directories = [self.cache_dir, self.log_dir, self.conf_dir]

        for directory in directories:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory, mode=0o755, exist_ok=True)
                    print(f"Created directory: {directory}", file=sys.stderr)
                except PermissionError:
                    print(f"Error: Permission denied creating directory: {directory}", file=sys.stderr)
                    sys.exit(1)
                except Exception as e:
                    print(f"Error creating directory {directory}: {e}", file=sys.stderr)
                    sys.exit(1)

    def create_default_config(self):
        """
        Create default configuration file if it doesn't exist
        """
        if not os.path.exists(self.conf_file):
            default_config = '''<settings version="3">
  <setting id="useragent">Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0</setting>
  <setting id="country">USA</setting>
  <setting id="zipcode">12979</setting>
  <setting id="lineupcode">lineupId</setting>
  <setting id="lineup">Local Over the Air Broadcast</setting>
  <setting id="device">-</setting>
  <setting id="days">1</setting>
  <setting id="redays">1</setting>
  <setting id="slist"></setting>
  <setting id="stitle">false</setting>
  <setting id="xdetails">true</setting>
  <setting id="xdesc">true</setting>
  <setting id="epgenre">3</setting>
  <setting id="epicon">1</setting>
  <setting id="usern"></setting>
  <setting id="passw"></setting>
  <setting id="tvhurl">127.0.0.1</setting>
  <setting id="tvhport">9981</setting>
  <setting id="tvhmatch">false</setting>
  <setting id="chmatch">false</setting>
</settings>'''

            try:
                with open(self.conf_file, 'w', encoding='utf-8') as f:
                    f.write(default_config)
                print(f"Created default configuration: {self.conf_file}", file=sys.stderr)
            except Exception as e:
                print(f"Error creating default configuration: {e}", file=sys.stderr)
                sys.exit(1)

    def validate_arguments(self) -> bool:
        """
        Validate arguments and environment

        Returns:
            bool: True if everything is valid
        """
        # Check output directory
        output_dir = os.path.dirname(self.xmltv_file)
        if not os.path.isdir(output_dir):
            print(f"Output directory for [{os.path.basename(self.xmltv_file)}] is inaccessible: {output_dir}", file=sys.stderr)
            return False

        if not os.access(output_dir, os.W_OK):
            print(f"Output directory for [{os.path.basename(self.xmltv_file)}] is not write accessible: {output_dir}", file=sys.stderr)
            return False

        # Check configuration file
        if not os.path.isfile(self.conf_file):
            print(f"Configuration file missing: {self.conf_file}", file=sys.stderr)
            return False

        # Validate offset
        if self.offset and not self.days_pattern.match(self.offset):
            print(f"Parameter [--offset] unmatched: {self.offset}", file=sys.stderr)
            return False

        # Validate days
        if self.days and not self.days_pattern.match(self.days):
            print(f"Parameter [--days] unmatched: {self.days}", file=sys.stderr)
            return False

        # Validate postal code
        if self.zipcode:
            if not (self.ca_code_pattern.match(self.zipcode) or self.us_code_pattern.match(self.zipcode)):
                print(f"Parameter [--zip|--postal|--code] unmatched: {self.zipcode}", file=sys.stderr)
                return False

        return True

    def setup_environment(self):
        """
        Configure necessary environment variables
        """
        # Environment variables for compatibility
        os.environ['CacheDir'] = os.path.relpath(self.cache_dir, self.base_dir)
        os.environ['ConfDir'] = os.path.relpath(self.conf_dir, self.base_dir)
        os.environ['ConfFile'] = os.path.relpath(self.conf_file, self.base_dir)
        os.environ['LogDir'] = os.path.relpath(self.log_dir, self.base_dir)
        os.environ['LogFile'] = os.path.relpath(self.log_file, self.base_dir)
        os.environ['XMLTV'] = os.path.relpath(self.xmltv_file, self.base_dir)

        # Optional arguments
        if self.days:
            os.environ['Days'] = self.days
        if self.offset:
            os.environ['Offset'] = self.offset
        if self.country:
            os.environ['Country'] = self.country
        if self.zipcode:
            os.environ['ZipCode'] = self.zipcode

    def parse_arguments(self) -> Tuple[bool, str]:
        """
        Parse command-line arguments

        Returns:
            Tuple (success: bool, working_directory: str)
        """
        # Detect if called via tv_grab_gracenote2epg
        script_name = os.path.basename(sys.argv[0])
        is_tvheadend_mode = script_name.startswith('tv_grab_')

        parser = argparse.ArgumentParser(
            prog=script_name,
            description='North America TV schedule grabber (tvlistings.gracenote.com)',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=f'''
Examples:
  {script_name}                                    # Default INFO logging
  {script_name} --days 3 --offset 1              # 3 days, 1 day offset
  {script_name} --zip 12979 --output /tmp/guide.xml
  {script_name} --config-file /path/to/custom_config.xml
  {script_name} --debug                           # Debug logging (most verbose)
  {script_name} --warning                         # Warning logging only
  {script_name} --silent                          # Silent mode (errors only)

Logging Levels:
  --debug      Show DEBUG, INFO, WARNING, ERROR messages (most verbose)
  (default)    Show INFO, WARNING, ERROR messages (recommended)
  --warning    Show WARNING, ERROR messages only
  --silent     Show ERROR messages only (least verbose)

TVHeadend Integration:
  This grabber is compatible with TVHeadend EPG sources.
  Use '{script_name}' as the grabber name in TVHeadend configuration.
            '''
        )

        parser.add_argument('-d', '--description',
                           action='store_true',
                           help='Show description and exit')

        parser.add_argument('-v', '--version',
                           action='store_true',
                           help='Show version and exit')

        parser.add_argument('-c', '--capabilities',
                           action='store_true',
                           help='Show capabilities and exit')

        parser.add_argument('-q', '--quiet',
                           action='store_true',
                           help='Quiet mode - do not output XMLTV to stdout')

        parser.add_argument('-o', '--output',
                           metavar='FILE',
                           help='Output XMLTV file path')

        parser.add_argument('--days',
                           metavar='N',
                           help='Number of days to grab (1-14)')

        parser.add_argument('--offset',
                           metavar='N',
                           help='Day offset (0-9)')

        parser.add_argument('--config-file',
                           metavar='FILE',
                           help='Configuration file path')

        parser.add_argument('--zip', '--postal', '--code',
                           dest='zipcode',
                           metavar='CODE',
                           help='ZIP code (US) or postal code (CA)')

        parser.add_argument('--base-dir',
                           metavar='DIR',
                           help='Base directory for cache/config/logs')

        parser.add_argument('--debug',
                           action='store_true',
                           help='Enable debug logging (most verbose)')

        parser.add_argument('--warning',
                           action='store_true',
                           help='Enable warning level logging')

        parser.add_argument('--silent',
                           action='store_true',
                           help='Silent mode - only log errors')

        args = parser.parse_args()

        # Handle information flags
        if args.description:
            print("North America (tvlistings.gracenote.com using gracenote2epg)")
            sys.exit(0)

        if args.version:
            print("4.0")
            sys.exit(0)

        if args.capabilities:
            print("baseline")
            sys.exit(0)

        # Configure attributes
        self.quiet = args.quiet
        self.days = args.days
        self.offset = args.offset
        self.zipcode = args.zipcode.replace(' ', '') if args.zipcode else ''

        # Custom base directory
        if args.base_dir:
            self.base_dir = os.path.abspath(args.base_dir)
            self.cache_dir = os.path.join(self.base_dir, "cache")
            self.conf_dir = os.path.join(self.base_dir, "conf")
            self.log_dir = os.path.join(self.base_dir, "log")
            self.conf_file = os.path.join(self.conf_dir, "gracenote2epg.xml")
            self.log_file = os.path.join(self.log_dir, "gracenote2epg.log")
            self.xmltv_file = os.path.join(self.cache_dir, "xmltv.xml")

        # Custom configuration file
        if args.config_file:
            self.conf_file = os.path.abspath(args.config_file)
            self.conf_dir = os.path.dirname(self.conf_file)

        # Custom output file
        if args.output:
            self.xmltv_file = os.path.abspath(args.output)

        # Logging configuration - level hierarchy
        if args.debug:
            log_level = logging.DEBUG
            log_description = "debug"
        elif args.warning:
            log_level = logging.WARNING
            log_description = "warning"
        elif args.silent:
            log_level = logging.ERROR
            log_description = "silent (errors only)"
        else:
            # Default: INFO (always show important information)
            log_level = logging.INFO
            log_description = "info (default)"

        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.log_file), mode=0o755, exist_ok=True)

        logging.basicConfig(
            filename=self.log_file,
            filemode='w',
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y/%m/%d %H:%M:%S',
            level=log_level
        )

        # Log operating mode
        if is_tvheadend_mode:
            logging.info(f'Starting gracenote2epg in TVHeadend mode (called as {script_name}) - Log level: {log_description}')
        else:
            logging.info(f'Starting gracenote2epg in standalone mode - Log level: {log_description}')

        return True, self.base_dir

    def initialize(self) -> Tuple[bool, str]:
        """
        Initialize environment completely

        Returns:
            Tuple (success: bool, working_directory: str)
        """
        try:
            # Parse arguments
            success, working_dir = self.parse_arguments()
            if not success:
                return False, ""

            # Create directories
            self.create_directories()

            # Create default configuration if needed
            self.create_default_config()

            # Validate arguments
            if not self.validate_arguments():
                return False, ""

            # Configure environment
            self.setup_environment()

            return True, working_dir

        except Exception as e:
            print(f"Error during initialization: {e}", file=sys.stderr)
            return False, ""

    def should_output_xmltv(self) -> bool:
        """
        Determine if XMLTV file should be displayed on stdout

        Returns:
            bool: True if should display
        """
        return not self.quiet

    def get_xmltv_output_path(self) -> str:
        """
        Return XMLTV output file path

        Returns:
            str: XMLTV file path
        """
        return self.xmltv_file


def create_argument_parser() -> GracenoteEPGArgumentParser:
    """
    Factory function to create an argument parser

    Returns:
        GracenoteEPGArgumentParser instance
    """
    return GracenoteEPGArgumentParser()


def main_with_args():
    """
    Main entry point with argument management
    """
    parser = create_argument_parser()
    success, working_dir = parser.initialize()

    if not success:
        sys.exit(1)

    # Import main class directly from gracenote2epg.py
    try:
        import importlib.util

        # Look for gracenote2epg.py file in parent directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        main_script = os.path.join(parent_dir, 'gracenote2epg.py')

        if not os.path.exists(main_script):
            print(f"Error: Cannot find gracenote2epg.py at {main_script}", file=sys.stderr)
            sys.exit(1)

        # Dynamic import of main script
        spec = importlib.util.spec_from_file_location("gracenote2epg_main", main_script)
        gracenote2epg_main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gracenote2epg_main)

        # Get the class
        GracenoteEPGApplication = gracenote2epg_main.GracenoteEPGApplication

    except Exception as e:
        print(f"Error importing gracenote2epg main script: {e}", file=sys.stderr)
        sys.exit(1)

    # Execute application
    app = GracenoteEPGApplication(working_dir)
    result = app.run()

    if result and result[0] is not None:
        time_run, station_count, episode_count = result

        # Display XMLTV if requested
        if parser.should_output_xmltv():
            try:
                xmltv_path = parser.get_xmltv_output_path()
                with open(xmltv_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Remove trailing newline to avoid extra blank line
                    print(content.rstrip('\n'))
            except Exception as e:
                logging.error(f"Error reading XMLTV output: {e}")

        print(f"Execution completed in {time_run} seconds", file=sys.stderr)
        print(f"{station_count} stations and {episode_count} episodes processed", file=sys.stderr)
        sys.exit(0)
    else:
        print("An error occurred during execution", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main_with_args()
