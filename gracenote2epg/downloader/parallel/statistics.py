"""
gracenote2epg.downloader.parallel.statistics - Download statistics tracking

Thread-safe statistics collection and reporting for parallel downloads.
"""

import logging
import threading
import time
from typing import Dict, Any, Optional


class DownloadStatistics:
    """Thread-safe download statistics tracker"""
    
    def __init__(self):
        self.stats = {
            'total_tasks': 0,
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'cached': 0,
            'waf_blocks': 0,
            'rate_limit_hits': 0,
            'worker_reductions': 0,
            'total_time': 0,
            'bytes_downloaded': 0
        }
        self.lock = threading.RLock()
        self.start_time = time.time()
        
    def increment(self, key: str, value: int = 1):
        """Thread-safe increment of a statistic"""
        with self.lock:
            if key in self.stats:
                self.stats[key] += value
            else:
                self.stats[key] = value
                
    def add_bytes(self, bytes_count: int):
        """Add downloaded bytes to statistics"""
        with self.lock:
            self.stats['bytes_downloaded'] += bytes_count
            
    def record_success(self, bytes_downloaded: int = 0):
        """Record a successful download"""
        with self.lock:
            self.stats['successful'] += 1
            self.stats['total_requests'] += 1
            if bytes_downloaded > 0:
                self.stats['bytes_downloaded'] += bytes_downloaded
                
    def record_failure(self):
        """Record a failed download"""
        with self.lock:
            self.stats['failed'] += 1
            self.stats['total_requests'] += 1
            
    def record_cached(self):
        """Record a cache hit"""
        with self.lock:
            self.stats['cached'] += 1
            
    def record_waf_block(self):
        """Record a WAF block incident"""
        with self.lock:
            self.stats['waf_blocks'] += 1
            
    def record_rate_limit(self):
        """Record a rate limit hit"""
        with self.lock:
            self.stats['rate_limit_hits'] += 1
            
    def record_worker_reduction(self):
        """Record a worker reduction event"""
        with self.lock:
            self.stats['worker_reductions'] += 1
            
    def set_total_tasks(self, count: int):
        """Set total task count"""
        with self.lock:
            self.stats['total_tasks'] = count
            
    def update_total_time(self, elapsed_time: float):
        """Update total execution time"""
        with self.lock:
            self.stats['total_time'] = elapsed_time
            
    def get_stats_copy(self) -> Dict[str, Any]:
        """Get thread-safe copy of current statistics"""
        with self.lock:
            return self.stats.copy()
            
    def reset(self):
        """Reset all statistics"""
        with self.lock:
            for key in self.stats:
                self.stats[key] = 0
            self.start_time = time.time()


class PerformanceCalculator:
    """Calculate performance metrics from statistics"""
    
    @staticmethod
    def calculate_success_rate(stats: Dict[str, Any]) -> float:
        """Calculate success rate excluding cached items"""
        successful = stats.get('successful', 0)
        failed = stats.get('failed', 0)
        total_attempted = successful + failed
        
        if total_attempted == 0:
            return 100.0
        return (successful / total_attempted) * 100.0
        
    @staticmethod
    def calculate_cache_hit_rate(stats: Dict[str, Any]) -> float:
        """Calculate cache hit rate"""
        cached = stats.get('cached', 0)
        successful = stats.get('successful', 0)
        failed = stats.get('failed', 0)
        total_processed = cached + successful + failed
        
        if total_processed == 0:
            return 0.0
        return (cached / total_processed) * 100.0
        
    @staticmethod
    def calculate_throughput_mbps(stats: Dict[str, Any]) -> float:
        """Calculate throughput in MB/s"""
        bytes_downloaded = stats.get('bytes_downloaded', 0)
        total_time = stats.get('total_time', 0)
        
        if total_time == 0 or bytes_downloaded == 0:
            return 0.0
        
        mb_downloaded = bytes_downloaded / (1024 * 1024)
        return mb_downloaded / total_time
        
    @staticmethod
    def calculate_requests_per_second(stats: Dict[str, Any]) -> float:
        """Calculate requests per second"""
        total_requests = stats.get('total_requests', 0)
        total_time = stats.get('total_time', 0)
        
        if total_time == 0:
            return 0.0
        return total_requests / total_time
        
    @staticmethod
    def calculate_items_per_second(stats: Dict[str, Any]) -> float:
        """Calculate successful items per second"""
        successful = stats.get('successful', 0)
        total_time = stats.get('total_time', 0)
        
        if total_time == 0:
            return 0.0
        return successful / total_time


