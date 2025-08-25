"""
gracenote2epg.gracenote2epg_parser - Guide data parsing with parallel download support

Enhanced version with parallel downloading capabilities for improved performance.
"""

import calendar
import json
import logging
import re
import time
import urllib.parse
from typing import Dict, List, Optional, Any

from .gracenote2epg_downloader import OptimizedDownloader
from .gracenote2epg_parallel import ParallelDownloadManager, AdaptiveParallelDownloader
from .gracenote2epg_tvheadend import TvheadendClient
from .gracenote2epg_utils import CacheManager, TimeUtils


class GuideParser:
    """Parses TV guide data with optional parallel download support"""

    def __init__(
        self,
        cache_manager: CacheManager,
        downloader: OptimizedDownloader,
        tvh_client: Optional[TvheadendClient] = None,
        enable_parallel: bool = True,
        max_workers: int = 4
    ):
        """
        Initialize guide parser

        Args:
            cache_manager: Cache manager instance
            downloader: Sequential downloader (fallback)
            tvh_client: Optional TVheadend client
            enable_parallel: Enable parallel downloading
            max_workers: Maximum parallel workers
        """
        self.cache_manager = cache_manager
        self.downloader = downloader
        self.tvh_client = tvh_client
        self.schedule: Dict = {}

        # Parallel download support
        self.enable_parallel = enable_parallel
        self.parallel_manager = None
        self.adaptive_downloader = None

        if enable_parallel:
            try:
                self.parallel_manager = ParallelDownloadManager(
                    max_workers=max_workers,
                    max_retries=3,
                    base_delay=0.5,
                    enable_rate_limiting=True
                )

                self.adaptive_downloader = AdaptiveParallelDownloader(
                    initial_workers=2,
                    max_workers=max_workers
                )

                logging.info("Parallel downloading enabled with %d max workers", max_workers)
            except Exception as e:
                logging.warning("Could not initialize parallel downloading: %s", str(e))
                logging.info("Falling back to sequential downloading")
                self.enable_parallel = False

    def optimized_guide_download(
        self, grid_time_start: float, day_hours: int, config_manager, refresh_hours: int = 48
    ) -> bool:
        """
        Optimized guide download with parallel support

        Uses parallel downloading when available for improved performance
        """
        logging.info("Starting optimized guide download (parallel mode: %s)",
                    "enabled" if self.enable_parallel else "disabled")

        # Get lineup configuration
        lineup_config = config_manager.get_lineup_config()

        logging.info("  Refresh window: first %d hours will be re-downloaded", refresh_hours)
        logging.info("  Guide duration: %d blocks (%d hours)", day_hours, day_hours * 3)

        # Choose download method
        if self.enable_parallel and self.parallel_manager:
            return self._parallel_guide_download(
                grid_time_start, day_hours, lineup_config, config_manager, refresh_hours
            )
        else:
            return self._sequential_guide_download(
                grid_time_start, day_hours, lineup_config, refresh_hours
            )

    def _parallel_guide_download(
        self, grid_time_start: float, day_hours: int, lineup_config: Dict,
        config_manager, refresh_hours: int
    ) -> bool:
        """Download guide blocks in parallel"""

        logging.info("Using PARALLEL download method for guide blocks")

        # Prepare all download tasks
        tasks = []
        grid_time = grid_time_start

        for count in range(day_hours):
            # Generate standardized filename
            standard_block_time = TimeUtils.get_standard_block_time(grid_time)
            filename = standard_block_time.strftime("%Y%m%d%H") + ".json.gz"

            # Build download URL
            url = self._build_gracenote_url(lineup_config, grid_time)

            tasks.append({
                'grid_time': grid_time,
                'filename': filename,
                'url': url,
                'count': count
            })

            grid_time = grid_time + 10800  # Next 3-hour block

        # Define progress callback
        def progress_callback(completed, total):
            if completed % 10 == 0 or completed == total:
                percent = (completed / total * 100) if total > 0 else 0
                logging.info("Guide download progress: %d/%d blocks (%.1f%%)",
                           completed, total, percent)

        # Download blocks in parallel
        results = self.parallel_manager.download_guide_blocks(
            tasks=tasks,
            cache_manager=self.cache_manager,
            config_manager=config_manager,  # Now passed correctly
            refresh_hours=refresh_hours,
            progress_callback=progress_callback
        )

        # Parse downloaded/cached blocks
        parse_success = 0
        parse_failed = 0

        for task in tasks:
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

                except Exception as e:
                    logging.warning("Parse error for %s: %s", filename, str(e))
                    parse_failed += 1
            else:
                logging.warning("No content available for %s", filename)
                parse_failed += 1

        # Get statistics
        stats = self.parallel_manager.get_statistics()

        # Summary
        total_blocks = day_hours
        success_rate = (parse_success / total_blocks * 100) if total_blocks > 0 else 0

        logging.info("Parallel guide download completed:")
        logging.info("  Blocks processed: %d total (%d parsed, %d failed)",
                    total_blocks, parse_success, parse_failed)
        logging.info("  Downloads: %d new, %d cached, %d failed",
                    stats['successful'], stats['cached'], stats['failed'])
        logging.info("  Performance: %.1f MB downloaded in %.1f seconds",
                    stats['bytes_downloaded'] / (1024 * 1024), stats['total_time'])
        logging.info("  Success rate: %.1f%%", success_rate)

        if stats['waf_blocks'] > 0:
            logging.warning("  WAF blocks encountered: %d", stats['waf_blocks'])

        return success_rate >= 80

    def _sequential_guide_download(
        self, grid_time_start: float, day_hours: int, lineup_config: Dict, refresh_hours: int
    ) -> bool:
        """Original sequential download method (fallback)"""

        logging.info("Using SEQUENTIAL download method for guide blocks")

        downloaded_count = 0
        cached_count = 0
        failed_count = 0

        count = 0
        grid_time = grid_time_start

        while count < day_hours:
            # Generate standardized filename
            standard_block_time = TimeUtils.get_standard_block_time(grid_time)
            filename = standard_block_time.strftime("%Y%m%d%H") + ".json.gz"

            # Build download URL
            url = self._build_gracenote_url(lineup_config, grid_time)

            # Download block safely
            if self.cache_manager.download_guide_block_safe(
                self.downloader, grid_time, filename, url, refresh_hours
            ):
                # Determine if it was downloaded or cached
                time_from_now = grid_time - time.time()
                if time_from_now < (refresh_hours * 3600):
                    downloaded_count += 1
                else:
                    cached_count += 1
            else:
                failed_count += 1

            # Parse the file
            content = self.cache_manager.load_guide_block(filename)
            if content:
                try:
                    logging.debug("Parsing %s", filename)

                    if count == 0:
                        self.parse_stations(content)
                    self.parse_episodes(content)

                except Exception as e:
                    logging.warning("Parse error for %s: %s", filename, str(e))

            count += 1
            grid_time = grid_time + 10800  # Next 3-hour block

        # Summary
        total_blocks = day_hours
        success_rate = (
            ((downloaded_count + cached_count) / total_blocks * 100) if total_blocks > 0 else 0
        )

        logging.info("Sequential guide download completed:")
        logging.info(
            "  Blocks: %d total (%d downloaded, %d cached, %d failed)",
            total_blocks,
            downloaded_count,
            cached_count,
            failed_count,
        )
        logging.info("  Success rate: %.1f%%", success_rate)

        return success_rate >= 80

    def parse_extended_details(self) -> bool:
        """Download and parse extended program details with parallel support"""

        if self.enable_parallel and self.parallel_manager:
            return self._parallel_extended_details()
        else:
            return self._sequential_extended_details()

    def _parallel_extended_details(self) -> bool:
        """Download extended details in parallel"""

        logging.info("Starting PARALLEL extended details download")

        # Collect unique series IDs
        unique_series = set()
        series_usage = {}  # Track how many times each series is used

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

        # Progress callback
        def progress_callback(completed, total):
            if completed % 50 == 0 or completed == total:
                percent = (completed / total * 100) if total > 0 else 0
                logging.info("Series details progress: %d/%d (%.1f%%)",
                           completed, total, percent)

        # Download in parallel (without duplicate progress callback)
        series_details = self.parallel_manager.download_series_details(
            series_list=series_list,
            cache_manager=self.cache_manager,
            progress_callback=progress_callback
        )

        # Process downloaded details
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
                        except Exception as e:
                            logging.warning("Error processing series %s: %s", series_id, str(e))
                            failed_count += 1

        # Get statistics
        stats = self.parallel_manager.get_statistics()

        # Summary
        logging.info("Parallel extended details completed:")
        logging.info("  Unique series: %d", len(unique_series))
        logging.info("  Downloaded: %d, Cached: %d, Failed: %d",
                    stats['successful'], stats['cached'], stats['failed'])
        logging.info("  Episodes processed: %d", processed_count)
        logging.info("  Performance: %.1f MB in %.1f seconds",
                    stats['bytes_downloaded'] / (1024 * 1024), stats['total_time'])

        # Adaptive performance summary
        if self.adaptive_downloader:
            perf_summary = self.adaptive_downloader.get_performance_summary()
            if perf_summary:
                logging.info("  Adaptive concurrency: %d workers (adjusted %d times)",
                           perf_summary['current_workers'],
                           perf_summary['total_adjustments'])

        success_rate = (stats['successful'] / len(series_list) * 100) if series_list else 100
        return success_rate >= 70 or not series_list

    def _sequential_extended_details(self) -> bool:
        """Original sequential extended details download (fallback)"""

        logging.info("Starting SEQUENTIAL extended details download")

        show_list = []
        fail_list = []
        download_count = 0
        success_count = 0
        cached_series = set()
        total_usages = 0

        # Collect series IDs
        unique_series_to_download = set()

        for station in self.schedule:
            sdict = self.schedule[station]
            for episode in sdict:
                if not episode.startswith("ch"):
                    edict = sdict[episode]
                    series_id = edict.get("epseries")

                    if series_id and series_id not in fail_list:
                        show_list.append(series_id)

                        cached_details = self.cache_manager.load_series_details(series_id)
                        if cached_details is None and series_id not in unique_series_to_download:
                            unique_series_to_download.add(series_id)

        total_downloads_needed = len(unique_series_to_download)
        logging.info(
            "Extended details: %d unique series found, %d downloads needed",
            len(set(show_list)),
            total_downloads_needed,
        )

        # Download sequentially
        current_download = 0
        processed_series = set()

        for station in self.schedule:
            sdict = self.schedule[station]
            for episode in sdict:
                if not episode.startswith("ch"):
                    edict = sdict[episode]
                    series_id = edict.get("epseries")

                    if not series_id or series_id in fail_list or series_id in processed_series:
                        continue

                    processed_series.add(series_id)

                    cached_details = self.cache_manager.load_series_details(series_id)

                    if cached_details is None:
                        current_download += 1
                        download_count += 1

                        url = "https://tvlistings.gracenote.com/api/program/overviewDetails"
                        data = f"programSeriesID={series_id}"

                        logging.info(
                            "Downloading extended details for: %s (%d/%d)",
                            series_id,
                            current_download,
                            total_downloads_needed,
                        )

                        data_encoded = data.encode("utf-8")
                        content = self.downloader.download_with_retry_urllib(
                            url, data=data_encoded, timeout=6
                        )

                        if content:
                            if self.cache_manager.save_series_details(series_id, content):
                                try:
                                    cached_details = json.loads(content)
                                    logging.info(
                                        "  Successfully downloaded: %s.json (%d bytes)",
                                        series_id,
                                        len(content),
                                    )
                                    success_count += 1
                                except json.JSONDecodeError:
                                    logging.warning("  Invalid JSON received for: %s", series_id)
                                    fail_list.append(series_id)
                                    continue
                            else:
                                logging.warning("  Error saving details for: %s", series_id)
                                fail_list.append(series_id)
                                continue
                        else:
                            logging.warning("  Failed to download details for: %s", series_id)
                            fail_list.append(series_id)
                            continue
                    else:
                        cached_series.add(series_id)
                        total_usages += 1
                        logging.debug("Using cached details for: %s", series_id)

                    if cached_details:
                        self._process_series_details(edict, cached_details, series_id)

        # Statistics
        total_series = len(set(show_list))
        unique_cached = len(cached_series)

        logging.info("Sequential extended details completed:")
        logging.info("  Total unique series: %d", total_series)
        logging.info("  Downloads attempted: %d", download_count)
        logging.info("  Successful downloads: %d", success_count)
        logging.info("  From cache: %d", unique_cached)
        logging.info("  Failed downloads: %d", len(fail_list))

        success_rate = (success_count / download_count * 100) if download_count > 0 else 100
        return success_rate >= 70 or download_count == 0

    def _build_gracenote_url(self, lineup_config: Dict, grid_time: float) -> str:
        """Build Gracenote URL with simplified lineup configuration"""

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

                if self._should_process_station(station):
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

                        if not short_desc and not long_desc:
                            logging.debug(
                                "No description found for: %s - %s",
                                program.get("title", "Unknown"),
                                program.get("episodeTitle", ""),
                            )

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

                        ep_data.update(
                            {
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
                            }
                        )

                        if ep_data["epshow"] and "TBA" in ep_data["epshow"]:
                            check_tba = "Unsafe"
                        elif ep_data["eptitle"] and "TBA" in ep_data["eptitle"]:
                            check_tba = "Unsafe"

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
                                logging.info("  Found TBA listing in %s", series_id)
                        except Exception:
                            pass

        except Exception as e:
            logging.warning("Error processing series details for %s: %s", series_id, str(e))

    def cleanup(self):
        """Clean up resources and collect final statistics"""
        if self.parallel_manager:
            # Collect final statistics from all thread-local downloaders before cleanup
            self.parallel_manager.consolidate_downloader_stats()
            self.parallel_manager.cleanup()
