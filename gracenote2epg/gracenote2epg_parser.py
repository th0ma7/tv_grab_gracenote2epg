"""
gracenote2epg.gracenote2epg_parser - Guide data parsing

Handles parsing of TV guide data from gracenote.com, including stations,
episodes, and extended series details with intelligent caching.
Now uses simplified lineupid configuration with automatic normalization.
"""

import calendar
import json
import logging
import re
import time
import urllib.parse
from typing import Dict, List, Optional

from .gracenote2epg_downloader import OptimizedDownloader
from .gracenote2epg_tvheadend import TvheadendClient
from .gracenote2epg_utils import CacheManager, TimeUtils


class GuideParser:
    """Parses TV guide data and manages extended details"""

    def __init__(
        self,
        cache_manager: CacheManager,
        downloader: OptimizedDownloader,
        tvh_client: Optional[TvheadendClient] = None,
    ):
        self.cache_manager = cache_manager
        self.downloader = downloader
        self.tvh_client = tvh_client
        self.schedule: Dict = {}

    def optimized_guide_download(
        self, grid_time_start: float, day_hours: int, config_manager, refresh_hours: int = 48
    ) -> bool:
        """Optimized guide download with simplified lineup configuration"""

        logging.info("Starting optimized guide download (with simplified lineup configuration)")

        # Get simplified lineup configuration
        lineup_config = config_manager.get_lineup_config()

        # Log configuration used (debug level to avoid duplication)
        if lineup_config["auto_detected"]:
            logging.debug(
                "Using auto-detected lineup: %s (device: %s)",
                lineup_config["lineup_id"],
                lineup_config["device_type"],
            )
        else:
            logging.debug(
                "Using configured lineup: %s → %s (device: %s)",
                lineup_config["original_config"],
                lineup_config["lineup_id"],
                lineup_config["device_type"],
            )

        logging.info("  Refresh window: first %d hours will be re-downloaded", refresh_hours)
        logging.info("  Guide duration: %d blocks (%d hours)", day_hours, day_hours * 3)

        downloaded_count = 0
        cached_count = 0
        failed_count = 0

        count = 0
        grid_time = grid_time_start

        while count < day_hours:
            # Generate standardized filename
            standard_block_time = TimeUtils.get_standard_block_time(grid_time)
            filename = standard_block_time.strftime("%Y%m%d%H") + ".json.gz"

            # Build download URL with simplified configuration
            url = self._build_gracenote_url(lineup_config, grid_time)

            # Download block safely
            if self.cache_manager.download_guide_block_safe(
                self.downloader, grid_time, filename, url, refresh_hours
            ):
                # Determine if it was downloaded or cached
                time_from_now = grid_time - time.time()
                if time_from_now < (refresh_hours * 3600):
                    # In refresh window - likely downloaded
                    downloaded_count += 1
                else:
                    # Outside refresh window - likely cached
                    cached_count += 1
            else:
                failed_count += 1

            # Parse the file (cached or new)
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

        logging.info("Guide download completed:")
        logging.info(
            "  Blocks: %d total (%d downloaded, %d cached, %d failed)",
            total_blocks,
            downloaded_count,
            cached_count,
            failed_count,
        )
        logging.info(
            "  Cache efficiency: %.1f%% reused",
            (cached_count / total_blocks * 100) if total_blocks > 0 else 0,
        )
        logging.info("  Success rate: %.1f%%", success_rate)

        # Log URL format used (debug level to avoid duplication)
        if lineup_config["auto_detected"]:
            logging.debug("API calls used auto-detected lineup configuration")
        else:
            logging.debug("API calls used configured lineup: %s", lineup_config["original_config"])

        return success_rate >= 80  # Consider successful if 80%+ blocks available

    def _build_gracenote_url(self, lineup_config: Dict, grid_time: float) -> str:
        """Build Gracenote URL with simplified lineup configuration"""

        base_url = "http://tvlistings.gracenote.com/api/grid"

        # Parameters in optimal order for maximum compatibility
        params = [
            ("aid", "orbebb"),
            ("TMSID", ""),
            ("AffiliateID", "lat"),
            ("lineupId", lineup_config.get("lineup_id", "")),  # Normalized lineup ID
            ("timespan", "3"),
            ("headendId", lineup_config.get("headend_id", "lineupId")),  # Always 'lineupId'
            ("country", lineup_config.get("country", "USA")),
            ("device", lineup_config.get("device_type", "-")),  # Auto-detected device type
            ("postalCode", lineup_config.get("postal_code", "")),
            ("time", str(int(grid_time))),
            ("isOverride", "true"),
            ("pref", "-"),
            ("userId", "-"),
        ]

        # Build URL
        query_string = "&".join(
            [f"{key}={urllib.parse.quote(str(value))}" for key, value in params]
        )
        full_url = f"{base_url}?{query_string}"

        # Debug logging (without exposing full URL to avoid spam)
        if lineup_config.get("auto_detected"):
            logging.debug(
                "Built URL with auto-detected lineup: %s, device: %s",
                lineup_config.get("lineup_id", ""),
                lineup_config.get("device_type", ""),
            )
        else:
            logging.debug(
                "Built URL with configured lineup: %s → %s, device: %s",
                lineup_config.get("original_config", ""),
                lineup_config.get("lineup_id", ""),
                lineup_config.get("device_type", ""),
            )

        return full_url

    def parse_stations(self, content: bytes):
        """Parse station information from guide data"""
        try:
            ch_guide = json.loads(content)

            for station in ch_guide.get("channels", []):
                station_id = station.get("channelId")

                # Determine if this station should be processed
                if self._should_process_station(station):
                    self.schedule[station_id] = {}

                    call_sign = station.get("callSign")
                    affiliate_name = station.get("affiliateName")

                    self.schedule[station_id]["chfcc"] = call_sign
                    self.schedule[station_id]["chnam"] = affiliate_name

                    # Extract icon URL (remove query parameters)
                    thumbnail = station.get("thumbnail", "")
                    if thumbnail:
                        self.schedule[station_id]["chicon"] = thumbnail.split("?")[0]
                    else:
                        self.schedule[station_id]["chicon"] = ""

                    # Handle channel number with subchannel logic
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

                # Same logic as in parse_stations
                if self._should_process_station(station):
                    episodes = station.get("events", [])

                    for episode in episodes:
                        # Create episode key from start time
                        start_time_str = episode.get("startTime", "")
                        if start_time_str:
                            try:
                                ep_key = str(
                                    calendar.timegm(
                                        time.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ")
                                    )
                                )
                            except (ValueError, TypeError):
                                continue  # Skip invalid time format
                        else:
                            continue  # Skip if no start time

                        # Initialize episode data
                        self.schedule[station_id][ep_key] = {}
                        ep_data = self.schedule[station_id][ep_key]

                        # Parse program information
                        program = episode.get("program", {})

                        # Get descriptions with fallback logic
                        short_desc = program.get("shortDesc") or ""
                        long_desc = program.get("longDesc") or ""

                        # Handle None values
                        if short_desc is None:
                            short_desc = ""
                        if long_desc is None:
                            long_desc = ""

                        # Debug: log if no description found
                        if not short_desc and not long_desc:
                            logging.debug(
                                "No description found for: %s - %s",
                                program.get("title", "Unknown"),
                                program.get("episodeTitle", ""),
                            )

                        # Parse end time
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

                        # Populate episode data
                        ep_data.update(
                            {
                                "epid": program.get("tmsId"),
                                "epstart": ep_key,
                                "epend": ep_end,
                                "eplength": episode.get("duration"),
                                "epshow": program.get("title"),
                                "eptitle": program.get("episodeTitle"),
                                "epdesc": (
                                    long_desc if long_desc else short_desc
                                ),  # Priority to longDesc
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
                                "epoad": None,  # Will be populated by extended details
                                "epstar": None,
                                "epfilter": episode.get("filter", []),
                                "epgenres": None,  # Will be populated by extended details
                                "epcredits": None,  # Will be populated by extended details
                                "epseries": program.get("seriesId"),
                                "epimage": None,  # Will be populated by extended details
                                "epfan": None,  # Will be populated by extended details
                                "epseriesdesc": None,  # Will be populated by extended details
                            }
                        )

                        # Check for TBA listings
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
                explicit_station_list=None,  # This would come from config
                use_tvh_matching=True,
                use_channel_matching=True,
            )
        return True  # Process all stations if no TVH client

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

    def parse_extended_details(self) -> bool:
        """Download and parse extended program details - returns success status"""
        show_list = []
        fail_list = []
        download_count = 0
        success_count = 0
        cached_series = set()
        total_usages = 0

        logging.info("Starting extended details download using optimized session")

        try:
            # First pass: collect all unique series IDs and count total downloads needed
            unique_series_to_download = set()

            for station in self.schedule:
                sdict = self.schedule[station]
                for episode in sdict:
                    if not episode.startswith("ch"):
                        edict = sdict[episode]
                        series_id = edict.get("epseries")

                        # Check that series_id is not None or empty
                        if series_id and series_id not in fail_list:
                            show_list.append(series_id)

                            # Check if we need to download this series
                            cached_details = self.cache_manager.load_series_details(series_id)
                            if (
                                cached_details is None
                                and series_id not in unique_series_to_download
                            ):
                                unique_series_to_download.add(series_id)

            total_downloads_needed = len(unique_series_to_download)
            logging.info(
                "Extended details: %d unique series found, %d downloads needed",
                len(set(show_list)),
                total_downloads_needed,
            )

            # Second pass: process all series with progress tracking
            current_download = 0
            processed_series = set()

            for station in self.schedule:
                sdict = self.schedule[station]
                for episode in sdict:
                    if not episode.startswith("ch"):
                        edict = sdict[episode]
                        series_id = edict.get("epseries")

                        # Check that series_id is not None or empty
                        if not series_id or series_id in fail_list or series_id in processed_series:
                            continue

                        processed_series.add(series_id)

                        # Check if we already have cached details
                        cached_details = self.cache_manager.load_series_details(series_id)

                        if cached_details is None:
                            # Need to download new details
                            current_download += 1
                            download_count += 1

                            url = "https://tvlistings.gracenote.com/api/program/overviewDetails"
                            data = f"programSeriesID={series_id}"

                            # Add progress counter to the log message
                            logging.info(
                                "Downloading extended details for: %s (%d/%d)",
                                series_id,
                                current_download,
                                total_downloads_needed,
                            )
                            logging.debug("  URL: %s?%s", url, data)

                            # Encode data for urllib
                            data_encoded = data.encode("utf-8")

                            # Download using urllib method
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
                                        logging.warning(
                                            "  Invalid JSON received for: %s", series_id
                                        )
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
                            # Use existing cached details
                            cached_series.add(series_id)
                            total_usages += 1
                            logging.debug("Using cached details for: %s", series_id)

                        # Process the details (cached or newly downloaded)
                        if cached_details:
                            self._process_series_details(edict, cached_details, series_id)

            # Final statistics
            stats = self.downloader.get_stats()
            total_series = len(set(show_list))
            unique_cached = len(cached_series)

            logging.info("Extended details processing completed:")
            logging.info("  Total unique series: %d", total_series)
            logging.info("  Downloads attempted: %d", download_count)
            logging.info("  Successful downloads: %d", success_count)
            logging.info("  Unique series from cache: %d", unique_cached)
            logging.info("  Total cache file usages: %d", total_usages)
            logging.info("  Failed downloads: %d", len(fail_list))
            logging.info("  WAF blocks during details: %d", stats["waf_blocks"])

            # Calculate success rate and cache efficiency
            success_rate = (success_count / download_count * 100) if download_count > 0 else 100
            cache_efficiency = (unique_cached / total_series * 100) if total_series > 0 else 0

            logging.info("  Download success rate: %.1f%%", success_rate)
            logging.info(
                "  Cache efficiency: %.1f%% (%d/%d unique series reused)",
                cache_efficiency,
                unique_cached,
                total_series,
            )

            if fail_list:
                logging.info("  Failed series (first 10): %s", ", ".join(fail_list[:10]))

            # Return success status
            return success_rate >= 70 or download_count == 0

        except Exception as e:
            logging.error("Critical error in parse_extended_details: %s", str(e))
            return False

    def _process_series_details(self, episode_data: Dict, series_details: Dict, series_id: str):
        """Process extended series details and update episode data"""
        try:
            # Extract extended series description
            series_desc = series_details.get("seriesDescription")
            if series_desc and str(series_desc).strip():
                episode_data["epseriesdesc"] = str(series_desc).strip()
                logging.debug(
                    "Found extended series description for %s: %s",
                    series_id,
                    series_desc[:50] + "..." if len(series_desc) > 50 else series_desc,
                )

            # Process other details
            episode_data["epimage"] = series_details.get("seriesImage")
            episode_data["epfan"] = series_details.get("backgroundImage")

            # Handle genres
            ep_genres = series_details.get("seriesGenres")
            if series_id.startswith("MV"):  # Movie
                overview_tab = series_details.get("overviewTab", {})
                if isinstance(overview_tab, dict):
                    episode_data["epcredits"] = overview_tab.get("cast")
                ep_genres = "Movie|" + ep_genres if ep_genres else "Movie"

            if ep_genres:
                episode_data["epgenres"] = ep_genres.split("|")

            # Process upcoming episodes for original air date
            ep_list = series_details.get("upcomingEpisodeTab", [])
            if not isinstance(ep_list, list):
                ep_list = []

            ep_id = episode_data.get("epid", "")
            for airing in ep_list:
                if not isinstance(airing, dict):
                    continue

                if ep_id.lower() == airing.get("tmsID", "").lower():
                    if not series_id.startswith("MV"):  # Not a movie
                        try:
                            orig_date = airing.get("originalAirDate")
                            if orig_date and orig_date != "":
                                # Handle date format
                                ep_oad = re.sub("Z", ":00Z", orig_date)
                                episode_data["epoad"] = str(
                                    calendar.timegm(time.strptime(ep_oad, "%Y-%m-%dT%H:%M:%SZ"))
                                )
                        except Exception:
                            pass  # Ignore date parsing errors

                        # Check for TBA listings and remove if found
                        try:
                            tba_check = airing.get("episodeTitle", "")
                            if tba_check and "TBA" in tba_check:
                                # Mark for deletion (would be handled by cache cleanup)
                                logging.info("  Found TBA listing in %s", series_id)
                        except Exception:
                            pass

        except Exception as e:
            logging.warning("Error processing series details for %s: %s", series_id, str(e))
