#!/usr/bin/env python3
"""
gracenote2epg - North America TV Guide Grabber

Simplified version using unified parallel download architecture.
Single download method that adapts from sequential (1 worker) to parallel (N workers).
"""

import logging
import sys
import time
from pathlib import Path

# Import the unified download system
from .args import ArgumentParser
from .config import ConfigManager
from .downloader import create_download_system, get_performance_config, OptimizedDownloader
from .parser.guide import GuideParser  # Unified parser
from .tvheadend import TvheadendClient
from .utils import CacheManager
from .xmltv import XmltvGenerator
from .logrotate import LogRotationManager

# Package version
from . import __version__


def setup_logging(logging_config: dict, log_file: Path, retention_config: dict):
    """Setup logging configuration with unified retention policy"""
    # Create log directory
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Determine file logging level based on mode
    if logging_config["level"] == "warning":
        file_level = logging.WARNING
    elif logging_config["level"] == "debug":
        file_level = logging.DEBUG
    else:  # default
        file_level = logging.INFO

    # Create rotating file handler using unified retention config
    file_handler = LogRotationManager.create_rotating_handler(log_file, retention_config)
    file_handler.setLevel(file_level)

    # Set file formatter
    file_formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y/%m/%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(file_level)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)

    # Console logging only if --console is specified (and not --quiet)
    if logging_config["console"] and not logging_config["quiet"]:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(file_level)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return file_handler


def get_parallel_config(args) -> dict:
    """Get parallel download configuration from arguments and environment"""
    import os

    # Get base configuration from arguments
    base_config = {
        'enabled': getattr(args, 'parallel_enabled', True),
        'max_workers': getattr(args, 'workers', None),
        'adaptive': getattr(args, 'adaptive_enabled', True),
        'rate_limit': getattr(args, 'rate_limit', None),
    }

    # Override with environment variables if set
    if os.environ.get('GRACENOTE_PARALLEL'):
        base_config['enabled'] = os.environ.get('GRACENOTE_PARALLEL', 'true').lower() == 'true'
    
    if os.environ.get('GRACENOTE_MAX_WORKERS'):
        base_config['max_workers'] = int(os.environ.get('GRACENOTE_MAX_WORKERS', '4'))
    
    if os.environ.get('GRACENOTE_ADAPTIVE'):
        base_config['adaptive'] = os.environ.get('GRACENOTE_ADAPTIVE', 'true').lower() == 'true'

    # Get optimized performance config if max_workers not set
    if base_config['max_workers'] is None:
        perf_config = get_performance_config()
        base_config.update(perf_config)
    
    # Force sequential mode if disabled
    if not base_config['enabled']:
        base_config['max_workers'] = 1
        base_config['adaptive'] = False
        base_config['enable_monitoring'] = False

    # Validate max_workers
    if base_config['max_workers'] < 1:
        base_config['max_workers'] = 1
    elif base_config['max_workers'] > 10:
        base_config['max_workers'] = 10
        logging.warning("Max workers limited to 10 to avoid server overload")

    return base_config


