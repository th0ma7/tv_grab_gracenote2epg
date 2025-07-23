#!/usr/bin/env python3
"""
gracenote2epg - TV Guide grabber for TVHeadend (Version 4.0)
Main executable script with command-line argument support
"""

import os
import sys
import time
import datetime
import logging
from typing import Tuple, Optional

# Import gracenote2epg modules
from gracenote2epg.gracenote2epg_config import create_config_manager, validate_environment_quick
from gracenote2epg.gracenote2epg_tvheadend import create_tvheadend_manager, TVHeadendConfig
from gracenote2epg.gracenote2epg_downloader import create_downloader, calculate_grid_times
from gracenote2epg.gracenote2epg_parser import parseStations, parseEpisodes, debug_station_icons
from gracenote2epg.gracenote2epg_xmltv import create_xmltv_generator, XMLTVValidator
from gracenote2epg.gracenote2epg_utils import genShowList, deleteOldShowCache


class GracenoteEPGApplication:
    """
    Main gracenote2epg application class
    """

    def __init__(self, userdata_dir: str):
        """
        Initialize the application

        Args:
            userdata_dir: User data directory path
        """
        self.userdata = userdata_dir
        self.config_manager = None
        self.config = {}
        self.schedule = {}
        self.tvh_match_dict = {}
        self.execution_stats = {
            'start_time': 0,
            'end_time': 0,
            'station_count': 0,
            'episode_count': 0,
            'download_count': 0,
            'download_errors': 0
        }

    def initialize(self) -> bool:
        """
        Initialize application and load configuration

        Returns:
            bool: True if successful
        """
        try:
            self.execution_stats['start_time'] = time.time()

            # Quick environment validation
            if not validate_environment_quick():
                return False

            # Create and configure the configuration manager
            self.config_manager = create_config_manager(self.userdata)

            # Complete environment validation
            success, error_msg = self.config_manager.validate_environment()
            if not success:
                logging.error(error_msg)
                return False

            # Load XML settings
            if not self.config_manager.load_xml_settings():
                return False

            # Merge environment settings
            if not self.config_manager.merge_environment_settings():
                return False

            # Detect country and calculate offset
            self.config_manager.detect_country()
            self.config_manager.calculate_offset()

            # Get final configuration
            self.config = self.config_manager.get_config()

            # Display configuration
            self.config_manager.log_configuration()

            return True

        except Exception as e:
            logging.exception('Exception during initialization: %s', str(e))
            return False

    def setup_tvheadend_integration(self) -> bool:
        """
        Configure TVHeadend integration

        Returns:
            bool: True if successful or if TVH is not used
        """
        try:
            tvh_config = TVHeadendConfig()

            # If TVHeadend is enabled in config (tvhmatch=true)
            if self.config_manager.get_xml_setting('tvhmatch') == 'true':
                tvh_manager = create_tvheadend_manager(
                    self.config_manager.get_xml_setting('tvhurl', '127.0.0.1'),
                    self.config_manager.get_xml_setting('tvhport', '9981'),
                    self.config_manager.get_xml_setting('usern'),
                    self.config_manager.get_xml_setting('passw')
                )

                # Test connection and retrieve channels
                if tvh_manager.test_connection():
                    channels, success = tvh_manager.get_channels()
                    if success and len(channels) > 0:
                        self.tvh_match_dict = channels
                        logging.info('TVHeadend integration SUCCESS with %d channels', len(channels))
                    else:
                        tvh_config.disable_tvh_features("Failed to retrieve channels")
                        logging.warning('TVHeadend integration FAILED - no channels retrieved')
                else:
                    tvh_config.disable_tvh_features("Connection test failed")
                    logging.warning('TVHeadend integration FAILED - connection test failed')
            else:
                logging.info('TVHeadend integration DISABLED in configuration')

            # Final TVHeadend configuration
            self.config_manager.setup_tvheadend_config(self.tvh_match_dict)
            self.config = self.config_manager.get_config()

            return True

        except Exception as e:
            logging.exception('Exception during TVHeadend setup: %s', str(e))
            return False

    def download_guide_data(self) -> bool:
        """
        Download all guide data

        Returns:
            bool: True if successful
        """
        try:
            # Create downloader
            downloader = create_downloader(self.config)

            # Ensure cache directory exists
            if not downloader.ensure_cache_directory():
                return False

            # Calculate download parameters
            days = int(self.config.get('days', '1'))
            day_hours = days * 8  # 8 blocks of 3 hours per day

            grid_start = int(time.mktime(time.strptime(
                str(datetime.datetime.now().replace(microsecond=0, second=0, minute=0)),
                '%Y-%m-%d %H:%M:%S'
            ))) + self.config.get('offset', 0) * 86400

            logging.info('\tTV Guide duration: %s days (%d x 3-hour blocks)', days, day_hours)
            logging.info('\tTV Guide Start: %i', int(grid_start))

            # Cleanup old files
            redays = self.config.get('redays', '1')
            downloader.cleanup_old_cache(grid_start, redays)

            # Calculate timestamps to download
            grid_times = calculate_grid_times(grid_start, day_hours)
            logging.info('Downloading %d data blocks from Gracenote API...', len(grid_times))

            # Download data
            for count, gridtime in enumerate(grid_times):
                if not downloader.file_exists_in_cache(gridtime):
                    success = downloader.download_and_cache(gridtime)
                    if not success:
                        logging.warning('Failed to download data for gridtime: %i', gridtime)
                else:
                    logging.debug('Using cached data for gridtime: %i', gridtime)

                # Process downloaded data
                content = downloader.read_cached_file(gridtime)
                if content:
                    self._process_downloaded_content(content, count == 0, downloader, gridtime)

            # Download statistics
            download_count, error_count = downloader.get_download_stats()
            self.execution_stats['download_count'] = download_count
            self.execution_stats['download_errors'] = error_count

            # Debug icons if requested
            if logging.getLogger().level <= logging.DEBUG:
                debug_station_icons(self.schedule)

            logging.info('Download phase completed: %d downloads, %d errors',
                        download_count, error_count)

            return True

        except Exception as e:
            logging.exception('Exception during guide data download: %s', str(e))
            return False

    def _process_downloaded_content(self, content: str, is_first: bool,
                                  downloader, gridtime: int):
        """
        Process downloaded content

        Args:
            content: JSON content
            is_first: True if this is the first file
            downloader: Downloader instance
            gridtime: Grid timestamp
        """
        try:
            filename = str(int(gridtime)) + '.json.gz'
            logging.info('Parsing %s', filename)

            # Parse stations (only for the first file)
            if is_first:
                station_count = parseStations(content, self.config, self.schedule, self.tvh_match_dict)
                logging.info('Parsed %d stations from first file', station_count)

            # Parse episodes
            tba_check = parseEpisodes(content, self.config, self.schedule)

            # TBA check - remove file if problematic
            if tba_check == "Unsafe":
                try:
                    file_path = downloader.get_cached_file_path(gridtime)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logging.info('Deleting %s due to TBA listings', filename)
                except OSError as e:
                    logging.warning('Error Deleting: %s - %s.' % (e.filename, e.strerror))

        except Exception as e:
            logging.warning('Error processing content for %s: %s', gridtime, str(e))

    def generate_xmltv_output(self) -> bool:
        """
        Generate XMLTV output file

        Returns:
            bool: True if successful
        """
        try:
            # Generate show list for cleanup
            show_list = genShowList(self.schedule)
            cache_dir = self.config.get('cacheDir')
            if cache_dir:
                deleteOldShowCache(show_list, cache_dir)

            # Generate XMLTV file
            xmltv_generator = create_xmltv_generator(self.config)
            station_count, episode_count = xmltv_generator.generate_xmltv_file(self.schedule)

            self.execution_stats['station_count'] = station_count
            self.execution_stats['episode_count'] = episode_count

            # Validate generated file
            output_file = os.path.join(self.config['userdata'],
                                     os.environ.get('XMLTV', 'xmltv.xml'))

            validator = XMLTVValidator()
            is_valid, message = validator.validate_xmltv_file(output_file)

            if is_valid:
                logging.info('XMLTV file validation: %s', message)
                return True
            else:
                logging.error('XMLTV file validation failed: %s', message)
                return False

        except Exception as e:
            logging.exception('Exception during XMLTV generation: %s', str(e))
            return False

    def finalize(self):
        """
        Finalize execution and display statistics
        """
        self.execution_stats['end_time'] = time.time()
        time_run = round(self.execution_stats['end_time'] - self.execution_stats['start_time'], 2)

        logging.info('gracenote2epg completed in %s seconds.', time_run)
        logging.info('%s Stations and %s Episodes written to xmltv.xml file.',
                    str(self.execution_stats['station_count']),
                    str(self.execution_stats['episode_count']))

        if self.execution_stats['download_count'] > 0:
            days = int(self.config.get('days', 1))
            expected_downloads = days * 8  # 8 blocks of 3h per day

            logging.info('Guide data downloads: %d/%d successful (%.1f%%), %d errors',
                        self.execution_stats['download_count'],
                        expected_downloads,
                        (self.execution_stats['download_count'] / expected_downloads * 100) if expected_downloads > 0 else 0,
                        self.execution_stats['download_errors'])

            if self.execution_stats['download_errors'] > 0:
                logging.warning('Some downloads failed - guide data may be incomplete')
            else:
                logging.info('All guide data downloaded successfully')

    def run(self) -> Tuple[Optional[float], int, int]:
        """
        Run the complete application

        Returns:
            Tuple (execution time, station count, episode count)
        """
        try:
            # Initialization
            if not self.initialize():
                logging.error('Application initialization failed')
                return None, 0, 0

            # TVHeadend configuration
            if not self.setup_tvheadend_integration():
                logging.error('TVHeadend setup failed')
                return None, 0, 0

            # Download guide data
            if not self.download_guide_data():
                logging.error('Guide data download failed')
                return None, 0, 0

            # Generate XMLTV
            if not self.generate_xmltv_output():
                logging.error('XMLTV generation failed')
                return None, 0, 0

            # Finalization
            self.finalize()

            time_run = round(self.execution_stats['end_time'] - self.execution_stats['start_time'], 2)
            return time_run, self.execution_stats['station_count'], self.execution_stats['episode_count']

        except Exception as e:
            logging.exception('Exception in main run: %s', str(e))
            return None, 0, 0


