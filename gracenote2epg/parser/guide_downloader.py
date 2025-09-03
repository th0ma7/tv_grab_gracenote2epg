"""
Guide data downloader for gracenote2epg
"""

import logging
import time
import urllib.parse
from typing import Dict, Optional

from .base_downloader import BaseDownloader
from ..gracenote2epg_utils import TimeUtils


class GuideDownloader(BaseDownloader):
    """Downloads TV guide data blocks"""
    
    def __init__(self, downloader, cache_manager):
        super().__init__(downloader, cache_manager)
        self.base_url = "http://tvlistings.gracenote.com/api/grid"
        
    def download(self, grid_time_start: float, day_hours: int, 
                 lineup_config: Dict, refresh_hours: int = 48) -> bool:
        """
        Download guide blocks with intelligent caching
        
        Args:
            grid_time_start: Start time for guide
            day_hours: Number of 3-hour blocks to download
            lineup_config: Lineup configuration from config manager
            refresh_hours: Hours to refresh from cache
            
        Returns:
            bool: True if successful (80%+ blocks available)
        """
        logging.info("Starting optimized guide download")
        logging.info("  Refresh window: first %d hours will be re-downloaded", refresh_hours)
        logging.info("  Guide duration: %d blocks (%d hours)", day_hours, day_hours * 3)
        
        self._log_lineup_config(lineup_config)
        
        # Download each block
        grid_time = grid_time_start
        for block_num in range(day_hours):
            success = self._download_block(grid_time, lineup_config, refresh_hours)
            
            if success:
                # Determine if it was downloaded or cached
                time_from_now = grid_time - time.time()
                if time_from_now < (refresh_hours * 3600):
                    self.downloaded_count += 1
                else:
                    self.cached_count += 1
            else:
                self.failed_count += 1
                
            grid_time += 10800  # Next 3-hour block
            
        # Log statistics
        self._log_statistics()
        
        return self._calculate_success_rate() >= 80
    
    def _download_block(self, grid_time: float, lineup_config: Dict, 
                       refresh_hours: int) -> bool:
        """Download a single guide block"""
        # Generate filename
        standard_block_time = TimeUtils.get_standard_block_time(grid_time)
        filename = standard_block_time.strftime("%Y%m%d%H") + ".json.gz"
        
        # Build URL
        url = self.build_url(lineup_config, grid_time)
        
        # Download with cache
        return self.cache_manager.download_guide_block_safe(
            self.downloader, grid_time, filename, url, refresh_hours
        )
    
    def build_url(self, lineup_config: Dict, grid_time: float) -> str:
        """Build Gracenote API URL"""
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
        return f"{self.base_url}?{query_string}"
    
    def _log_lineup_config(self, lineup_config: Dict):
        """Log lineup configuration"""
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
    
    def _log_statistics(self):
        """Log download statistics"""
        stats = self.get_statistics()
        total = stats["total"]
        
        logging.info("Guide download completed:")
        logging.info(
            "  Blocks: %d total (%d downloaded, %d cached, %d failed)",
            total,
            self.downloaded_count,
            self.cached_count,
            self.failed_count,
        )
        logging.info(
            "  Cache efficiency: %.1f%% reused",
            (self.cached_count / total * 100) if total > 0 else 0,
        )
        logging.info("  Success rate: %.1f%%", stats["success_rate"])
