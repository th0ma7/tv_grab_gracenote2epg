"""
gracenote2epg.downloader.parallel - Parallel download manager with intelligent progress reporting

Fixed version with dynamic progress intervals and improved download vs cache reporting.
"""

import json
import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Callable

from .base import OptimizedDownloader
from .monitoring import EventDrivenMonitor, EventType, MonitoringMixin
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
                self.max_requests_per_second = min(
                    self.max_requests_per_second * 1.1,
                    15.0  # Max 15 requests/second
                )
            else:
                self.max_requests_per_second = max(
                    self.max_requests_per_second * 0.5,
                    1.0  # Min 1 request/second
                )

            self.min_interval = 1.0 / self.max_requests_per_second


class ParallelDownloadManager(MonitoringMixin):
    """
    Parallel Download Manager with intelligent progress reporting and clean logging
    """

    def __init__(
        self,
        max_workers: int = 4,
        max_retries: int = 3,
        base_delay: float = 0.5,
        enable_rate_limiting: bool = True,
        monitor: Optional[EventDrivenMonitor] = None,
        log_initialization: bool = True
    ):
        """
        Initialize parallel download manager

        Args:
            max_workers: Maximum number of concurrent downloads
            max_retries: Maximum retries per download
            base_delay: Base delay between requests
            enable_rate_limiting: Whether to enable rate limiting
            monitor: EventDrivenMonitor instance for real-time monitoring
            log_initialization: Whether to log initialization message (prevents duplicates)
        """
        super().__init__()

        self.max_workers = max_workers
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.enable_rate_limiting = enable_rate_limiting

        # Statistics
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
        self.stats_lock = threading.Lock()

        # Set monitor
        self.set_monitor(monitor)

        # Worker management
        self.worker_id_counter = 0
        self.worker_id_map = {}
        self.thread_local = threading.local()

        # Rate limiter - conservative for series details
        self.rate_limiter = RateLimiter(max_requests_per_second=2.0)

        # WAF detection
        self.waf_event = threading.Event()
        self.waf_event.set()

        # Only log if requested (prevents duplicate messages)
        if log_initialization:
            logging.info(
                "Parallel download manager initialized: %d workers, monitoring %s",
                max_workers,
                "enabled" if monitor else "disabled"
            )

    def _get_worker_id(self) -> int:
        """Get unique worker ID"""
        thread_id = threading.get_ident()
        if thread_id not in self.worker_id_map:
            self.worker_id_counter += 1
            self.worker_id_map[thread_id] = self.worker_id_counter
        return self.worker_id_map[thread_id]

    def _get_thread_downloader(self) -> OptimizedDownloader:
        """Get or create thread-local downloader with monitoring support"""
        if not hasattr(self.thread_local, 'downloader'):
            downloader = OptimizedDownloader(
                base_delay=self.base_delay,
                min_delay=self.base_delay / 2
            )

            # Connect downloader to monitoring if available
            if self.monitor:
                downloader.set_monitor_callback(self._downloader_event_callback)

            self.thread_local.downloader = downloader

        return self.thread_local.downloader

    def _downloader_event_callback(self, event_type: str, worker_id: int, **data):
        """Callback to receive events from downloader"""
        if event_type == 'waf_detected':
            self.emit_event(EventType.WAF_DETECTED, worker_id, **data)
        elif event_type == 'rate_limit':
            self.emit_event(EventType.RATE_LIMIT_HIT, worker_id, **data)

    def _calculate_progress_interval(self, total: int) -> int:
        """
        Calculate intelligent progress reporting interval

        Args:
            total: Total number of items

        Returns:
            Progress reporting interval (every N items)
        """
        if total <= 0:
            return 1

        # Target: roughly 20 progress messages (5% intervals)
        # But with reasonable bounds for small and large datasets
        if total <= 20:
            # Small datasets: report every item or every 2-5 items
            return max(1, total // 10)  # 10% for very small datasets
        elif total <= 100:
            # Medium datasets: every 5% (every 5-10 items)
            return max(5, total // 20)  # 5% intervals
        elif total <= 1000:
            # Large datasets: every 5% but capped
            return max(10, min(total // 20, 50))  # 5% with reasonable caps
        else:
            # Very large datasets: cap at 50-100 items per progress
            return max(50, min(total // 20, 100))

    def _download_task(self, task) -> Tuple[str, bool, Optional[bytes]]:
        """Execute download task with integrated monitoring"""
        worker_id = self._get_worker_id()
        task_id = getattr(task, 'task_id', str(task))

        # Emit monitoring event
        self.emit_event(EventType.TASK_STARTED, worker_id, task_id)

        # Wait for WAF clearance
        if not self.waf_event.wait(timeout=30):
            logging.warning("Download %s: Timeout waiting for WAF clearance", task_id)
            self.emit_event(EventType.TASK_FAILED, worker_id, task_id, error="WAF timeout")
            return task_id, False, None

        # Apply rate limiting
        if self.enable_rate_limiting:
            self.rate_limiter.wait_if_needed()

        # Count request attempt
        with self.stats_lock:
            self.stats['total_requests'] += 1

        downloader = self._get_thread_downloader()
        start_time = time.time()

        try:
            # Perform download based on task type
            if hasattr(task, 'task_type') and task.task_type == 'guide_block':
                content = downloader.download_with_retry(
                    url=task.url,
                    method="GET",
                    max_retries=self.max_retries,
                    timeout=8
                )
            elif hasattr(task, 'task_type') and task.task_type == 'series_details':
                data_encoded = task.data.encode('utf-8') if task.data else None
                content = downloader.download_with_retry_urllib(
                    url=task.url,
                    data=data_encoded,
                    max_retries=self.max_retries,
                    timeout=6
                )
            else:
                logging.error("Unknown task type: %s", getattr(task, 'task_type', 'unknown'))
                content = None

            duration = time.time() - start_time
            bytes_downloaded = len(content) if content else 0

            if content:
                # Success
                with self.stats_lock:
                    self.stats['successful'] += 1
                    self.stats['bytes_downloaded'] += bytes_downloaded

                self.emit_event(
                    EventType.TASK_COMPLETED, worker_id, task_id,
                    duration=duration, bytes_downloaded=bytes_downloaded
                )

                if self.enable_rate_limiting:
                    self.rate_limiter.adjust_rate(True)

                # Use "Download" instead of "Task" in log messages
                logging.info("Download %s: Success (%d bytes)", task_id, bytes_downloaded)
                return task_id, True, content
            else:
                # Failure
                with self.stats_lock:
                    self.stats['failed'] += 1

                # Check for WAF
                downloader_stats = downloader.get_stats()
                if downloader_stats.get('waf_blocks', 0) > 0:
                    self._handle_waf_detection()

                self.emit_event(EventType.TASK_FAILED, worker_id, task_id,
                              duration=duration, error="No content received")

                if self.enable_rate_limiting:
                    self.rate_limiter.adjust_rate(False)

                logging.warning("Download %s: Failed", task_id)
                return task_id, False, None

        except Exception as e:
            duration = time.time() - start_time

            with self.stats_lock:
                self.stats['failed'] += 1

            self.emit_event(EventType.TASK_FAILED, worker_id, task_id,
                          duration=duration, error=str(e))

            logging.error("Download %s: Exception - %s", task_id, str(e))
            return task_id, False, None

    def _handle_waf_detection(self):
        """Handle WAF detection with event emission"""
        if self.waf_event.is_set():
            self.waf_event.clear()

            with self.stats_lock:
                self.stats['waf_blocks'] += 1

            # Emit WAF event
            self.emit_event(EventType.WAF_DETECTED, 0)

            backoff_time = random.uniform(5, 15)
            logging.warning("WAF detected! Global backoff for %.1f seconds", backoff_time)

            def clear_waf_block():
                time.sleep(backoff_time)
                self.waf_event.set()
                logging.info("WAF backoff completed")

            threading.Thread(target=clear_waf_block, daemon=True).start()

    def download_guide_blocks(
        self,
        tasks: List[Dict[str, Any]],
        cache_manager,
        config_manager,
        refresh_hours: int = 48,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, bytes]:
        """Download guide blocks with intelligent progress reporting"""
        start_time = time.time()
        results = {}
        download_tasks = []

        # Reset statistics for this batch
        self.reset_statistics()

        # Emit batch started event
        self.emit_event(EventType.BATCH_STARTED, 0, None,
                       total_tasks=len(tasks), task_type="guide_blocks")

        # Create progress tracker if monitor available
        progress_tracker = None
        if self.monitor:
            progress_tracker = self.monitor.create_progress_tracker("Guide Blocks", len(tasks))

        # Prepare tasks and separate downloads from cache hits
        for task_info in tasks:
            grid_time = task_info['grid_time']
            filename = task_info['filename']
            url = task_info['url']

            # Check cache
            cached_content = cache_manager.load_guide_block(filename)
            time_from_now = grid_time - time.time()
            needs_refresh = time_from_now < (refresh_hours * 3600)

            if cached_content and not needs_refresh:
                results[filename] = cached_content
                with self.stats_lock:
                    self.stats['cached'] += 1
                if progress_tracker:
                    progress_tracker.increment()
                logging.debug("Using cached: %s", filename)
            else:
                task = DownloadTask(
                    task_id=filename,
                    url=url,
                    task_type='guide_block',
                    priority=int(grid_time),
                    metadata={'grid_time': grid_time}
                )
                download_tasks.append(task)

        # Execute downloads with intelligent progress reporting
        if download_tasks:
            # Calculate intelligent progress interval based on actual download count
            progress_interval = self._calculate_progress_interval(len(download_tasks))

            logging.debug("Guide block progress: reporting every %d downloads (total: %d)",
                        progress_interval, len(download_tasks))

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_task = {
                    executor.submit(self._download_task, task): task
                    for task in download_tasks
                }

                completed = 0
                total = len(download_tasks)

                for future in as_completed(future_to_task):
                    task = future_to_task[future]

                    try:
                        task_id, success, content = future.result(timeout=30)

                        if success and content:
                            try:
                                json.loads(content)  # Validate JSON
                                if cache_manager.save_guide_block(task_id, content):
                                    results[task_id] = content
                                    logging.debug("Saved guide block: %s", task_id)
                            except json.JSONDecodeError:
                                logging.warning("Invalid JSON for block: %s", task_id)

                        completed += 1

                        if progress_tracker:
                            progress_tracker.increment()

                        # Intelligent progress reporting
                        if progress_callback and (completed % progress_interval == 0 or completed == total):
                            progress_callback(completed, total)

                    except Exception as e:
                        logging.error("Error processing download %s: %s", task.task_id, str(e))

        # Update statistics and emit completion
        elapsed = time.time() - start_time
        with self.stats_lock:
            self.stats['total_time'] = elapsed
            self.stats['total_tasks'] = len(tasks)

        self.emit_event(EventType.BATCH_COMPLETED, 0, None,
                       total_time=elapsed, successful_tasks=self.stats['successful'])

        self._log_download_summary("Guide blocks", elapsed)
        return results

    def download_series_details(
        self,
        series_list: List[str],
        cache_manager,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Dict]:
        """Download series details with intelligent progress reporting"""
        start_time = time.time()
        results = {}
        download_tasks = []

        # Emit batch started event
        self.emit_event(EventType.BATCH_STARTED, 0, None,
                       total_tasks=len(series_list), task_type="series_details")

        # Create progress tracker if monitor available
        progress_tracker = None
        if self.monitor:
            progress_tracker = self.monitor.create_progress_tracker("Series Details", len(series_list))

        # Check cache and prepare tasks, separating downloads from cache hits
        for series_id in series_list:
            cached_details = cache_manager.load_series_details(series_id)

            if cached_details:
                results[series_id] = cached_details
                with self.stats_lock:
                    self.stats['cached'] += 1
                if progress_tracker:
                    progress_tracker.increment()
                logging.debug("Using cached series details: %s", series_id)
            else:
                url = "https://tvlistings.gracenote.com/api/program/overviewDetails"
                data = f"programSeriesID={series_id}"

                task = DownloadTask(
                    task_id=series_id,
                    url=url,
                    task_type='series_details',
                    data=data
                )
                download_tasks.append(task)

        # Execute downloads with intelligent progress reporting
        if download_tasks:
            # Calculate intelligent progress interval based on actual download count
            progress_interval = self._calculate_progress_interval(len(download_tasks))

            logging.debug("Series details progress: reporting every %d downloads (total: %d)",
                        progress_interval, len(download_tasks))

            # Max 2 workers for series details to avoid rate limiting
            actual_workers = min(self.max_workers, 2)
            logging.info("Using %d workers for series details (reduced to avoid rate limiting)", actual_workers)

            with ThreadPoolExecutor(max_workers=actual_workers) as executor:
                future_to_task = {
                    executor.submit(self._download_task, task): task
                    for task in download_tasks
                }

                completed = 0
                total = len(download_tasks)

                for future in as_completed(future_to_task):
                    task = future_to_task[future]

                    try:
                        # Check for KeyboardInterrupt with shorter timeout
                        task_id, success, content = future.result(timeout=5)

                        if success and content:
                            try:
                                details = json.loads(content)
                                if cache_manager.save_series_details(task_id, content):
                                    results[task_id] = details
                                    logging.debug("Saved series details: %s", task_id)
                            except json.JSONDecodeError:
                                logging.warning("Invalid JSON for series: %s", task_id)

                        completed += 1

                        if progress_tracker:
                            progress_tracker.increment()

                        # Intelligent progress reporting
                        if progress_callback and (completed % progress_interval == 0 or completed == total):
                            progress_callback(completed, total)

                    except KeyboardInterrupt:
                        logging.info("KeyboardInterrupt caught - cancelling remaining downloads")
                        # Cancel remaining futures
                        for remaining_future in future_to_task:
                            remaining_future.cancel()
                        executor.shutdown(wait=False)
                        raise
                    except Exception as e:
                        logging.error("Error processing series download %s: %s", task.task_id, str(e))

        # Update statistics and emit completion
        elapsed = time.time() - start_time
        with self.stats_lock:
            self.stats['total_time'] = elapsed

        self.emit_event(EventType.BATCH_COMPLETED, 0, None,
                       total_time=elapsed, successful_tasks=self.stats['successful'])

        self._log_download_summary("Series details", elapsed)
        return results

    def _log_download_summary(self, task_type: str, elapsed_time: float):
        """Log download summary with corrected statistics"""
        with self.stats_lock:
            total_tasks = self.stats.get('total_tasks', 0)
            successful = self.stats.get('successful', 0)
            failed = self.stats.get('failed', 0)
            cached = self.stats.get('cached', 0)
            waf_blocks = self.stats.get('waf_blocks', 0)
            bytes_downloaded = self.stats.get('bytes_downloaded', 0)

        # Calculate corrected statistics
        total_processed = successful + failed + cached

        if total_processed > 0:
            # Fix: Use correct denominators for percentage calculations
            success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 100
            cache_rate = (cached / total_processed * 100)

            mb_downloaded = bytes_downloaded / (1024 * 1024)
            speed_mbps = mb_downloaded / elapsed_time if elapsed_time > 0 else 0

            logging.info("%s download completed in %.1f seconds:", task_type, elapsed_time)
            logging.info("  Total items: %d", total_processed)
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

    def get_detailed_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics with monitoring data"""
        with self.stats_lock:
            stats = self.stats.copy()

        # Add derived metrics
        if stats['total_time'] > 0:
            stats['requests_per_second'] = stats.get('total_requests', 0) / stats['total_time']
            if stats['bytes_downloaded'] > 0:
                stats['throughput_mbps'] = (stats['bytes_downloaded'] / (1024 * 1024)) / stats['total_time']
            else:
                stats['throughput_mbps'] = 0
        else:
            stats['requests_per_second'] = 0
            stats['throughput_mbps'] = 0

        # Add corrected success rate
        total_requests = stats.get('total_requests', 0)
        if total_requests > 0:
            stats['success_rate'] = (stats['successful'] / total_requests) * 100
        else:
            stats['success_rate'] = 100

        # Add monitoring stats if available
        if self.monitor:
            monitor_stats = self.monitor.get_statistics()
            stats['realtime_monitoring'] = monitor_stats

        return stats

    def get_statistics(self) -> Dict[str, Any]:
        """Get basic statistics (compatible API)"""
        with self.stats_lock:
            return self.stats.copy()

    def reset_statistics(self):
        """Reset statistics"""
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
        if hasattr(self.thread_local, 'downloader'):
            self.thread_local.downloader.close()


class AdaptiveParallelDownloader:
    """Adaptive parallel downloader that adjusts concurrency based on performance"""

    def __init__(self, initial_workers: int = 2, max_workers: int = 8):
        self.current_workers = initial_workers
        self.max_workers = max_workers
        self.min_workers = 1
        self.performance_history = []
        self.adjustment_interval = 10

        logging.info(
            "Adaptive parallel downloader initialized: %d initial workers (max: %d)",
            initial_workers,
            max_workers
        )

    def adjust_workers(self, success_rate: float, avg_response_time: float):
        """Adjust worker count based on performance"""
        self.performance_history.append({
            'workers': self.current_workers,
            'success_rate': success_rate,
            'response_time': avg_response_time
        })

        if success_rate > 0.95 and avg_response_time < 2.0:
            self.current_workers = min(self.current_workers + 1, self.max_workers)
            logging.info("Performance good, increasing workers to %d", self.current_workers)
        elif success_rate < 0.8 or avg_response_time > 5.0:
            self.current_workers = max(self.current_workers - 1, self.min_workers)
            logging.info("Performance degraded, reducing workers to %d", self.current_workers)

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