class DetailedStatisticsReporter:
    """Generate detailed statistics reports"""
    
    def __init__(self, statistics: DownloadStatistics, 
                 current_workers: int, original_workers: int,
                 worker_reduction_active: bool = False,
                 consecutive_429s: int = 0):
        self.statistics = statistics
        self.current_workers = current_workers
        self.original_workers = original_workers
        self.worker_reduction_active = worker_reduction_active
        self.consecutive_429s = consecutive_429s
        
    def get_detailed_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics with calculated metrics"""
        stats_copy = self.statistics.get_stats_copy()
        
        # Calculate derived metrics
        success_rate = PerformanceCalculator.calculate_success_rate(stats_copy)
        cache_hit_rate = PerformanceCalculator.calculate_cache_hit_rate(stats_copy)
        throughput_mbps = PerformanceCalculator.calculate_throughput_mbps(stats_copy)
        requests_per_second = PerformanceCalculator.calculate_requests_per_second(stats_copy)
        
        # Return comprehensive report
        return {
            # Raw statistics
            'total_requests': stats_copy.get('total_requests', 0),
            'successful': stats_copy.get('successful', 0),
            'failed': stats_copy.get('failed', 0),
            'cached': stats_copy.get('cached', 0),
            'waf_blocks': stats_copy.get('waf_blocks', 0),
            'rate_limit_hits': stats_copy.get('rate_limit_hits', 0),
            'worker_reductions': stats_copy.get('worker_reductions', 0),
            'bytes_downloaded': stats_copy.get('bytes_downloaded', 0),
            'total_time': stats_copy.get('total_time', 0),
            
            # Calculated metrics
            'success_rate': success_rate,
            'cache_hit_rate': cache_hit_rate,
            'requests_per_second': requests_per_second,
            'throughput_mbps': throughput_mbps,
            
            # Worker status
            'current_workers': self.current_workers,
            'original_workers': self.original_workers,
            'worker_reduction_active': self.worker_reduction_active,
            'consecutive_429s': self.consecutive_429s
        }
        
    def log_summary(self, task_type: str, elapsed_time: float):
        """Log comprehensive download summary"""
        stats = self.statistics.get_stats_copy()
        
        total_tasks = stats.get('total_tasks', 0)
        successful = stats.get('successful', 0)
        failed = stats.get('failed', 0)
        cached = stats.get('cached', 0)
        waf_blocks = stats.get('waf_blocks', 0)
        rate_limit_hits = stats.get('rate_limit_hits', 0)
        worker_reductions = stats.get('worker_reductions', 0)
        bytes_downloaded = stats.get('bytes_downloaded', 0)

        # Calculate metrics
        total_processed = successful + failed + cached
        success_rate = PerformanceCalculator.calculate_success_rate(stats)
        cache_rate = PerformanceCalculator.calculate_cache_hit_rate(stats)
        throughput = PerformanceCalculator.calculate_throughput_mbps(stats)
        items_per_sec = PerformanceCalculator.calculate_items_per_second(stats)

        if total_processed > 0:
            logging.info("%s download completed in %.1f seconds:", task_type, elapsed_time)
            logging.info("  Total items: %d", total_processed)
            logging.info("  Downloaded: %d (%.1f%% success rate)", successful, success_rate)
            logging.info("  From cache: %d (%.1f%% cache hit rate)", cached, cache_rate)
            logging.info("  Failed: %d", failed)

            # Enhanced error reporting
            if rate_limit_hits > 0:
                logging.info("  Rate limit hits: %d (HTTP 429 errors)", rate_limit_hits)

            if worker_reductions > 0:
                logging.info("  Worker adaptations: %d (auto-reduced due to rate limiting)", worker_reductions)
                logging.info("  Final worker count: %d (started with %d)",
                           self.current_workers, self.original_workers)

            if waf_blocks > 0:
                logging.info("  WAF blocks encountered: %d", waf_blocks)

            if successful > 0:
                mb_downloaded = bytes_downloaded / (1024 * 1024)
                logging.info("  Data downloaded: %.1f MB", mb_downloaded)
                logging.info("  Average speed: %.2f MB/s", throughput)
                logging.info("  Processing rate: %.1f items/second", items_per_sec)


class ProgressTracker:
    """Track download progress with intelligent reporting intervals"""
    
    def __init__(self, total_items: int, task_type: str = "download"):
        self.total_items = total_items
        self.task_type = task_type
        self.completed = 0
        self.start_time = time.time()
        self.last_report_time = 0
        self.progress_interval = self._calculate_progress_interval()
        
    def _calculate_progress_interval(self) -> int:
        """Calculate intelligent progress reporting interval"""
        if self.total_items <= 0:
            return 1
            
        if self.task_type == "series":
            # Series downloads: Very frequent progress
            if self.total_items <= 50:
                return max(1, self.total_items // 10)  # Every 10%
            else:
                return max(5, min(self.total_items // 20, 10))  # Every 5% with caps
        else:
            # Guide downloads: Less frequent but reasonable
            if self.total_items <= 20:
                return max(1, self.total_items // 4)  # Every 25%
            else:
                return max(5, min(self.total_items // 10, 50))  # Every 10% with caps
                
    def increment(self):
        """Increment progress counter"""
        self.completed += 1
        
    def should_report(self) -> bool:
        """Check if progress should be reported now"""
        return (self.completed % self.progress_interval == 0 or 
                self.completed == self.total_items)
        
    def get_progress_info(self) -> Dict[str, Any]:
        """Get current progress information"""
        if self.total_items == 0:
            return {'completed': 0, 'total': 0, 'percentage': 0.0}
            
        percentage = (self.completed / self.total_items) * 100
        elapsed = time.time() - self.start_time
        
        return {
            'completed': self.completed,
            'total': self.total_items,
            'percentage': percentage,
            'elapsed_time': elapsed,
            'items_per_second': self.completed / elapsed if elapsed > 0 else 0
        }
