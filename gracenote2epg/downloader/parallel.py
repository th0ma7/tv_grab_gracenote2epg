"""
gracenote2epg.downloader.parallel - Parallel download manager

Provides parallel downloading capabilities for guide blocks and series details
with intelligent concurrency control, rate limiting, and WAF protection.
Moved from gracenote2epg_parallel.py
"""

import json
import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from queue import Queue
from typing import Dict, List, Optional, Tuple, Any, Callable
import urllib.parse

from .base import OptimizedDownloader
from ..utils import TimeUtils


@dataclass
class DownloadTask:
    """Represents a download task for parallel processing"""
    task_id: str
    url: str
    task_type: str  # 'guide_block' or 'series_details'
    priority: int = 0
    data: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RateLimiter:
    """Thread-safe rate limiter for controlling request frequency"""

    def __init__(self, max_requests_per_second: float = 10.0):
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Wait if necessary to respect rate limit"""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_request_time = time.time()

    def adjust_rate(self, success: bool):
        """Dynamically adjust rate based on success/failure"""
        with self.lock:
            if success:
                # Gradually increase rate on success
                self.max_requests_per_second = min(
                    self.max_requests_per_second * 1.1,
                    15.0  # Max 15 requests/second
                )
            else:
                # Reduce rate on failure
                self.max_requests_per_second = max(
                    self.max_requests_per_second * 0.5,
                    1.0  # Min 1 request/second
                )

            self.min_interval = 1.0 / self.max_requests_per_second


class ParallelDownloadManager:
    """Manages parallel downloads with intelligent concurrency control"""

    def __init__(
        self,
        max_workers: int = 4,
        max_retries: int = 3,
        base_delay: float = 0.5,
        enable_rate_limiting: bool = True
    ):
        """
        Initialize parallel download manager

        Args:
            max_workers: Maximum number of concurrent downloads
            max_retries: Maximum retries per download
            base_delay: Base delay between requests
            enable_rate_limiting: Whether to enable rate limiting
        """
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.enable_rate_limiting = enable_rate_limiting

        # Statistics
        self.stats = {
            'total_tasks': 0,
            'total_requests': 0,  # Track actual HTTP requests
            'successful': 0,
            'failed': 0,
            'cached': 0,
            'waf_blocks': 0,
            'total_time': 0,
            'bytes_downloaded': 0
        }
        self.stats_lock = threading.Lock()

        # Rate limiter
        self.rate_limiter = RateLimiter(max_requests_per_second=5.0)

        # Thread-local storage for downloaders
        self.thread_local = threading.local()

        # WAF detection and backoff
        self.waf_event = threading.Event()
        self.waf_event.set()  # Not blocked initially

        logging.info(
            "Parallel download manager initialized: %d workers, rate limiting %s",
            max_workers,
            "enabled" if enable_rate_limiting else "disabled"
        )

    def _get_thread_downloader(self) -> OptimizedDownloader:
        """Get or create a thread-local downloader instance"""
        if not hasattr(self.thread_local, 'downloader'):
            self.thread_local.downloader = OptimizedDownloader(
                base_delay=self.base_delay,
                min_delay=self.base_delay / 2
            )
        return self.thread_local.downloader

    def _download_task(self, task: DownloadTask) -> Tuple[str, bool, Optional[bytes]]:
        """
        Execute a single download task

        Returns:
            Tuple of (task_id, success, content)
        """
        downloader = self._get_thread_downloader()

        # Wait for WAF clearance
        if not self.waf_event.wait(timeout=30):
            logging.warning("Task %s: Timeout waiting for WAF clearance", task.task_id)
            return task.task_id, False, None

        # Apply rate limiting
        if self.enable_rate_limiting:
            self.rate_limiter.wait_if_needed()

        # Count this as a request attempt
        with self.stats_lock:
            if 'total_requests' not in self.stats:
                self.stats['total_requests'] = 0
            self.stats['total_requests'] += 1

        try:
            # Log task start
            logging.debug("Starting download task: %s", task.task_id)

            # Perform download based on task type
            if task.task_type == 'guide_block':
                content = downloader.download_with_retry(
                    url=task.url,
                    method="GET",
                    max_retries=self.max_retries,
                    timeout=8
                )
            elif task.task_type == 'series_details':
                # Series details use POST with urllib method
                data_encoded = task.data.encode('utf-8') if task.data else None
                content = downloader.download_with_retry_urllib(
                    url=task.url,
                    data=data_encoded,
                    max_retries=self.max_retries,
                    timeout=6
                )
            else:
                logging.error("Unknown task type: %s", task.task_type)
                return task.task_id, False, None

            # Check for success
            if content:
                # Update statistics
                with self.stats_lock:
                    self.stats['successful'] += 1
                    self.stats['bytes_downloaded'] += len(content)

                # Adjust rate on success
                if self.enable_rate_limiting:
                    self.rate_limiter.adjust_rate(True)

                logging.info("Task %s: Success (%d bytes)", task.task_id, len(content))
                return task.task_id, True, content
            else:
                # Check for WAF block
                stats = downloader.get_stats()
                if stats['waf_blocks'] > 0:
                    self._handle_waf_detection()

                with self.stats_lock:
                    self.stats['failed'] += 1

                if self.enable_rate_limiting:
                    self.rate_limiter.adjust_rate(False)

                logging.warning("Task %s: Failed", task.task_id)
                return task.task_id, False, None

        except Exception as e:
            logging.error("Task %s: Exception - %s", task.task_id, str(e))
            with self.stats_lock:
                self.stats['failed'] += 1
            return task.task_id, False, None

    def _handle_waf_detection(self):
        """Handle WAF detection with global backoff"""
        if self.waf_event.is_set():
            self.waf_event.clear()

            with self.stats_lock:
                self.stats['waf_blocks'] += 1

            # Global backoff
            backoff_time = random.uniform(5, 15)
            logging.warning("WAF detected! Global backoff for %.1f seconds", backoff_time)

            def clear_waf_block():
                time.sleep(backoff_time)
                self.waf_event.set()
                logging.info("WAF backoff completed, resuming downloads")

            threading.Thread(target=clear_waf_block, daemon=True).start()

    def download_guide_blocks(
        self,
        tasks: List[Dict[str, Any]],
        cache_manager,
        config_manager,
        refresh_hours: int = 48,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, bytes]:
        """
        Download guide blocks in parallel

        Args:
            tasks: List of guide block tasks with grid_time, filename, url
            cache_manager: Cache manager instance
            config_manager: Config manager instance
            refresh_hours: Hours to refresh
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary of successful downloads {filename: content}
        """
        start_time = time.time()
        results = {}
        download_tasks = []

        logging.info(
            "Starting parallel guide block download: %d blocks, %d workers",
            len(tasks),
            self.max_workers
        )

        # Prepare download tasks
        for task_info in tasks:
            grid_time = task_info['grid_time']
            filename = task_info['filename']
            url = task_info['url']

            # Check cache first
            cached_content = cache_manager.load_guide_block(filename)
            time_from_now = grid_time - time.time()
            needs_refresh = time_from_now < (refresh_hours * 3600)

            if cached_content and not needs_refresh:
                # Use cached version
                results[filename] = cached_content
                with self.stats_lock:
                    self.stats['cached'] += 1
                logging.debug("Using cached: %s", filename)
            else:
                # Need to download
                task = DownloadTask(
                    task_id=filename,
                    url=url,
                    task_type='guide_block',
                    priority=int(grid_time),  # Earlier blocks have higher priority
                    metadata={'grid_time': grid_time}
                )
                download_tasks.append(task)

        # Sort tasks by priority (download earlier blocks first)
        download_tasks.sort(key=lambda t: t.priority)

        # Execute parallel downloads
        if download_tasks:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_task = {
                    executor.submit(self._download_task, task): task
                    for task in download_tasks
                }

                # Process completed tasks
                completed = 0
                total = len(download_tasks)

                for future in as_completed(future_to_task):
                    task = future_to_task[future]

                    try:
                        task_id, success, content = future.result(timeout=30)

                        if success and content:
                            # Validate and save
                            try:
                                json.loads(content)  # Validate JSON
                                if cache_manager.save_guide_block(task_id, content):
                                    results[task_id] = content
                                    logging.info("Saved guide block: %s", task_id)
                            except json.JSONDecodeError:
                                logging.warning("Invalid JSON for block: %s", task_id)

                        completed += 1

                        # Progress callback
                        if progress_callback:
                            progress_callback(completed, total)

                    except Exception as e:
                        logging.error("Error processing task %s: %s", task.task_id, str(e))

        # Calculate statistics
        elapsed = time.time() - start_time
        with self.stats_lock:
            self.stats['total_time'] = elapsed

        # Log summary
        self._log_download_summary("Guide blocks", elapsed)

        return results

    def download_series_details(
        self,
        series_list: List[str],
        cache_manager,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Dict]:
        """
        Download series details in parallel

        Args:
            series_list: List of series IDs to download
            cache_manager: Cache manager instance
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary of successful downloads {series_id: details}
        """
        start_time = time.time()
        results = {}
        download_tasks = []

        logging.info(
            "Starting parallel series details download: %d series, %d workers",
            len(series_list),
            self.max_workers
        )

        # Check cache and prepare tasks
        for series_id in series_list:
            # Check cache first
            cached_details = cache_manager.load_series_details(series_id)

            if cached_details:
                results[series_id] = cached_details
                with self.stats_lock:
                    self.stats['cached'] += 1
                logging.debug("Using cached series details: %s", series_id)
            else:
                # Need to download
                url = "https://tvlistings.gracenote.com/api/program/overviewDetails"
                data = f"programSeriesID={series_id}"

                task = DownloadTask(
                    task_id=series_id,
                    url=url,
                    task_type='series_details',
                    data=data
                )
                download_tasks.append(task)

        # Execute parallel downloads
        if download_tasks:
            # Limit workers for series details to avoid overwhelming the API
            actual_workers = min(self.max_workers, 3)  # Max 3 concurrent for series

            with ThreadPoolExecutor(max_workers=actual_workers) as executor:
                # Submit all tasks
                future_to_task = {
                    executor.submit(self._download_task, task): task
                    for task in download_tasks
                }

                # Process completed tasks
                completed = 0
                total = len(download_tasks)

                for future in as_completed(future_to_task):
                    task = future_to_task[future]

                    try:
                        task_id, success, content = future.result(timeout=30)

                        if success and content:
                            # Parse and save
                            try:
                                details = json.loads(content)
                                if cache_manager.save_series_details(task_id, content):
                                    results[task_id] = details
                                    logging.info("Saved series details: %s", task_id)
                            except json.JSONDecodeError:
                                logging.warning("Invalid JSON for series: %s", task_id)

                        completed += 1

                        # Progress callback
                        if progress_callback:
                            progress_callback(completed, total)

                    except Exception as e:
                        logging.error("Error processing series %s: %s", task.task_id, str(e))

        # Calculate statistics
        elapsed = time.time() - start_time
        with self.stats_lock:
            self.stats['total_time'] = elapsed

        # Log summary
        self._log_download_summary("Series details", elapsed)

        return results

    def _log_download_summary(self, task_type: str, elapsed_time: float):
        """Log download summary statistics"""
        with self.stats_lock:
            total = self.stats.get('total_tasks', 0)
            successful = self.stats.get('successful', 0)
            failed = self.stats.get('failed', 0)
            cached = self.stats.get('cached', 0)
            waf_blocks = self.stats.get('waf_blocks', 0)
            bytes_downloaded = self.stats.get('bytes_downloaded', 0)

        if total > 0:
            success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
            cache_rate = (cached / total * 100)

            # Calculate download speed
            mb_downloaded = bytes_downloaded / (1024 * 1024)
            if elapsed_time > 0:
                speed_mbps = mb_downloaded / elapsed_time
            else:
                speed_mbps = 0

            logging.info("%s download completed in %.1f seconds:", task_type, elapsed_time)
            logging.info("  Total items: %d", total)
            logging.info("  Downloaded: %d (%.1f%% success rate)", successful, success_rate)
            logging.info("  From cache: %d (%.1f%% cache hit rate)", cached, cache_rate)
            logging.info("  Failed: %d", failed)

            if waf_blocks > 0:
                logging.info("  WAF blocks encountered: %d", waf_blocks)

            if successful > 0:
                logging.info("  Data downloaded: %.1f MB", mb_downloaded)
                logging.info("  Average speed: %.2f MB/s", speed_mbps)

                if elapsed_time > 0:
                    items_per_second = successful / elapsed_time
                    logging.info("  Processing rate: %.1f items/second", items_per_second)

    def consolidate_downloader_stats(self):
        """Consolidate statistics from all thread-local downloaders"""
        try:
            logging.debug("Consolidating downloader statistics from parallel workers")
        except Exception as e:
            logging.warning("Error consolidating downloader stats: %s", str(e))

    def get_detailed_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics including performance metrics"""
        with self.stats_lock:
            stats = self.stats.copy()

            # Add derived metrics
            if stats['total_time'] > 0:
                # Use total_requests for requests per second (includes failed attempts)
                stats['requests_per_second'] = stats.get('total_requests', 0) / stats['total_time']

                if stats['bytes_downloaded'] > 0:
                    stats['throughput_mbps'] = (stats['bytes_downloaded'] / (1024 * 1024)) / stats['total_time']
                else:
                    stats['throughput_mbps'] = 0
            else:
                stats['requests_per_second'] = 0
                stats['throughput_mbps'] = 0

            # Add efficiency metrics
            total_requests = stats.get('total_requests', 0)
            if total_requests > 0:
                stats['success_rate'] = (stats['successful'] / total_requests) * 100
            else:
                stats['success_rate'] = 100

            return stats

    def get_statistics(self) -> Dict[str, Any]:
        """Get download statistics"""
        with self.stats_lock:
            return self.stats.copy()

    def reset_statistics(self):
        """Reset statistics for new download session"""
        with self.stats_lock:
            self.stats = {
                'total_tasks': 0,
                'total_requests': 0,
                'successful': 0,
                'failed': 0,
                'cached': 0,
                'waf_blocks': 0,
                'total_time': 0,
                'bytes_downloaded': 0
            }

    def cleanup(self):
        """Cleanup resources"""
        # Close all thread-local downloaders
        if hasattr(self.thread_local, 'downloader'):
            self.thread_local.downloader.close()


