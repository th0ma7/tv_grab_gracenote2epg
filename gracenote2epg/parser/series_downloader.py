"""
Series details downloader for gracenote2epg
"""

import json
import logging
from typing import Dict, List, Optional, Set

from .base_downloader import BaseDownloader


class SeriesDownloader(BaseDownloader):
    """Downloads extended series details"""
    
    def __init__(self, downloader, cache_manager):
        super().__init__(downloader, cache_manager)
        self.base_url = "https://tvlistings.gracenote.com/api/program/overviewDetails"
        self.failed_series: List[str] = []
        self.cached_series: Set[str] = set()
        
    def download(self, series_list: List[str]) -> bool:
        """
        Download extended details for series
        
        Args:
            series_list: List of series IDs to download
            
        Returns:
            bool: True if 70%+ successful
        """
        logging.info("Starting extended details download")
        
        # Get unique series and check what needs downloading
        unique_series = set(series_list)
        to_download = self._identify_series_to_download(unique_series)
        
        logging.info(
            "Extended details: %d unique series found, %d downloads needed",
            len(unique_series),
            len(to_download),
        )
        
        # Download each series
        for index, series_id in enumerate(to_download, 1):
            success = self._download_series(series_id, index, len(to_download))
            
            if success:
                self.downloaded_count += 1
            else:
                self.failed_count += 1
                self.failed_series.append(series_id)
        
        # Count cached series
        self.cached_count = len(self.cached_series)
        
        # Log statistics
        self._log_statistics()
        
        return self._calculate_success_rate() >= 70 or self.downloaded_count == 0
    
    def _identify_series_to_download(self, unique_series: Set[str]) -> List[str]:
        """Identify which series need to be downloaded"""
        to_download = []
        
        for series_id in unique_series:
            if not series_id:
                continue
                
            # Check cache
            cached_details = self.cache_manager.load_series_details(series_id)
            if cached_details is None:
                to_download.append(series_id)
            else:
                self.cached_series.add(series_id)
                
        return to_download
    
    def _download_series(self, series_id: str, index: int, total: int) -> bool:
        """Download a single series details"""
        url = self.build_url(series_id)
        data = f"programSeriesID={series_id}".encode("utf-8")
        
        logging.info(
            "Downloading extended details for: %s (%d/%d)",
            series_id,
            index,
            total,
        )
        logging.debug("  URL: %s?programSeriesID=%s", self.base_url, series_id)
        
        # Download using urllib method
        content = self.downloader.download_with_retry_urllib(
            url, data=data, timeout=6
        )
        
        if content:
            try:
                # Validate JSON
                json.loads(content)
                
                # Save to cache
                if self.cache_manager.save_series_details(series_id, content):
                    logging.info(
                        "  Successfully downloaded: %s.json (%d bytes)",
                        series_id,
                        len(content),
                    )
                    return True
                else:
                    logging.warning("  Error saving details for: %s", series_id)
                    return False
                    
            except json.JSONDecodeError:
                logging.warning("  Invalid JSON received for: %s", series_id)
                return False
        else:
            logging.warning("  Failed to download details for: %s", series_id)
            return False
    
    def build_url(self, series_id: str) -> str:
        """Build series details URL"""
        return self.base_url
    
    def get_cached_details(self, series_id: str) -> Optional[Dict]:
        """Get cached series details"""
        return self.cache_manager.load_series_details(series_id)
    
    def _log_statistics(self):
        """Log download statistics"""
        stats = self.get_statistics()
        
        logging.info("Extended details processing completed:")
        logging.info("  Downloads attempted: %d", self.downloaded_count)
        logging.info("  Successful downloads: %d", self.downloaded_count)
        logging.info("  Unique series from cache: %d", self.cached_count)
        logging.info("  Failed downloads: %d", self.failed_count)
        
        if self.downloaded_count > 0:
            logging.info("  Download success rate: %.1f%%", stats["success_rate"])
            
        cache_efficiency = (
            (self.cached_count / (self.cached_count + self.downloaded_count) * 100)
            if (self.cached_count + self.downloaded_count) > 0
            else 0
        )
        logging.info("  Cache efficiency: %.1f%% reused", cache_efficiency)
        
        if self.failed_series:
            logging.info(
                "  Failed series (first 10): %s",
                ", ".join(self.failed_series[:10]),
            )
