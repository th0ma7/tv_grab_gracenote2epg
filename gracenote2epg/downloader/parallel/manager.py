"""
gracenote2epg.downloader.parallel.manager - Main parallel download manager

Simplified main manager that orchestrates all parallel download components.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable

from ..base import OptimizedDownloader
from ..monitoring import EventDrivenMonitor, EventType, MonitoringMixin
from ...utils import TimeUtils

from .tasks import DownloadTask, create_guide_task, create_series_task, validate_task_result
from .statistics import DownloadStatistics, DetailedStatisticsReporter, ProgressTracker
from .rate_limiting import AdaptiveRateController
from .worker_pool import WorkerPool, AdaptiveWorkerManager


class SimpleProgressCallback:
    """Simple progress callback that passes through to original callback"""

    def __init__(self, task_type: str, original_callback: Optional[Callable] = None):
        self.task_type = task_type
        self.original_callback = original_callback

    def __call__(self, completed: int, total: int):
        # Simply pass through to original callback - let guide.py handle interval logic
        if self.original_callback:
            self.original_callback(completed, total)


class ParallelDownloadManager(MonitoringMixin):
    """
    Simplified Parallel Download Manager with modular components
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
            log_initialization: Whether to log initialization message
        """
        super().__init__()

        # Core configuration
        self.max_workers = max_workers
        self.original_max_workers = max_workers
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.enable_rate_limiting = enable_rate_limiting

        # Initialize components
        self.statistics = DownloadStatistics()
        self.worker_pool = WorkerPool(max_workers, max_workers)
        self.rate_controller = AdaptiveRateController(initial_rate=1.5) if enable_rate_limiting else None
        self.adaptive_manager = AdaptiveWorkerManager(self.worker_pool) if max_workers > 1 else None

        # Set monitor
        self.set_monitor(monitor)

        # Thread-local downloader storage
        self.thread_local_storage = {}

        if log_initialization:
            logging.info(
                "Parallel download manager initialized: %d workers, monitoring %s",
                max_workers,
                "enabled" if monitor else "disabled"
            )

    @property
    def current_workers(self) -> int:
        """Get current worker count"""
        return self.worker_pool.current_workers

    @property
    def consecutive_429s(self) -> int:
        """Get consecutive 429 count from rate controller"""
        if self.rate_controller:
            return self.rate_controller.consecutive_429s
        return 0

    @property
    def worker_reduction_active(self) -> bool:
        """Check if worker reduction is active"""
        return self.current_workers < self.original_max_workers

    def _get_thread_downloader(self) -> OptimizedDownloader:
        """Get or create thread-local downloader"""
        import threading
        thread_id = threading.get_ident()

        if thread_id not in self.thread_local_storage:
            downloader = OptimizedDownloader(
                base_delay=self.base_delay,
                min_delay=self.base_delay / 2
            )

            # Connect to monitoring if available
            if self.monitor:
                downloader.set_monitor_callback(self._downloader_event_callback)

            self.thread_local_storage[thread_id] = downloader

        return self.thread_local_storage[thread_id]

    def _downloader_event_callback(self, event_type: str, worker_id: int, **data):
        """Callback to receive events from downloader"""
        if event_type == 'waf_detected':
            self.statistics.record_waf_block()
            self.emit_event(EventType.WAF_DETECTED, worker_id, **data)
        elif event_type == 'rate_limit':
            self.statistics.record_rate_limit()
            self.emit_event(EventType.RATE_LIMIT_HIT, worker_id, **data)

    def _execute_download_task(self, task: DownloadTask) -> tuple[str, bool, Optional[bytes]]:
        """Execute a single download task with rate limiting and monitoring"""
        worker_id = self.worker_pool._get_worker_id()

        # Emit task started event
        self.emit_event(EventType.TASK_STARTED, worker_id, task.task_id)

        # Apply rate limiting
        if self.rate_controller and not self.rate_controller.before_request():
            logging.warning("Download %s: Rate limiting prevented request", task.task_id)
            self.emit_event(EventType.TASK_FAILED, worker_id, task.task_id, error="Rate limited")
            return task.task_id, False, None

        downloader = self._get_thread_downloader()
        start_time = time.time()

        try:
            # Execute based on task type
            if task.task_type == 'guide_block':
                content = downloader.download_with_retry(
                    url=task.url,
                    method="GET",
                    max_retries=self.max_retries,
                    timeout=8
                )
            elif task.task_type == 'series_details':
                data_encoded = task.data.encode('utf-8') if task.data else None
                content = downloader.download_with_retry_urllib(
                    url=task.url,
                    data=data_encoded,
                    max_retries=self.max_retries,
                    timeout=6
                )
            else:
                logging.error("Unknown task type: %s", task.task_type)
                content = None

            duration = time.time() - start_time

            # Update rate controller
            if self.rate_controller:
                self.rate_controller.after_request(
                    success=content is not None,
                    response_text=content.decode('utf-8', errors='ignore') if content else "",
                    error=None
                )

            if content:
                # Success
                self.statistics.record_success(len(content))

                self.emit_event(
                    EventType.TASK_COMPLETED, worker_id, task.task_id,
                    duration=duration, bytes_downloaded=len(content)
                )

                logging.info("Download %s: Success (%d bytes)", task.task_id, len(content))
                return task.task_id, True, content
            else:
                # Failure
                self.statistics.record_failure()

                self.emit_event(EventType.TASK_FAILED, worker_id, task.task_id,
                              duration=duration, error="No content received")

                logging.warning("Download %s: Failed", task.task_id)
                return task.task_id, False, None

        except Exception as e:
            duration = time.time() - start_time
            error_str = str(e)

            self.statistics.record_failure()

            # Handle specific errors
            if "429" in error_str or "Too Many Requests" in error_str:
                self.statistics.record_rate_limit()
                if self.worker_pool.current_workers > 1:
                    self.worker_pool.reduce_workers_for_rate_limiting()
                    self.statistics.record_worker_reduction()

            # Update rate controller
            if self.rate_controller:
                self.rate_controller.after_request(
                    success=False,
                    error=error_str
                )

            self.emit_event(EventType.TASK_FAILED, worker_id, task.task_id,
                          duration=duration, error=error_str)

            logging.error("Download %s: Exception - %s", task.task_id, error_str)
            return task.task_id, False, None

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
        self.statistics.reset()

        # Emit batch started event
        self.emit_event(EventType.BATCH_STARTED, 0, None,
                       total_tasks=len(tasks), task_type="guide_blocks")

        # Process tasks - separate downloads from cache hits
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
                self.statistics.record_cached()
                logging.debug("Using cached: %s", filename)
            else:
                download_task = create_guide_task(grid_time, filename, url)
                download_tasks.append(download_task)

        # Execute downloads
        if download_tasks:
            download_count = len(download_tasks)
            logging.info("Executing %d guide block downloads with %d workers",
                        download_count, self.current_workers)

            # Create simple pass-through callback
            simple_callback = SimpleProgressCallback(
                task_type="guide blocks",
                original_callback=progress_callback
            )

            download_results = self.worker_pool.execute_tasks(
                tasks=download_tasks,
                task_executor=self._execute_download_task,
                progress_callback=simple_callback
            )

            # Process results
            for task_id, result in download_results.items():
                if result.success and result.content:
                    try:
                        # Validate JSON content
                        json.loads(result.content)
                        if cache_manager.save_guide_block(task_id, result.content):
                            results[task_id] = result.content
                            logging.debug("Saved guide block: %s", task_id)
                    except json.JSONDecodeError:
                        logging.warning("Invalid JSON for block: %s", task_id)

        # Update statistics and emit completion
        elapsed = time.time() - start_time
        self.statistics.update_total_time(elapsed)
        self.statistics.set_total_tasks(len(tasks))

        self.emit_event(EventType.BATCH_COMPLETED, 0, None,
                       total_time=elapsed, successful_tasks=self.statistics.get_stats_copy()['successful'])

        # Log summary
        reporter = DetailedStatisticsReporter(
            self.statistics, self.current_workers, self.original_max_workers,
            self.worker_reduction_active, self.consecutive_429s
        )
        reporter.log_summary("Guide blocks", elapsed)

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

        # Process series list - separate downloads from cache hits
        for series_id in series_list:
            cached_details = cache_manager.load_series_details(series_id)

            if cached_details:
                results[series_id] = cached_details
                self.statistics.record_cached()
                logging.debug("Using cached series details: %s", series_id)
            else:
                data = f"programSeriesID={series_id}"
                download_task = create_series_task(series_id, data)
                download_tasks.append(download_task)

        # Execute downloads with conservative worker count for series
        if download_tasks:
            effective_workers = min(self.current_workers, 2)
            original_workers = self.worker_pool.current_workers
            self.worker_pool.current_workers = effective_workers

            download_count = len(download_tasks)
            logging.info("Executing %d series downloads with %d workers",
                        download_count, effective_workers)

            # Create simple pass-through callback
            simple_callback = SimpleProgressCallback(
                task_type="series details",
                original_callback=progress_callback
            )

            download_results = self.worker_pool.execute_tasks(
                tasks=download_tasks,
                task_executor=self._execute_download_task,
                progress_callback=simple_callback
            )

            # Restore original worker count
            self.worker_pool.current_workers = original_workers

            # Process results
            for task_id, result in download_results.items():
                if result.success and result.content:
                    try:
                        details = json.loads(result.content)
                        if cache_manager.save_series_details(task_id, result.content):
                            results[task_id] = details
                            logging.debug("Saved series details: %s", task_id)
                    except json.JSONDecodeError:
                        logging.warning("Invalid JSON for series: %s", task_id)

        # Update statistics and emit completion
        elapsed = time.time() - start_time
        self.statistics.update_total_time(elapsed)

        self.emit_event(EventType.BATCH_COMPLETED, 0, None,
                       total_time=elapsed, successful_tasks=self.statistics.get_stats_copy()['successful'])

        # Log summary
        reporter = DetailedStatisticsReporter(
            self.statistics, self.current_workers, self.original_max_workers,
            self.worker_reduction_active, self.consecutive_429s
        )
        reporter.log_summary("Series details", elapsed)

        return results

    def get_detailed_statistics(self) -> Dict[str, Any]:
        """Get detailed download statistics for external reporting"""
        reporter = DetailedStatisticsReporter(
            self.statistics, self.current_workers, self.original_max_workers,
            self.worker_reduction_active, self.consecutive_429s
        )
        return reporter.get_detailed_statistics()

    def reset_statistics(self):
        """Reset statistics for new batch"""
        self.statistics.reset()

    def cleanup(self):
        """Cleanup resources with proper shutdown"""
        logging.info("Cleaning up parallel download manager resources")

        # Clean up worker pool
        self.worker_pool.cleanup()

        # Clean up thread-local downloaders
        for downloader in self.thread_local_storage.values():
            try:
                downloader.close()
            except Exception as e:
                logging.warning("Error closing downloader: %s", str(e))

        self.thread_local_storage.clear()

        # Log final statistics if there were rate limit issues
        stats = self.statistics.get_stats_copy()
        if stats.get('rate_limit_hits', 0) > 0:
            logging.info("Session summary: encountered %d rate limit errors, "
                       "performed %d worker adaptations",
                       stats['rate_limit_hits'], stats.get('worker_reductions', 0))

            if self.current_workers < self.original_max_workers:
                logging.info("Final state: using %d/%d workers due to rate limiting",
                           self.current_workers, self.original_max_workers)
