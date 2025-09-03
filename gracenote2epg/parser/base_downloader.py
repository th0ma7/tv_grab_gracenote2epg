"""
Base downloader class for common download functionality
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

class BaseDownloader(ABC):
    """Abstract base class for all downloaders"""
    
    def __init__(self, downloader, cache_manager):
        self.downloader = downloader
        self.cache_manager = cache_manager
        self.downloaded_count = 0
        self.cached_count = 0
        self.failed_count = 0
        
    @abstractmethod
    def download(self, *args, **kwargs) -> bool:
        """Main download method to be implemented by subclasses"""
        pass
    
    @abstractmethod
    def build_url(self, *args, **kwargs) -> str:
        """Build download URL"""
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get download statistics"""
        return {
            "downloaded": self.downloaded_count,
            "cached": self.cached_count,
            "failed": self.failed_count,
            "total": self.downloaded_count + self.cached_count + self.failed_count,
            "success_rate": self._calculate_success_rate()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate success rate percentage"""
        total = self.downloaded_count + self.cached_count + self.failed_count
        if total == 0:
            return 100.0
        success = self.downloaded_count + self.cached_count
        return (success / total) * 100