class AdaptiveParallelDownloader:
    """
    Adaptive parallel downloader that adjusts concurrency based on performance
    """

    def __init__(self, initial_workers: int = 2, max_workers: int = 8):
        """
        Initialize adaptive parallel downloader

        Args:
            initial_workers: Starting number of workers
            max_workers: Maximum number of workers
        """
        self.current_workers = initial_workers
        self.max_workers = max_workers
        self.min_workers = 1

        self.performance_history = []
        self.adjustment_interval = 10  # Adjust after every N tasks

        logging.info(
            "Adaptive parallel downloader initialized: %d initial workers (max: %d)",
            initial_workers,
            max_workers
        )

    def adjust_workers(self, success_rate: float, avg_response_time: float):
        """
        Dynamically adjust number of workers based on performance

        Args:
            success_rate: Recent success rate (0-1)
            avg_response_time: Average response time in seconds
        """
        # Record performance
        self.performance_history.append({
            'workers': self.current_workers,
            'success_rate': success_rate,
            'response_time': avg_response_time
        })

        # Adjust based on performance
        if success_rate > 0.95 and avg_response_time < 2.0:
            # Good performance, try increasing workers
            self.current_workers = min(self.current_workers + 1, self.max_workers)
            logging.info("Performance good, increasing workers to %d", self.current_workers)

        elif success_rate < 0.8 or avg_response_time > 5.0:
            # Poor performance, reduce workers
            self.current_workers = max(self.current_workers - 1, self.min_workers)
            logging.info("Performance degraded, reducing workers to %d", self.current_workers)

        # Keep history size manageable
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-50:]

    def get_optimal_workers(self) -> int:
        """Get current optimal number of workers"""
        return self.current_workers

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.performance_history:
            return {}

        recent = self.performance_history[-10:] if len(self.performance_history) >= 10 else self.performance_history

        return {
            'current_workers': self.current_workers,
            'avg_success_rate': sum(p['success_rate'] for p in recent) / len(recent),
            'avg_response_time': sum(p['response_time'] for p in recent) / len(recent),
            'total_adjustments': len(self.performance_history)
        }
