#!/usr/bin/env python3
"""
gracenote2epg - North America TV Guide Grabber

A modular Python implementation for downloading TV guide data from
tvlistings.gracenote.com with intelligent caching and TVheadend integration.
"""

import logging
import sys
import time
from pathlib import Path

# Specifics imports
from .gracenote2epg_args import ArgumentParser
from .gracenote2epg_config import ConfigManager
from .gracenote2epg_downloader import OptimizedDownloader
from .gracenote2epg_parser import GuideParser
from .gracenote2epg_tvheadend import TvheadendClient
from .gracenote2epg_utils import CacheManager, TimeUtils
from .gracenote2epg_xmltv import XmltvGenerator
from .gracenote2epg_logrotate import LogRotationManager

# Package version
from . import __version__


def check_rotation_status(log_file: Path, rotation_config: dict):
    """Check and report any rotation that occurred during startup"""
    if not rotation_config.get('enabled', False):
        return

    try:
        log_dir = log_file.parent
        log_basename = log_file.name

        # Find backup files created recently (last 10 minutes)
        import time
        recent_cutoff = time.time() - 600  # 10 minutes ago
        recent_backups = []

        for backup_file in log_dir.glob(f"{log_basename}.*"):
            if str(backup_file) != str(log_file):
                try:
                    if backup_file.stat().st_mtime > recent_cutoff:
                        recent_backups.append(backup_file)
                except:
                    continue

        if recent_backups:
            logging.info('Log Rotation Report:')
            logging.info('  Recent rotation detected - %d backup files created:', len(recent_backups))

            for backup in sorted(recent_backups):
                try:
                    size_mb = backup.stat().st_size / (1024*1024)
                    # Extract period from filename
                    period = backup.name.replace(f"{log_basename}.", "")
                    logging.info('    Created backup: %s (%.1f MB) - %s rotation',
                               backup.name, size_mb, rotation_config.get('interval', 'unknown'))
                except:
                    logging.info('    Created backup: %s', backup.name)

            current_size_mb = log_file.stat().st_size / (1024*1024) if log_file.exists() else 0
            logging.info('    Current log: %s (%.1f MB) - contains current %s only',
                       log_basename, current_size_mb, rotation_config.get('interval', 'period'))
            logging.info('  Log rotation completed successfully')
        else:
            logging.debug('No recent log rotation detected')

    except Exception as e:
        logging.debug('Error checking rotation status: %s', str(e))


def setup_logging(logging_config: dict, log_file: Path, rotation_config: dict):
    """Setup logging configuration with optional log rotation"""
    # Create log directory
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Determine file logging level based on mode
    if logging_config['level'] == 'warning':
        file_level = logging.WARNING
    elif logging_config['level'] == 'debug':
        file_level = logging.DEBUG
    else:  # default
        file_level = logging.INFO

    # Create rotating file handler (or standard file handler if rotation disabled)
    file_handler = LogRotationManager.create_rotating_handler(log_file, rotation_config)
    file_handler.setLevel(file_level)

    # Set file formatter
    file_formatter = logging.Formatter(
        '%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(file_level)

    # Clear any existing handlers and add file handler
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)

    # Console logging only if --console is specified (and not --quiet)
    # IMPORTANT: Use stderr to avoid polluting XML output on stdout
    if logging_config['console'] and not logging_config['quiet']:
        console_handler = logging.StreamHandler(sys.stderr)  # Force stderr for console output

        # Set console level to match file level
        console_handler.setLevel(file_level)

        formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Log rotation status
    if rotation_config.get('enabled', False):
        rotation_status = LogRotationManager.get_rotation_status(log_file, rotation_config)
        logging.debug('Log rotation status: interval=%s, keep=%d files, current_size=%d bytes, backups=%d',
                     rotation_status.get('interval', 'unknown'),
                     rotation_status.get('keep_files', 0),
                     rotation_status.get('current_log_size', 0),
                     rotation_status.get('backup_files_count', 0))

    # Return the file handler so it can be used for manual rotation triggering
    return file_handler