def main():
    """Main application entry point with unified download architecture"""
    python_start_time = time.time()

    try:
        # Parse command line arguments
        arg_parser = ArgumentParser()
        args = arg_parser.parse_args()

        # Get system defaults
        defaults = arg_parser.get_system_defaults()

        # Override defaults with command line arguments
        config_file = args.config_file or defaults["config_file"]
        xmltv_file = args.output or defaults["xmltv_file"]
        log_file = defaults["log_file"]

        # Ensure directories exist
        arg_parser.create_directories_with_proper_permissions()

        # Load and validate configuration
        config_manager = ConfigManager(config_file)
        config = config_manager.load_config(
            location_code=getattr(args, "location_code", None),
            location_source=getattr(args, "location_source", "explicit"),
            location_extracted_from=getattr(args, "original_lineupid", None),
            days=args.days,
            langdetect=args.langdetect,
            refresh_hours=getattr(args, "refresh_hours", None),
            lineupid=getattr(args, "original_lineupid", None),
        )

        # Get unified retention configuration
        retention_config = config_manager.get_retention_config()

        # Setup logging
        logging_config = arg_parser.get_logging_config(args)
        file_handler = setup_logging(logging_config, log_file, retention_config)

        # Check for log rotation
        if retention_config.get("enabled", False) and hasattr(file_handler, "_check_startup_rotation"):
            try:
                logging.info("Checking for startup log rotation...")
                file_handler._check_startup_rotation()
                logging.info("Startup rotation check completed")
            except Exception as e:
                logging.warning("Error during startup rotation check: %s", str(e))

        # Start session logging
        logging.info("=" * 60)
        logging.info("gracenote2epg session started - Version %s", __version__)

        # Get parallel download configuration
        parallel_config = get_parallel_config(args)

        # Log performance configuration
        logging.info("Performance Configuration:")
        if parallel_config['max_workers'] == 1:
            logging.info("  Mode: SEQUENTIAL (1 worker)")
            if parallel_config.get('enabled', True):
                logging.info("  Note: Using unified architecture in sequential mode")
        else:
            logging.info("  Mode: PARALLEL (%d workers)", parallel_config['max_workers'])
            logging.info("  Adaptive concurrency: %s", 
                        "enabled" if parallel_config.get('adaptive', True) else "disabled")

        if parallel_config.get('rate_limit'):
            logging.info("  Rate limiting: %.1f requests/second", parallel_config['rate_limit'])

        # Performance tips
        if parallel_config['max_workers'] == 1:
            logging.info("  TIP: Use --workers N for parallel downloads (faster)")
        elif parallel_config['max_workers'] > 6:
            logging.info("  NOTE: High worker count may trigger rate limiting")

        if logging_config["level"] == "debug":
            logging.info("Debug logging enabled - all debug information will be logged")
        if logging_config["console"]:
            logging.info("Console logging enabled - logs also displayed on stderr")

        # Log configuration summary
        logging.info("Configuration loaded from: %s", config_file)
        config_manager.log_config_summary()

        # Initialize components
        cache_manager = CacheManager(defaults["cache_dir"])

        # Setup TVheadend client if enabled
        tvh_client = None
        if config.get("tvhoff", False):
            tvh_client = TvheadendClient(
                url=config.get("tvhurl", "127.0.0.1"),
                port=config.get("tvhport", "9981"),
                username=config.get("usern") or None,
                password=config.get("passw") or None,
            )

            # Fetch channels if TVheadend matching is enabled
            if config.get("tvhmatch", False):
                tvh_client.fetch_channels()
                tvh_client.log_filtering_summary(
                    explicit_station_list=config_manager.get_station_list(),
                    use_tvh_matching=config.get("tvhmatch", False),
                )

        # Calculate guide parameters
        days = int(config.get("days", 1))
        offset = float(getattr(args, "offset", 0) or 0)
        day_hours = days * 8  # 8 three-hour blocks per day

        # Get refresh hours from configuration/command line
        refresh_hours = config_manager.get_refresh_hours()

        # Calculate start time
        from datetime import datetime
        now = datetime.now().replace(microsecond=0, second=0, minute=0)
        grid_time_start = int(time.mktime(now.timetuple())) + int(offset * 86400)

        # Log guide parameters
        logging.info("TV Guide duration: %s days", days)
        if offset > 1:
            logging.info("TV Guide Start: %i [offset: %i days]", grid_time_start, int(offset))
        elif offset == 1:
            logging.info("TV Guide Start: %i [offset: %i day]", grid_time_start, int(offset))
        else:
            logging.info("TV Guide Start: %i", grid_time_start)

        logging.info("Caching directory: %s", defaults["cache_dir"])

        # Log cache refresh configuration
        if refresh_hours == 0:
            logging.info("Cache refresh: disabled (--norefresh or refresh=0)")
        else:
            logging.info(
                "Cache refresh: %d hours (first %d hours will be re-downloaded)",
                refresh_hours,
                refresh_hours,
            )

        # Perform initial cache cleanup
        xmltv_retention_days = retention_config.get("xmltv_retention_days", 7)
        cache_manager.perform_initial_cleanup(
            grid_time_start, days, xmltv_file, xmltv_retention_days
        )

        # Create unified download system
        base_downloader, parallel_manager, monitor = create_download_system(
            max_workers=parallel_config['max_workers'],
            enable_monitoring=parallel_config.get('enable_monitoring', False),
            enable_adaptive=parallel_config.get('adaptive', True),
            base_delay=parallel_config.get('base_delay', 0.8),
            min_delay=parallel_config.get('min_delay', 0.4)
        )

        # Start monitoring if enabled
        if monitor:
            monitor.start()

        try:
            # Create unified guide parser
            guide_parser = GuideParser(
                cache_manager=cache_manager,
                base_downloader=base_downloader,
                tvh_client=tvh_client,
                max_workers=parallel_config['max_workers'],
                enable_adaptive=parallel_config.get('adaptive', True)
            )

            # Track performance metrics
            download_start = time.time()

            # Download and parse guide data
            guide_success = guide_parser.download_and_parse_guide(
                grid_time_start=grid_time_start,
                day_hours=day_hours,
                config_manager=config_manager,
                refresh_hours=refresh_hours,
            )

            guide_download_time = time.time() - download_start

            if not guide_success:
                logging.warning("Guide download had issues, but continuing with available data")

            # Clean show cache now that we have parsed episodes
            active_series = guide_parser.get_active_series_list()
            cache_manager.perform_show_cleanup(active_series)

            # Download extended details if needed
            extended_download_time = 0
            if config_manager.needs_extended_download():
                extended_start = time.time()
                extended_success = guide_parser.download_and_parse_extended_details()
                extended_download_time = time.time() - extended_start

                if not extended_success:
                    logging.warning(
                        "Extended details download had issues, using basic descriptions"
                    )

            # Generate XMLTV
            xmltv_start = time.time()
            xmltv_generator = XmltvGenerator(cache_manager)
            xmltv_success = xmltv_generator.generate_xmltv(
                schedule=guide_parser.schedule, config=config, xmltv_file=xmltv_file
            )
            xmltv_generation_time = time.time() - xmltv_start

            if not xmltv_success:
                logging.error("XMLTV generation failed")
                return 1

            # Final cleanup
            final_active_series = guide_parser.get_active_series_list()
            if final_active_series:
                cache_manager.clean_show_cache(final_active_series)
                logging.info(
                    "Final show cache verification: keeping %d active series",
                    len(final_active_series),
                )

            # Performance statistics
            total_time = time.time() - python_start_time

            logging.info("=" * 60)
            logging.info("PERFORMANCE SUMMARY:")
            logging.info("  Total execution time: %.2f seconds", total_time)
            logging.info("  Guide download: %.2f seconds (%.1f%%)",
                        guide_download_time,
                        (guide_download_time / total_time * 100))

            if extended_download_time > 0:
                logging.info("  Extended details: %.2f seconds (%.1f%%)",
                            extended_download_time,
                            (extended_download_time / total_time * 100))

            logging.info("  XMLTV generation: %.2f seconds (%.1f%%)",
                        xmltv_generation_time,
                        (xmltv_generation_time / total_time * 100))

            # Performance comparison and statistics
            stats = guide_parser.get_statistics()
            
            logging.info("=" * 60)
            logging.info("NETWORK STATISTICS:")
            
            mode_description = "sequential" if parallel_config['max_workers'] == 1 else "parallel"
            logging.info("  Download mode: %s (%d workers)", 
                        mode_description, parallel_config['max_workers'])
            
            logging.info("  Total requests: %d", stats.get('total_requests', 0))
            logging.info("  Successful downloads: %d", stats.get('successful', 0))
            logging.info("  Failed downloads: %d", stats.get('failed', 0))
            logging.info("  From cache: %d", stats.get('cached', 0))

            bytes_downloaded = stats.get('bytes_downloaded', 0)
            if bytes_downloaded > 0:
                logging.info("  Data downloaded: %.2f MB", bytes_downloaded / (1024 * 1024))

            # Performance metrics
            success_rate = stats.get('success_rate', 0)
            if success_rate > 0:
                logging.info("  Success rate: %.1f%%", success_rate)

            requests_per_second = stats.get('requests_per_second', 0)
            if requests_per_second > 0:
                logging.info("  Download rate: %.1f requests/second", requests_per_second)

            throughput = stats.get('throughput_mbps', 0)
            if throughput > 0:
                logging.info("  Throughput: %.2f MB/s", throughput)

            # Performance comparison for parallel mode
            if parallel_config['max_workers'] > 1:
                # Estimate sequential time (rough approximation)
                estimated_sequential = total_time * (parallel_config['max_workers'] * 0.6)
                speedup = estimated_sequential / total_time

                if speedup > 1.2:
                    logging.info("  Estimated speedup: %.1fx faster than sequential", speedup)

            # WAF blocks
            total_waf = stats.get('waf_blocks', 0)
            if total_waf > 0:
                logging.info("  WAF blocks encountered: %d", total_waf)

            logging.info("=" * 60)

            logging.info(
                "%d Stations and %d Episodes written to xmltv.xml file",
                xmltv_generator.station_count,
                xmltv_generator.episode_count,
            )

            # Clean up download system
            guide_parser.cleanup()

        finally:
            # Stop monitoring if enabled
            if monitor:
                monitor.stop()

            # Close download system
            if base_downloader:
                base_downloader.close()

        # Output XMLTV to stdout if not redirected to file
        if args.output is None:
            try:
                with open(xmltv_file, "r", encoding="utf-8") as f:
                    print(f.read(), end="")
            except Exception as e:
                logging.error("Could not output XMLTV to stdout: %s", str(e))
                return 1
        else:
            logging.info("XMLTV output written to: %s", args.output)

        logging.info("Script completed successfully")
        logging.info("gracenote2epg session ended successfully")
        logging.info("=" * 60)
        return 0

    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        return 1
    except Exception as e:
        logging.exception("Critical error: %s", str(e))
        logging.info("gracenote2epg session ended with error")
        logging.info("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
