"""
gracenote2epg.parser.guide - Unified guide data parsing with improved progress reporting

Fixed version with better progress reporting and single manager architecture.
"""

import calendar
import json
import logging
import re
import time
import urllib.parse
from typing import Dict, List, Optional, Any

from ..downloader.base import OptimizedDownloader
from ..downloader.parallel import ParallelDownloadManager, AdaptiveParallelDownloader
from ..downloader.monitoring import EventDrivenMonitor, EventType
from ..tvheadend import TvheadendClient
from ..utils import CacheManager, TimeUtils


class UnifiedGuideParser:
    """
    Unified TV guide parser with improved progress reporting and single manager architecture
    """

    def __init__(
        self,
        cache_manager: CacheManager,
        base_downloader: OptimizedDownloader,
        tvh_client: Optional[TvheadendClient] = None,
        max_workers: int = 4,
        enable_adaptive: bool = True,
        enable_monitoring: bool = False,
        monitoring_config: Optional[Dict] = None,
        # Accept pre-created managers to avoid duplication
        guide_manager: Optional[ParallelDownloadManager] = None,
        series_manager: Optional[ParallelDownloadManager] = None,
        monitor: Optional[EventDrivenMonitor] = None
    ):
        """
        Initialize unified guide parser with single manager architecture

        Args:
            cache_manager: Cache manager instance
            base_downloader: Base downloader for fallback operations
            tvh_client: Optional TVheadend client
            max_workers: Maximum parallel workers (1 = sequential behavior)
            enable_adaptive: Enable adaptive worker adjustment
            enable_monitoring: Enable real-time monitoring
            monitoring_config: Configuration for monitoring (port, web API, etc.)
            guide_manager: Pre-created guide manager (prevents duplication)
            series_manager: Pre-created series manager (prevents duplication)
            monitor: Pre-created monitor (prevents duplication)
        """
        self.cache_manager = cache_manager
        self.base_downloader = base_downloader
        self.tvh_client = tvh_client
        self.schedule: Dict = {}

        # Store configuration
        self.max_workers = max_workers
        self.enable_monitoring = enable_monitoring
        self.monitoring_config = monitoring_config or {}

        # Use provided managers or create new ones (but don't log if provided)
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

        # Use provided managers or create new ones
        if guide_manager:
            self.guide_manager = guide_manager
        else:
            self.guide_manager = ParallelDownloadManager(
                max_workers=max_workers,
                max_retries=3,
                base_delay=0.5,
                enable_rate_limiting=True,
                monitor=self.monitor,
                log_initialization=True
            )

        if series_manager:
            self.series_manager = series_manager
        else:
            self.series_manager = ParallelDownloadManager(
                max_workers=max_workers,
                max_retries=3,
                base_delay=0.5,
                enable_rate_limiting=True,
                monitor=self.monitor,
                log_initialization=False
            )

        # Initialize adaptive downloader if enabled
        self.adaptive_downloader = None
        if enable_adaptive and max_workers > 1:
            self.adaptive_downloader = AdaptiveParallelDownloader(
                initial_workers=min(2, max_workers),
                max_workers=max_workers
            )

        # Connect base downloader to monitoring if available
        if self.monitor:
            self.base_downloader.set_monitor_callback(self._base_downloader_event_callback)

        # Only log initialization if we created new managers
        if not (guide_manager and series_manager):
            mode = "sequential" if max_workers == 1 else "parallel"
            adaptive_str = " with adaptive adjustment" if enable_adaptive and max_workers > 1 else ""
            monitoring_str = " with real-time monitoring" if enable_monitoring else ""

            logging.info(
                "Unified guide parser initialized: %s mode (%d workers)%s%s",
                mode, max_workers, adaptive_str, monitoring_str
            )

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
        Unified guide download and parsing with improved progress reporting

        Args:
            grid_time_start: Start time for guide data
            day_hours: Number of 3-hour blocks to download
            config_manager: Configuration manager instance
            refresh_hours: Hours to refresh from cache

        Returns:
            Success status
        """
        logging.info("Starting unified guide download and parsing")

        # Get lineup configuration
        lineup_config = config_manager.get_lineup_config()

        logging.info("  Workers: %d", self.max_workers)
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

        # Create downloading progress tracker if monitoring enabled - ONLY for actual downloads
        download_progress_tracker = None
        if self.monitor and download_tasks_count > 0:
            download_progress_tracker = self.monitor.create_progress_tracker("Downloading Guide", download_tasks_count)
            # Store cache info in progress tracker
            with self.monitor.stats_lock:
                if download_progress_tracker.name in self.monitor.progress_bars:
                    self.monitor.progress_bars[download_progress_tracker.name]['cached'] = cached_tasks

        # Log actual download vs cache stats
        if download_tasks_count > 0:
            logging.info("Starting parallel guide block download: %d blocks, %d workers",
                        download_tasks_count, self.max_workers)
            if cached_tasks > 0:
                logging.info("  Will download: %d new blocks, use %d cached blocks",
                            download_tasks_count, cached_tasks)
        else:
            logging.info("All %d blocks found in cache, no downloads needed", cached_tasks)

        # Dynamic progress callback for download progress tracker
        def download_progress_callback(completed, total):
            # Update progress tracker for actual downloads only
            if download_progress_tracker:
                download_progress_tracker.update(completed)

            if total == 0:
                return

            # Calculate dynamic interval (5% or at least every 5 items, max every 100 items)
            interval = max(5, min(total // 20, 100))  # 5% or reasonable bounds

            if completed % interval == 0 or completed == total:
                percent = (completed / total * 100) if total > 0 else 0

                # Smart percentage formatting based on total count
                if total >= 100:
                    # Large datasets: round to nearest 5%
                    rounded_percent = round(percent / 5) * 5
                    formatted_percent = f"{rounded_percent:.0f}%"
                else:
                    # Small to medium datasets: round to nearest unit (no decimals)
                    formatted_percent = f"{percent:.0f}%"

                logging.info("Guide download progress: %d/%d blocks (%s)",
                           completed, total, formatted_percent)

        # Download blocks using guide manager
        download_start = time.time()
        results = self.guide_manager.download_guide_blocks(
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

        # Get statistics from guide manager
        guide_stats = self.guide_manager.get_detailed_statistics()

        total_blocks = day_hours
        success_rate = (parse_success / total_blocks * 100) if total_blocks > 0 else 0

        logging.info("Guide download and parsing completed:")
        logging.info("  Total time: %.1f seconds (download: %.1f, parsing: %.1f)",
                    download_time + parse_time, download_time, parse_time)
        logging.info("  Blocks processed: %d total (%d parsed, %d failed)",
                    total_blocks, parse_success, parse_failed)
        logging.info("  Network stats: %d new, %d cached, %d failed",
                    guide_stats['successful'], guide_stats['cached'], guide_stats['failed'])

        if guide_stats['bytes_downloaded'] > 0:
            logging.info("  Data downloaded: %.1f MB at %.2f MB/s",
                        guide_stats['bytes_downloaded'] / (1024 * 1024),
                        guide_stats.get('throughput_mbps', 0))

        logging.info("  Success rate: %.1f%%", success_rate)

        return success_rate >= 80

    def download_and_parse_extended_details(self) -> bool:
        """
        Download and parse extended program details with improved progress reporting

        Returns:
            Success status based on overall completion, not just new downloads
        """
        logging.info("Starting extended details download with enhanced monitoring")

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

        # Create downloading progress tracker if monitoring enabled - ONLY for actual downloads
        download_details_tracker = None
        if self.monitor and download_count > 0:
            download_details_tracker = self.monitor.create_progress_tracker("Downloading Details", download_count)
            # Store cache info in progress tracker
            with self.monitor.stats_lock:
                if download_details_tracker.name in self.monitor.progress_bars:
                    self.monitor.progress_bars[download_details_tracker.name]['cached'] = cached_count

        # Log actual download vs cache stats
        if download_count > 0:
            logging.info("Starting parallel series details download: %d series, %d workers",
                        download_count, min(self.max_workers, 2))
            if cached_count > 0:
                logging.info("  Will download: %d new series, use %d cached series",
                            download_count, cached_count)
        else:
            logging.info("All %d series found in cache, no downloads needed", cached_count)

        # Dynamic progress callback for series download progress tracker
        def series_progress_callback(completed, total):
            # Update progress tracker for actual downloads only
            if download_details_tracker:
                download_details_tracker.update(completed)

            if total == 0:
                return

            # Calculate dynamic interval (5% or at least every 5 items, max every 50 items)
            interval = max(5, min(total // 20, 50))  # 5% or reasonable bounds

            if completed % interval == 0 or completed == total:
                percent = (completed / total * 100) if total > 0 else 0

                # Smart percentage formatting based on total count
                if total >= 100:
                    # Large datasets (like 369 series): round to nearest 5%
                    rounded_percent = round(percent / 5) * 5
                    formatted_percent = f"{rounded_percent:.0f}%"
                else:
                    # Small to medium datasets: round to nearest unit (no decimals)
                    formatted_percent = f"{percent:.0f}%"

                logging.info("Series details progress: %d/%d (%s)",
                           completed, total, formatted_percent)

        # Download series details using series manager
        download_start = time.time()
        series_details = self.series_manager.download_series_details(
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

        # Get statistics from series manager
        series_stats = self.series_manager.get_detailed_statistics()

        # Enhanced summary logging
        total_time = download_time + process_time
        logging.info("Extended details completed:")
        logging.info("  Total time: %.1f seconds (download: %.1f, processing: %.1f)",
                    total_time, download_time, process_time)
        logging.info("  Unique series: %d", len(unique_series))
        logging.info("  Network stats: %d downloaded, %d cached, %d failed",
                    series_stats['successful'], series_stats['cached'], series_stats['failed'])
        logging.info("  Episodes processed: %d", processed_count)

        if series_stats['bytes_downloaded'] > 0:
            logging.info("  Data downloaded: %.1f MB at %.2f MB/s",
                        series_stats['bytes_downloaded'] / (1024 * 1024),
                        series_stats.get('throughput_mbps', 0))

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
        """Get comprehensive download and processing statistics combining both managers"""
        guide_stats = self.guide_manager.get_detailed_statistics()
        series_stats = self.series_manager.get_detailed_statistics()

        combined_stats = {
            'total_requests': guide_stats.get('total_requests', 0) + series_stats.get('total_requests', 0),
            'successful': guide_stats.get('successful', 0) + series_stats.get('successful', 0),
            'failed': guide_stats.get('failed', 0) + series_stats.get('failed', 0),
            'cached': guide_stats.get('cached', 0) + series_stats.get('cached', 0),
            'waf_blocks': guide_stats.get('waf_blocks', 0) + series_stats.get('waf_blocks', 0),
            'bytes_downloaded': guide_stats.get('bytes_downloaded', 0) + series_stats.get('bytes_downloaded', 0),
            'total_time': max(guide_stats.get('total_time', 0), series_stats.get('total_time', 0)),
        }

        if combined_stats['total_time'] > 0:
            combined_stats['requests_per_second'] = combined_stats['total_requests'] / combined_stats['total_time']
            if combined_stats['bytes_downloaded'] > 0:
                combined_stats['throughput_mbps'] = (combined_stats['bytes_downloaded'] / (1024 * 1024)) / combined_stats['total_time']
            else:
                combined_stats['throughput_mbps'] = 0
        else:
            combined_stats['requests_per_second'] = 0
            combined_stats['throughput_mbps'] = 0

        total_attempts = combined_stats['successful'] + combined_stats['failed']
        if total_attempts > 0:
            combined_stats['success_rate'] = (combined_stats['successful'] / total_attempts) * 100
        else:
            combined_stats['success_rate'] = 100

        if self.monitor:
            monitor_stats = self.monitor.get_statistics()
            combined_stats['monitoring'] = monitor_stats

        if self.adaptive_downloader:
            adaptive_stats = self.adaptive_downloader.get_performance_summary()
            combined_stats['adaptive'] = adaptive_stats

        return combined_stats

    def save_monitoring_metrics(self, filename: str = None):
        """Save monitoring metrics to file if monitoring is enabled"""
        if self.monitor:
            if filename:
                self.monitor.metrics_file = Path(filename)
            self.monitor.save_metrics()
            logging.info("Monitoring metrics saved")

    def cleanup(self):
        """Clean up resources and collect final statistics"""
        logging.info("Cleaning up unified guide parser resources")

        try:
            if self.guide_manager:
                self.guide_manager.cleanup()

            if self.series_manager:
                self.series_manager.cleanup()

            if self.base_downloader:
                self.base_downloader.close()

            self.stop_monitoring()

        except Exception as e:
            logging.warning("Error during cleanup: %s", str(e))


# Backward compatibility alias
GuideParser = UnifiedGuideParser