def main():
    """Main application entry point"""
    python_start_time = time.time()

    try:
        # Parse command line arguments
        arg_parser = ArgumentParser()
        args = arg_parser.parse_args()

        # Get system defaults
        defaults = arg_parser.get_system_defaults()

        # Override defaults with command line arguments
        base_dir = args.basedir or defaults['base_dir']
        config_file = args.config_file or defaults['config_file']
        xmltv_file = args.output or defaults['xmltv_file']
        log_file = defaults['log_file']

        # Ensure directories exist
        arg_parser = ArgumentParser()
        arg_parser.create_directories_with_proper_permissions()

        # Load and validate configuration
        config_manager = ConfigManager(config_file)
        config = config_manager.load_config(
            location_code=args.location_code,
            days=args.days,
            langdetect=args.langdetect,
            refresh_hours=args.refresh_hours  # NEW: Pass refresh hours
        )

        # Get log rotation configuration
        logrotate_config = config_manager.get_logrotate_config()

        # Setup logging with rotation
        logging_config = arg_parser.get_logging_config(args)
        file_handler = setup_logging(logging_config, log_file, logrotate_config)

        # FIRST: Check for log rotation (this may truncate/rebuild the log file)
        if logrotate_config.get('enabled', False) and hasattr(file_handler, '_check_startup_rotation'):
            try:
                logging.info('Checking for startup log rotation...')
                file_handler._check_startup_rotation()
                logging.info('Startup rotation check completed')
            except Exception as e:
                logging.warning('Error during startup rotation check: %s', str(e))

        # Report any rotation that occurred (includes its own separator if needed)
        check_rotation_status(log_file, logrotate_config)

        # NOW start the normal session logging with consistent separator
        logging.info('=' * 60)
        logging.info('gracenote2epg session started - Version %s', __version__)

        if logging_config['level'] == 'debug':
            logging.info('Debug logging enabled - all debug information will be logged')
        if logging_config['console']:
            logging.info('Console logging enabled - logs also displayed on stderr')

        # Log configuration summary
        logging.info('Configuration loaded from: %s', config_file)
        config_manager.log_config_summary()

        # Initialize components
        cache_manager = CacheManager(defaults['cache_dir'])

        # Setup TVheadend client if enabled
        tvh_client = None
        if config.get('tvhoff', False):
            tvh_client = TvheadendClient(
                url=config.get('tvhurl', '127.0.0.1'),
                port=config.get('tvhport', '9981'),
                username=config.get('usern') or None,
                password=config.get('passw') or None
            )

            # Fetch channels if TVheadend matching is enabled
            if config.get('tvhmatch', False):
                tvh_client.fetch_channels()
                tvh_client.log_filtering_summary(
                    explicit_station_list=config_manager.get_station_list(),
                    use_tvh_matching=config.get('tvhmatch', False)
                )

        # Calculate guide parameters
        days = int(config.get('days', 1))
        offset = float(args.offset or 0)
        day_hours = days * 8  # 8 three-hour blocks per day

        # Get refresh hours from configuration/command line
        refresh_hours = config_manager.get_refresh_hours()

        # Calculate start time
        from datetime import datetime
        now = datetime.now().replace(microsecond=0, second=0, minute=0)
        grid_time_start = int(time.mktime(now.timetuple())) + int(offset * 86400)

        # Log guide parameters
        country = config_manager.get_country()
        logging.info('Country: %s [%s]',
                    'United States of America' if country == 'USA' else 'Canada', country)
        logging.info('Location code: %s', config.get('zipcode'))
        logging.info('TV Guide duration: %s days', days)

        if offset > 1:
            logging.info('TV Guide Start: %i [offset: %i days]', grid_time_start, int(offset))
        elif offset == 1:
            logging.info('TV Guide Start: %i [offset: %i day]', grid_time_start, int(offset))
        else:
            logging.info('TV Guide Start: %i', grid_time_start)

        logging.info('Lineup: %s', config.get('lineup'))
        logging.info('Caching directory: %s', defaults['cache_dir'])

        # Log cache refresh configuration
        if refresh_hours == 0:
            logging.info('Cache refresh: disabled (--norefresh or refresh=0)')
        else:
            logging.info('Cache refresh: %d hours (first %d hours will be re-downloaded)', refresh_hours, refresh_hours)

        # Perform initial cache cleanup
        cache_manager.perform_initial_cleanup(grid_time_start, days, xmltv_file)

        # Download and parse guide data
        with OptimizedDownloader(base_delay=0.8, min_delay=0.4) as downloader:
            guide_parser = GuideParser(cache_manager, downloader, tvh_client)

            # Download guide blocks with configurable refresh
            guide_success = guide_parser.optimized_guide_download(
                grid_time_start=grid_time_start,
                day_hours=day_hours,
                lineupcode=config.get('lineupcode', 'lineupId'),
                country=country,
                device=config.get('device', '-'),
                zipcode=config.get('zipcode'),
                refresh_hours=refresh_hours  # NEW: Use configurable refresh hours
            )

            if not guide_success:
                logging.warning('Guide download had issues, but continuing with available data')

            # Clean show cache now that we have parsed episodes
            active_series = guide_parser.get_active_series_list()
            cache_manager.perform_show_cleanup(active_series)

            # Download extended details if needed
            if config_manager.needs_extended_download():
                extended_success = guide_parser.parse_extended_details()
                if not extended_success:
                    logging.warning('Extended details download had issues, using basic descriptions')

            # Generate XMLTV
            xmltv_generator = XmltvGenerator(cache_manager)
            xmltv_success = xmltv_generator.generate_xmltv(
                schedule=guide_parser.schedule,
                config=config,
                xmltv_file=xmltv_file
            )

            if not xmltv_success:
                logging.error('XMLTV generation failed')
                return 1

            # Final cleanup
            final_active_series = guide_parser.get_active_series_list()
            if final_active_series:
                cache_manager.clean_show_cache(final_active_series)
                logging.info('Final show cache verification: keeping %d active series',
                           len(final_active_series))

            # Final statistics
            time_run = round(time.time() - python_start_time, 2)
            logging.info('gracenote2epg completed in %s seconds', time_run)
            logging.info('%d Stations and %d Episodes written to xmltv.xml file',
                        xmltv_generator.station_count, xmltv_generator.episode_count)

            # Downloader statistics
            final_stats = downloader.get_stats()
            logging.info('Final download statistics:')
            logging.info('  Total requests: %d', final_stats['total_requests'])
            logging.info('  WAF blocks encountered: %d', final_stats['waf_blocks'])
            logging.info('  Final delay: %.2fs', final_stats['current_delay'])

            # Output XMLTV to stdout ONLY if not redirected to file
            # XMLTV standard: XML goes to stdout, logs go to stderr or file
            if args.output is None:
                # Pas de --output spécifié, afficher le XML sur stdout
                try:
                    with open(xmltv_file, 'r', encoding='utf-8') as f:
                        print(f.read(), end='')  # end='' pour éviter une ligne vide supplémentaire
                except Exception as e:
                    logging.error('Could not output XMLTV to stdout: %s', str(e))
                    return 1
            else:
                # --output spécifié, le XML est dans le fichier
                logging.info('XMLTV output written to: %s', args.output)

        logging.info('Script completed successfully')
        logging.info('gracenote2epg session ended successfully')
        logging.info('=' * 60)
        return 0

    except KeyboardInterrupt:
        logging.info('Interrupted by user')
        return 1
    except Exception as e:
        logging.exception('Critical error: %s', str(e))
        logging.info('gracenote2epg session ended with error')
        logging.info('=' * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
