"""
Core that orchestrates downloading and parsing
"""

import logging
from typing import Dict, List, Optional

from .guide_downloader import GuideDownloader
from .guide_parser import GuideParser
from .series_downloader import SeriesDownloader
from .series_parser import SeriesParser


class DataParser:
    """Main manager for TV guide operations"""
    
    def __init__(self, cache_manager, downloader, tvh_client=None):
        self.cache_manager = cache_manager
        self.downloader = downloader
        self.tvh_client = tvh_client
        
        # Initialize components
        self.guide_downloader = GuideDownloader(downloader, cache_manager)
        self.guide_parser = GuideParser(tvh_client)
        self.series_downloader = SeriesDownloader(downloader, cache_manager)
        self.series_parser = SeriesParser()
        
        self.schedule: Dict = {}
        
    def download_and_parse_guide(self, grid_time_start: float, day_hours: int,
                                 config_manager, refresh_hours: int = 48) -> bool:
        """
        Download and parse TV guide data
        
        Args:
            grid_time_start: Start time for guide
            day_hours: Number of 3-hour blocks
            config_manager: Configuration manager
            refresh_hours: Hours to refresh
            
        Returns:
            bool: True if successful
        """
        # Get lineup configuration
        lineup_config = config_manager.get_lineup_config()
        
        # Download guide blocks
        success = self.guide_downloader.download(
            grid_time_start, day_hours, lineup_config, refresh_hours
        )
        
        if not success:
            logging.warning("Guide download had issues, continuing with available data")
        
        # Parse downloaded blocks
        self._parse_guide_blocks(grid_time_start, day_hours)
        
        # Update schedule
        self.schedule = self.guide_parser.get_schedule()
        
        return success
    
    def _parse_guide_blocks(self, grid_time_start: float, day_hours: int):
        """Parse all downloaded guide blocks"""
        grid_time = grid_time_start
        
        for count in range(day_hours):
            # Generate filename
            from ..gracenote2epg_utils import TimeUtils
            standard_block_time = TimeUtils.get_standard_block_time(grid_time)
            filename = standard_block_time.strftime("%Y%m%d%H") + ".json.gz"
            
            # Load and parse block
            content = self.cache_manager.load_guide_block(filename)
            if content:
                try:
                    logging.debug("Parsing %s", filename)
                    
                    if count == 0:
                        self.guide_parser.parse_stations(content)
                    self.guide_parser.parse_episodes(content)
                    
                except Exception as e:
                    logging.warning("Parse error for %s: %s", filename, str(e))
            
            grid_time += 10800  # Next 3-hour block
    
    def download_and_parse_series_details(self) -> bool:
        """Download and parse extended series details"""
        # Extract active series list
        series_list = self.get_active_series_list()
        
        if not series_list:
            logging.info("No series found for extended details download")
            return True
        
        # Download series details
        success = self.series_downloader.download(series_list)
        
        if not success:
            logging.warning("Extended details download had issues, using basic descriptions")
        
        # Parse and apply series details
        self._apply_series_details()
        
        return success
    
    def _apply_series_details(self):
        """Apply series details to episodes"""
        processed_series = set()
        
        for station_id, station_data in self.schedule.items():
            for episode_key, episode_data in station_data.items():
                if episode_key.startswith("ch"):
                    continue
                    
                series_id = episode_data.get("epseries")
                if not series_id or series_id in processed_series:
                    continue
                    
                # Get series details (from cache or fresh download)
                series_details = self.series_downloader.get_cached_details(series_id)
                
                if series_details:
                    self.series_parser.parse_series_details(
                        episode_data, series_details, series_id
                    )
                    processed_series.add(series_id)
    
    def get_active_series_list(self) -> List[str]:
        """Extract list of active series from current schedule"""
        active_series = set()
        
        for station_id, station_data in self.schedule.items():
            for episode_key, episode_data in station_data.items():
                if not episode_key.startswith("ch"):
                    series_id = episode_data.get("epseries")
                    if series_id:
                        active_series.add(series_id)
                        
        return list(active_series)
    
    def get_schedule(self) -> Dict:
        """Get the complete schedule"""
        return self.schedule