def mainRun(userdata: str) -> Tuple[Optional[float], int, int]:
    """
    Main function (compatibility interface)

    Args:
        userdata: User data directory

    Returns:
        Tuple (execution time, station count, episode count)
    """
    logging.info('Running gracenote2epg-4.0 (Modular Architecture)')

    app = GracenoteEPGApplication(userdata)
    return app.run()


if __name__ == '__main__':
    # Detect execution mode
    script_name = os.path.basename(sys.argv[0])
    is_tvheadend_mode = script_name.startswith('tv_grab_')

    # If called with arguments OR in TVHeadend mode, use argument parser
    if len(sys.argv) > 1 or is_tvheadend_mode:
        try:
            from gracenote2epg.gracenote2epg_args import main_with_args
            main_with_args()
        except ImportError:
            print("Error: gracenote2epg_args module not found", file=sys.stderr)
            sys.exit(1)
    else:
        # Compatibility mode - use environment variables
        userdata = os.getcwd()
        log_file = os.path.join(userdata, os.environ.get('LogFile', 'gracenote2epg.log'))

        logging.basicConfig(
            filename=log_file,
            filemode='w',
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y/%m/%d %H:%M:%S',
            level=logging.INFO
        )

        # Main execution
        result = mainRun(userdata)

        if result and result[0] is not None:
            time_run, station_count, episode_count = result
            print(f"Execution completed in {time_run} seconds")
            print(f"{station_count} stations and {episode_count} episodes processed")
            sys.exit(0)
        else:
            print("An error occurred during execution")
            sys.exit(1)
