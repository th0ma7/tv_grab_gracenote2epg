"""
gracenote2epg.parser.guide - Unified guide parser with strategy-based downloads

Clean implementation using UnifiedDownloadManager with proper worker strategies.
Eliminates duplicate managers and provides consistent worker allocation.
"""

import calendar
import json
import logging
import re
import time
import urllib.parse
from typing import Dict, List, Optional, Any

from ..downloader.base import OptimizedDownloader
from ..downloader.parallel import UnifiedDownloadManager, create_adaptive_strategy
from ..downloader.monitoring import EventDrivenMonitor, EventType
from ..tvheadend import TvheadendClient
from ..utils import CacheManager, TimeUtils


class UnifiedGuideParser:
    """
    Unified TV guide parser with strategy-based downloads and clean architecture

    Key improvements:
    - Single UnifiedDownloadManager for both guide and series downloads
    - Strategy-based worker allocation (different strategies for different task types)
    - Consistent monitoring and statistics across all operations
    - Clean API without legacy compatibility issues
    """

    def __init__(
        self,
        cache_manager: CacheManager,
        base_downloader: OptimizedDownloader,
        tvh_client: Optional[TvheadendClient] = None,
        max_workers: int = 4,
        worker_strategy: str = "balanced",
        enable_adaptive: bool = True,
        enable_monitoring: bool = False,
        monitoring_config: Optional[Dict] = None,
        download_manager: Optional[UnifiedDownloadManager] = None,
        monitor: Optional[EventDrivenMonitor] = None
    ):
        """
        Initialize unified guide parser with strategy-based architecture

        Args:
            cache_manager: Cache manager instance
            base_downloader: Base downloader for fallback operations
            tvh_client: Optional TVheadend client
            max_workers: Maximum parallel workers
            worker_strategy: Worker allocation strategy ("conservative", "balanced", "aggressive")
            enable_adaptive: Enable adaptive worker adjustment
            enable_monitoring: Enable real-time monitoring
            monitoring_config: Configuration for monitoring
            download_manager: Pre-created download manager (optional)
            monitor: Pre-created monitor (optional)
        """
        self.cache_manager = cache_manager
        self.base_downloader = base_downloader
        self.tvh_client = tvh_client
        self.schedule: Dict = {}

        # Store configuration
        self.max_workers = max_workers
        self.worker_strategy = worker_strategy
        self.enable_adaptive = enable_adaptive
        self.enable_monitoring = enable_monitoring
        self.monitoring_config = monitoring_config or {}

        # Create or use provided monitor
        if monitor:
            self.monitor = monitor
        elif enable_monitoring:
            config = monitoring_config or {}
            self.monitor = EventDrivenMonitor(
                enable_console=config.get('enable_console', True),
                enable_web_api=config.get('enable_web_api', False),
                web_port=config.get('web_port', 9989),
                metrics_file=config.get('metrics_file', None)
            )
        else:
            self.monitor = None

        # Create or use provided download manager
        if download_manager:
            self.download_manager = download_manager
        else:
            self.download_manager = UnifiedDownloadManager(
                max_workers=max_workers,
                max_retries=3,
                base_delay=0.5,
                enable_rate_limiting=True,
                enable_adaptive=enable_adaptive,
                worker_strategy=worker_strategy,
                monitor=self.monitor
            )

        # Connect base downloader to monitoring if available
        if self.monitor:
            self.base_downloader.set_monitor_callback(self._base_downloader_event_callback)

        # Log initialization with strategy information
        mode = "sequential" if max_workers == 1 else "parallel"
        adaptive_str = f" (adaptive {worker_strategy})" if enable_adaptive and max_workers > 1 else ""
        monitoring_str = " with real-time monitoring" if enable_monitoring else ""

        logging.info(
            "Unified guide parser initialized: %s mode%s%s",
            mode, adaptive_str, monitoring_str
        )

        # Log strategy details
        if enable_adaptive and max_workers > 1:
            strategy_info = self.download_manager.adaptive_strategy.get_strategy_info()
            logging.info("Worker strategy details:")
            for task_type, config in strategy_info['strategies'].items():
                logging.info("  %s: %d workers (max: %d), %.1f req/s",
                           task_type, config['current_workers'], config['max_workers'], config['rate_limit'])

    def _base_downloader_event_callback(self, event_type: str, worker_id: int, **data):
        """Callback to receive events from base downloader"""
        if not self.monitor:
            return

        if event_type == 'waf_detected':
            self.monitor.emit_event(EventType.WAF_DETECTED, worker_id, **data)
        elif event_type == 'rate_limit':
            self.monitor.emit_event(EventType.RATE_LIMIT_HIT, worker_id, **data)
        elif event_type == 'request_success':
            self.monitor.emit_event(EventType.TASK_COMPLETED, worker_id, **data)
        elif event_type == 'request_failed':
            self.monitor.emit_event(EventType.TASK_FAILED, worker_id, **data)

    def start_monitoring(self):
        """Start real-time monitoring if configured"""
        if self.monitor:
            self.monitor.start()
            logging.info("Real-time monitoring started")

    def stop_monitoring(self):
        """Stop real-time monitoring if running"""
        if self.monitor:
            self.monitor.stop()
            logging.info("Real-time monitoring stopped")

    def download_and_parse_guide(
        self,
        grid_time_start: float,
        day_hours: int,
        config_manager,
        refresh_hours: int = 48
    ) -> bool:
        """
        Download and parse guide data using unified strategy-based approach

        Args:
            grid_time_start: Start time for guide data
            day_hours: Number of 3-hour blocks to download
            config_manager: Configuration manager instance
            refresh_hours: Hours to refresh from cache (0 = no refresh)

        Returns:
            Success status
        """
        logging.info("Starting guide download with unified strategy-based architecture")

        # Get lineup configuration
        lineup_config = config_manager.get_lineup_config()

        # Get current strategy information
        strategy_info = self.download_manager.adaptive_strategy.get_strategy_info()
        guide_strategy = strategy_info['strategies']['guide_block']

        logging.info("Guide download configuration:")
        logging.info("  Strategy: %s", strategy_info['name'])
        logging.info("  Guide workers: %d/%d", guide_strategy['current_workers'], guide_strategy['max_workers'])
        logging.info("  Rate limit: %.1f req/s", guide_strategy['rate_limit'])
        logging.info("  Adaptive: %s", "enabled" if self.enable_adaptive else "disabled")

        if refresh_hours == 0:
            logging.info("  Cache refresh: DISABLED (--norefresh)")
        else:
            logging.info("  Refresh window: first %d hours will be re-downloaded", refresh_hours)

        logging.info("  Guide duration: %d blocks (%d hours)", day_hours, day_hours * 3)

        # Prepare download tasks and count what will actually be downloaded
        tasks = []
        download_tasks_count = 0
        cached_tasks = 0
        grid_time = grid_time_start

        for count in range(day_hours):
            # Generate standardized filename
            standard_block_time = TimeUtils.get_standard_block_time(grid_time)
            filename = standard_block_time.strftime("%Y%m%d%H") + ".json.gz"

            # Check if this will be downloaded or cached
            cached_content = self.cache_manager.load_guide_block(filename)

            # Determine if refresh is needed
            if refresh_hours == 0:
                # --norefresh: never refresh, always use cache if available
                needs_refresh = False
            else:
                # Normal refresh logic: refresh blocks within refresh_hours window
                time_from_now = grid_time - time.time()
                needs_refresh = time_from_now < (refresh_hours * 3600)

            if cached_content and not needs_refresh:
                cached_tasks += 1
            else:
                download_tasks_count += 1

            # Build download URL
            url = self._build_gracenote_url(lineup_config, grid_time)

            tasks.append({
                'grid_time': grid_time,
                'filename': filename,
                'url': url,
                'count': count
            })

            grid_time = grid_time + 10800  # Next 3-hour block

        # Create downloading progress tracker if monitoring enabled
        download_progress_tracker = None
        if self.monitor:
            if download_tasks_count > 0:
                # There are actual downloads to perform
                download_progress_tracker = self.monitor.create_progress_tracker("Downloading Guide", download_tasks_count)
                # Store metadata for display
                with self.monitor.stats_lock:
                    if download_progress_tracker.name in self.monitor.progress_bars:
                        self.monitor.progress_bars[download_progress_tracker.name]['cached'] = cached_tasks
                        self.monitor.progress_bars[download_progress_tracker.name]['total_blocks'] = len(tasks)
                        self.monitor.progress_bars[download_progress_tracker.name]['has_downloads'] = True
            else:
                # Everything is cached - create tracker just for display
                download_progress_tracker = self.monitor.create_progress_tracker("Downloading Guide", len(tasks))
                download_progress_tracker.update(len(tasks))  # Set to complete immediately
                # Store metadata for display
                with self.monitor.stats_lock:
                    if download_progress_tracker.name in self.monitor.progress_bars:
                        self.monitor.progress_bars[download_progress_tracker.name]['cached'] = cached_tasks
                        self.monitor.progress_bars[download_progress_tracker.name]['total_blocks'] = len(tasks)
                        self.monitor.progress_bars[download_progress_tracker.name]['has_downloads'] = False
                        self.monitor.progress_bars[download_progress_tracker.name]['cache_only'] = True

        # Log download plan
        if download_tasks_count > 0:
            logging.info("Starting guide block download: %d blocks, %d workers",
                        download_tasks_count, guide_strategy['current_workers'])
            if cached_tasks > 0:
                logging.info("  Will download: %d new blocks, use %d cached blocks",
                            download_tasks_count, cached_tasks)
        else:
            logging.info("All %d blocks found in cache, no downloads needed", cached_tasks)

        # Progress callback for guide downloads
        downloaded_so_far = 0
        def download_progress_callback(completed, total):
            nonlocal downloaded_so_far

            if download_progress_tracker and download_tasks_count > 0:
                # Track only actual downloads, not cache hits
                if completed > downloaded_so_far:
                    downloaded_so_far = completed
                    download_progress_tracker.update(completed)

            if download_tasks_count == 0:
                return

            # Dynamic progress reporting
            interval = max(1, min(download_tasks_count // 20, 50))
            if completed % interval == 0 or completed == download_tasks_count:
                percent = (completed / download_tasks_count * 100) if download_tasks_count > 0 else 100
                formatted_percent = f"{percent:.0f}%"
                logging.info("Guide download progress: %d/%d blocks (%s)",
                           completed, download_tasks_count, formatted_percent)

        # Download blocks using unified manager
        download_start = time.time()
        results = self.download_manager.download_guide_blocks(
            tasks=tasks,
            cache_manager=self.cache_manager,
            config_manager=config_manager,
            refresh_hours=refresh_hours,
            progress_callback=download_progress_callback
        )
        download_time = time.time() - download_start

        # Create parsing progress tracker if monitoring enabled
        parsing_tracker = None
        if self.monitor:
            parsing_tracker = self.monitor.create_progress_tracker("Parsing Guide", len(tasks))

        # Parse downloaded/cached blocks
        parse_start = time.time()
        parse_success = 0
        parse_failed = 0

        for task_index, task in enumerate(tasks):
            filename = task['filename']
            count = task['count']

            # Load content (from results or cache)
            if filename in results:
                content = results[filename]
            else:
                content = self.cache_manager.load_guide_block(filename)

            if content:
                try:
                    logging.debug("Parsing %s", filename)

                    if count == 0:
                        self.parse_stations(content)
                    self.parse_episodes(content)

                    parse_success += 1

                    if parsing_tracker:
                        parsing_tracker.increment()

                except Exception as e:
                    logging.warning("Parse error for %s: %s", filename, str(e))
                    parse_failed += 1

                    if parsing_tracker:
                        parsing_tracker.increment()
            else:
                logging.warning("No content available for %s", filename)
                parse_failed += 1

                if parsing_tracker:
                    parsing_tracker.increment()

        parse_time = time.time() - parse_start

        # Get unified statistics
        stats = self.download_manager.get_detailed_statistics()

        total_blocks = day_hours
        success_rate = (parse_success / total_blocks * 100) if total_blocks > 0 else 0

        logging.info("Guide download and parsing completed:")
        logging.info("  Total time: %.1f seconds (download: %.1f, parsing: %.1f)",
                    download_time + parse_time, download_time, parse_time)
        logging.info("  Blocks processed: %d total (%d parsed, %d failed)",
                    total_blocks, parse_success, parse_failed)
        logging.info("  Network stats: %d new, %d cached, %d failed",
                    stats['successful'], stats['cached'], stats['failed'])

        if stats['bytes_downloaded'] > 0:
            logging.info("  Data downloaded: %.1f MB at %.2f MB/s",
                        stats['bytes_downloaded'] / (1024 * 1024),
                        stats.get('throughput_mbps', 0))

        logging.info("  Success rate: %.1f%%", success_rate)

        # Log strategy performance if adaptive is enabled
        if self.enable_adaptive:
            strategy_stats = stats.get('adaptive_strategy', {})
            if strategy_stats.get('status') == 'active':
                guide_summary = strategy_stats.get('task_summaries', {}).get('guide_block', {})
                if guide_summary.get('samples', 0) > 0:
                    logging.info("  Adaptive performance: %.1f%% success, %.2fs avg response, %s trend",
                               guide_summary['avg_success_rate'] * 100,
                               guide_summary['avg_response_time'],
                               guide_summary['performance_trend'])

        return success_rate >= 80

    def download_and_parse_extended_details(self) -> bool:
        """
        Download and parse extended program details using unified strategy-based approach

        Returns:
            Success status based on overall completion
        """
        logging.info("Starting extended details download with strategy-based architecture")

        # Collect unique series IDs
        unique_series = set()
        series_usage = {}

        for station in self.schedule:
            sdict = self.schedule[station]
            for episode in sdict:
                if not episode.startswith("ch"):
                    edict = sdict[episode]
                    series_id = edict.get("epseries")

                    if series_id:
                        unique_series.add(series_id)
                        series_usage[series_id] = series_usage.get(series_id, 0) + 1

        series_list = list(unique_series)
        logging.info("Extended details: %d unique series found", len(series_list))

        if not series_list:
            logging.info("No series found for extended details download")
            return True

        # Get current strategy information
        strategy_info = self.download_manager.adaptive_strategy.get_strategy_info()
        series_strategy = strategy_info['strategies']['series_details']

        logging.info("Series download configuration:")
        logging.info("  Strategy: %s", strategy_info['name'])
        logging.info("  Series workers: %d/%d", series_strategy['current_workers'], series_strategy['max_workers'])
        logging.info("  Rate limit: %.1f req/s", series_strategy['rate_limit'])
        logging.info("  Conservative mode: %s", series_strategy['conservative'])

        # Count what will actually be downloaded vs cached
        download_count = 0
        cached_count = 0

        for series_id in series_list:
            cached_details = self.cache_manager.load_series_details(series_id)
            if cached_details and isinstance(cached_details, dict) and len(cached_details) > 0:
                # Additional validation - check for essential keys
                if any(key in cached_details for key in ['seriesDescription', 'seriesGenres', 'overviewTab', 'upcomingEpisodeTab']):
                    cached_count += 1
                else:
                    download_count += 1
            else:
                download_count += 1

        # Create downloading progress tracker if monitoring enabled
        download_details_tracker = None
        if self.monitor:
            if download_count > 0:
                # There are actual downloads to perform
                download_details_tracker = self.monitor.create_progress_tracker("Downloading Details", download_count)
                # Store metadata for display
                with self.monitor.stats_lock:
                    if download_details_tracker.name in self.monitor.progress_bars:
                        self.monitor.progress_bars[download_details_tracker.name]['cached'] = cached_count
                        self.monitor.progress_bars[download_details_tracker.name]['total_series'] = len(series_list)
                        self.monitor.progress_bars[download_details_tracker.name]['has_downloads'] = True
            else:
                # Everything is cached - create tracker just for display
                download_details_tracker = self.monitor.create_progress_tracker("Downloading Details", cached_count)
                download_details_tracker.update(cached_count)  # Set to complete immediately
                # Store metadata for display
                with self.monitor.stats_lock:
                    if download_details_tracker.name in self.monitor.progress_bars:
                        self.monitor.progress_bars[download_details_tracker.name]['cached'] = cached_count
                        self.monitor.progress_bars[download_details_tracker.name]['total_series'] = len(series_list)
                        self.monitor.progress_bars[download_details_tracker.name]['has_downloads'] = False
                        self.monitor.progress_bars[download_details_tracker.name]['cache_only'] = True

        # Log download plan
        if download_count > 0:
            logging.info("Starting series details download: %d series, %d workers",
                        download_count, series_strategy['current_workers'])
            if cached_count > 0:
                logging.info("  Will download: %d new series, use %d cached series",
                            download_count, cached_count)
        else:
            logging.info("All %d series found in cache, no downloads needed", cached_count)

        # Progress callback for series downloads
        downloaded_so_far = 0
        def series_progress_callback(completed, total):
            nonlocal downloaded_so_far

            if download_details_tracker and download_count > 0:
                # Track only actual downloads
                if completed > downloaded_so_far:
                    downloaded_so_far = completed
                    download_details_tracker.update(completed)

            if download_count == 0:
                return

            # Dynamic progress reporting
            interval = max(1, min(download_count // 20, 25))
            if completed % interval == 0 or completed == download_count:
                percent = (completed / download_count * 100) if download_count > 0 else 100
                formatted_percent = f"{percent:.0f}%"
                logging.info("Series details progress: %d/%d (%s)",
                           completed, download_count, formatted_percent)

        # Download series details using unified manager
        download_start = time.time()
        series_details = self.download_manager.download_series_details(
            series_list=series_list,
            cache_manager=self.cache_manager,
            progress_callback=series_progress_callback
        )
        download_time = time.time() - download_start

        # Create processing progress tracker if monitoring enabled
        processing_tracker = None
        if self.monitor:
            total_episodes = sum(
                1 for station in self.schedule
                for episode in self.schedule[station]
                if not episode.startswith("ch") and self.schedule[station][episode].get("epseries")
            )
            processing_tracker = self.monitor.create_progress_tracker("Processing Details", total_episodes)

        # Process downloaded details with enhanced monitoring
        process_start = time.time()
        processed_count = 0
        failed_count = 0

        for station in self.schedule:
            sdict = self.schedule[station]
            for episode in sdict:
                if not episode.startswith("ch"):
                    edict = sdict[episode]
                    series_id = edict.get("epseries")

                    if series_id and series_id in series_details:
                        try:
                            self._process_series_details(
                                edict, series_details[series_id], series_id
                            )
                            processed_count += 1

                            if processing_tracker:
                                processing_tracker.increment()

                        except Exception as e:
                            logging.warning("Error processing series %s: %s", series_id, str(e))
                            failed_count += 1

                            if processing_tracker:
                                processing_tracker.increment()

        process_time = time.time() - process_start

        # Get unified statistics
        stats = self.download_manager.get_detailed_statistics()

        # Enhanced summary logging
        total_time = download_time + process_time
        logging.info("Extended details completed:")
        logging.info("  Total time: %.1f seconds (download: %.1f, processing: %.1f)",
                    total_time, download_time, process_time)
        logging.info("  Unique series: %d", len(unique_series))
        logging.info("  Network stats: %d downloaded, %d cached, %d failed",
                    stats['successful'], stats['cached'], stats['failed'])
        logging.info("  Episodes processed: %d", processed_count)

        if stats['bytes_downloaded'] > 0:
            logging.info("  Data downloaded: %.1f MB at %.2f MB/s",
                        stats['bytes_downloaded'] / (1024 * 1024),
                        stats.get('throughput_mbps', 0))

        # Log adaptive strategy performance
        if self.enable_adaptive:
            strategy_stats = stats.get('adaptive_strategy', {})
            if strategy_stats.get('status') == 'active':
                series_summary = strategy_stats.get('task_summaries', {}).get('series_details', {})
                if series_summary.get('samples', 0) > 0:
                    logging.info("  Adaptive performance: %.1f%% success, %.2fs avg response, %s trend",
                               series_summary['avg_success_rate'] * 100,
                               series_summary['avg_response_time'],
                               series_summary['performance_trend'])

        # Log worker pool statistics for verification
        pool_stats = stats.get('active_pools', {})
        for task_type, pool_info in pool_stats.items():
            pool_detailed = pool_info.get('statistics', {})
            if pool_detailed.get('worker_count_consistent', True):
                logging.debug("%s pool: worker count consistent", task_type)
            else:
                logging.warning("%s pool: worker count mismatch - reported %d, actual %d",
                               task_type,
                               pool_detailed.get('reported_workers', 0),
                               pool_detailed.get('actual_executor_workers', 0))

        # Success detection logic
        total_completed = len(series_details)  # This includes both downloaded and cached
        total_requested = len(series_list)

        if total_requested == 0:
            return True

        completion_rate = (total_completed / total_requested) * 100
        success_threshold = 90.0
        is_successful = completion_rate >= success_threshold

        logging.info("  Completion rate: %.1f%% (%d/%d series have data)",
                    completion_rate, total_completed, total_requested)
        logging.info("  Success threshold: %.1f%% - Status: %s",
                    success_threshold, "SUCCESS" if is_successful else "ISSUES")

        return is_successful

    def _build_gracenote_url(self, lineup_config: Dict, grid_time: float) -> str:
        """Build Gracenote URL with lineup configuration"""
        base_url = "http://tvlistings.gracenote.com/api/grid"

        params = [
            ("aid", "orbebb"),
            ("TMSID", ""),
            ("AffiliateID", "lat"),
            ("lineupId", lineup_config.get("lineup_id", "")),
            ("timespan", "3"),
            ("headendId", lineup_config.get("headend_id", "lineupId")),
            ("country", lineup_config.get("country", "USA")),
            ("device", lineup_config.get("device_type", "-")),
            ("postalCode", lineup_config.get("postal_code", "")),
            ("time", str(int(grid_time))),
            ("isOverride", "true"),
            ("pref", "-"),
            ("userId", "-"),
        ]

        query_string = "&".join(
            [f"{key}={urllib.parse.quote(str(value))}" for key, value in params]
        )
        return f"{base_url}?{query_string}"

    def parse_stations(self, content: bytes):
        """Parse station information from guide data"""
        try:
            ch_guide = json.loads(content)

            for station in ch_guide.get("channels", []):
                station_id = station.get("channelId")

                if self._should_process_station(station):
                    self.schedule[station_id] = {}

                    call_sign = station.get("callSign")
                    affiliate_name = station.get("affiliateName")

                    self.schedule[station_id]["chfcc"] = call_sign
                    self.schedule[station_id]["chnam"] = affiliate_name

                    thumbnail = station.get("thumbnail", "")
                    if thumbnail:
                        self.schedule[station_id]["chicon"] = thumbnail.split("?")[0]
                    else:
                        self.schedule[station_id]["chicon"] = ""

                    if self.tvh_client:
                        matched_channel = self.tvh_client.get_matched_channel_number(
                            station, use_channel_matching=True
                        )
                        tvh_name = self.tvh_client.get_tvh_channel_name(matched_channel)
                    else:
                        matched_channel = station.get("channelNo", "")
                        tvh_name = None

                    self.schedule[station_id]["chnum"] = matched_channel
                    self.schedule[station_id]["chtvh"] = tvh_name

        except Exception as e:
            logging.exception("Exception in parse_stations: %s", str(e))

    def parse_episodes(self, content: bytes) -> str:
        """Parse episode information from guide data"""
        check_tba = "Safe"

        try:
            ch_guide = json.loads(content)

            for station in ch_guide.get("channels", []):
                station_id = station.get("channelId")

                if self._should_process_station(station) and station_id in self.schedule:
                    episodes = station.get("events", [])

                    for episode in episodes:
                        start_time_str = episode.get("startTime", "")
                        if start_time_str:
                            try:
                                ep_key = str(
                                    calendar.timegm(
                                        time.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ")
                                    )
                                )
                            except (ValueError, TypeError):
                                continue
                        else:
                            continue

                        self.schedule[station_id][ep_key] = {}
                        ep_data = self.schedule[station_id][ep_key]

                        program = episode.get("program", {})

                        short_desc = program.get("shortDesc") or ""
                        long_desc = program.get("longDesc") or ""

                        if short_desc is None:
                            short_desc = ""
                        if long_desc is None:
                            long_desc = ""

                        end_time_str = episode.get("endTime", "")
                        if end_time_str:
                            try:
                                ep_end = str(
                                    calendar.timegm(
                                        time.strptime(end_time_str, "%Y-%m-%dT%H:%M:%SZ")
                                    )
                                )
                            except (ValueError, TypeError):
                                ep_end = None
                        else:
                            ep_end = None

                        ep_data.update({
                            "epid": program.get("tmsId"),
                            "epstart": ep_key,
                            "epend": ep_end,
                            "eplength": episode.get("duration"),
                            "epshow": program.get("title"),
                            "eptitle": program.get("episodeTitle"),
                            "epdesc": long_desc if long_desc else short_desc,
                            "epyear": program.get("releaseYear"),
                            "eprating": episode.get("rating"),
                            "epflag": episode.get("flag", []),
                            "eptags": episode.get("tags", []),
                            "epsn": program.get("season"),
                            "epen": program.get("episode"),
                            "epthumb": (
                                episode.get("thumbnail", "").split("?")[0]
                                if episode.get("thumbnail")
                                else ""
                            ),
                            "epoad": None,
                            "epstar": None,
                            "epfilter": episode.get("filter", []),
                            "epgenres": None,
                            "epcredits": None,
                            "epseries": program.get("seriesId"),
                            "epimage": None,
                            "epfan": None,
                            "epseriesdesc": None,
                        })

                        if ep_data["epshow"] and "TBA" in ep_data["epshow"]:
                            check_tba = "Unsafe"
                        elif ep_data["eptitle"] and "TBA" in ep_data["eptitle"]:
                            check_tba = "Unsafe"

                else:
                    if station_id not in self.schedule:
                        logging.debug("Station %s filtered out or not found in schedule", station_id)

        except Exception as e:
            logging.exception("Exception in parse_episodes: %s", str(e))

        return check_tba

    def _should_process_station(self, station_data: Dict) -> bool:
        """Determine if a station should be processed based on filtering rules"""
        if self.tvh_client:
            return self.tvh_client.should_process_station(
                station_data,
                explicit_station_list=None,
                use_tvh_matching=True,
                use_channel_matching=True,
            )
        return True

    def get_active_series_list(self) -> List[str]:
        """Extract list of active series from current schedule"""
        active_series = set()
        for station in self.schedule:
            sdict = self.schedule[station]
            for episode in sdict:
                if not episode.startswith("ch"):
                    edict = sdict[episode]
                    series_id = edict.get("epseries")
                    if series_id:
                        active_series.add(series_id)
        return list(active_series)

    def _process_series_details(self, episode_data: Dict, series_details: Dict, series_id: str):
        """Process extended series details and update episode data"""
        try:
            series_desc = series_details.get("seriesDescription")
            if series_desc and str(series_desc).strip():
                episode_data["epseriesdesc"] = str(series_desc).strip()
                logging.debug(
                    "Found extended series description for %s: %s",
                    series_id,
                    series_desc[:50] + "..." if len(series_desc) > 50 else series_desc,
                )

            episode_data["epimage"] = series_details.get("seriesImage")
            episode_data["epfan"] = series_details.get("backgroundImage")

            ep_genres = series_details.get("seriesGenres")
            if series_id.startswith("MV"):
                overview_tab = series_details.get("overviewTab", {})
                if isinstance(overview_tab, dict):
                    episode_data["epcredits"] = overview_tab.get("cast")
                ep_genres = "Movie|" + ep_genres if ep_genres else "Movie"

            if ep_genres:
                episode_data["epgenres"] = ep_genres.split("|")

            ep_list = series_details.get("upcomingEpisodeTab", [])
            if not isinstance(ep_list, list):
                ep_list = []

            ep_id = episode_data.get("epid", "")
            for airing in ep_list:
                if not isinstance(airing, dict):
                    continue

                if ep_id.lower() == airing.get("tmsID", "").lower():
                    if not series_id.startswith("MV"):
                        try:
                            orig_date = airing.get("originalAirDate")
                            if orig_date and orig_date != "":
                                ep_oad = re.sub("Z", ":00Z", orig_date)
                                episode_data["epoad"] = str(
                                    calendar.timegm(time.strptime(ep_oad, "%Y-%m-%dT%H:%M:%SZ"))
                                )
                        except Exception:
                            pass

                        try:
                            tba_check = airing.get("episodeTitle", "")
                            if tba_check and "TBA" in tba_check:
                                logging.info("Found TBA listing in %s", series_id)
                        except Exception:
                            pass

        except Exception as e:
            logging.warning("Error processing series details for %s: %s", series_id, str(e))

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive download and processing statistics from unified manager"""
        # Get unified statistics from single manager
        unified_stats = self.download_manager.get_detailed_statistics()

        # Add parser-specific information
        unified_stats.update({
            'parser_info': {
                'stations_count': len(self.schedule),
                'episodes_count': sum(
                    len([ep for ep in station.keys() if not ep.startswith("ch")])
                    for station in self.schedule.values()
                ),
                'series_count': len(self.get_active_series_list())
            },
            'configuration': {
                'max_workers': self.max_workers,
                'worker_strategy': self.worker_strategy,
                'adaptive_enabled': self.enable_adaptive,
                'monitoring_enabled': self.enable_monitoring
            }
        })

        return unified_stats

    def save_monitoring_metrics(self, filename: str = None):
        """Save monitoring metrics to file if monitoring is enabled"""
        if self.monitor:
            if filename:
                from pathlib import Path
                self.monitor.metrics_file = Path(filename)
            self.monitor.save_metrics()
            logging.info("Monitoring metrics saved")

    def get_performance_recommendations(self) -> List[str]:
        """Get performance recommendations based on observed behavior"""
        recommendations = []

        if not self.enable_adaptive:
            recommendations.append("Enable adaptive mode for better performance")

        stats = self.get_statistics()

        # Check for rate limiting issues
        if stats.get('rate_limit_hits', 0) > 10:
            recommendations.append("Consider using 'conservative' strategy due to frequent rate limiting")

        # Check for worker efficiency
        active_pools = stats.get('active_pools', {})
        for task_type, pool_info in active_pools.items():
            pool_stats = pool_info.get('statistics', {})
            if not pool_stats.get('worker_count_consistent', True):
                recommendations.append(f"Worker count inconsistency detected in {task_type} pool - check logs")

        # Check for monitoring value
        if not self.enable_monitoring and self.max_workers > 2:
            recommendations.append("Enable monitoring for better visibility into parallel downloads")

        # Strategy recommendations
        strategy_stats = stats.get('adaptive_strategy', {})
        if strategy_stats.get('status') == 'active':
            for task_type, task_summary in strategy_stats.get('task_summaries', {}).items():
                if task_summary.get('avg_success_rate', 1.0) < 0.85:
                    recommendations.append(f"Poor {task_type} success rate - consider reducing workers or enabling conservative mode")

        return recommendations

    def cleanup(self):
        """Clean up resources and collect final statistics"""
        logging.info("Cleaning up unified guide parser resources")

        try:
            # Get final performance recommendations
            recommendations = self.get_performance_recommendations()
            if recommendations:
                logging.info("Performance recommendations:")
                for rec in recommendations[:3]:  # Show top 3
                    logging.info("  • %s", rec)

            # Clean up unified download manager
            if self.download_manager:
                self.download_manager.cleanup()

            # Clean up base downloader
            if self.base_downloader:
                self.base_downloader.close()

            # Stop monitoring
            self.stop_monitoring()

        except Exception as e:
            logging.warning("Error during cleanup: %s", str(e))


# Clean API alias
GuideParser = UnifiedGuideParser
