"""
gracenote2epg.downloader.parallel.manager - Unified parallel download manager

Unified manager with consistent worker strategies and true adaptive behavior.
Eliminates worker count inconsistencies and implements proper strategy separation.
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
from .adaptive import WorkerStrategy, AdaptiveStrategy


class SimpleProgressCallback:
    """Simple progress callback that passes through to original callback"""

    def __init__(self, task_type: str, original_callback: Optional[Callable] = None):
        self.task_type = task_type
        self.original_callback = original_callback

    def __call__(self, completed: int, total: int):
        if self.original_callback:
            self.original_callback(completed, total)


class UnifiedDownloadManager(MonitoringMixin):
    """
    Unified Download Manager with consistent worker strategies and true adaptive behavior

    Key improvements:
    - Separate worker strategies for guide vs series downloads
    - True adaptive behavior with proper ThreadPoolExecutor management
    - Consistent monitoring and statistics across all download types
    - Clean API without legacy compatibility issues
    """

    def __init__(
        self,
        max_workers: int = 4,
        max_retries: int = 3,
        base_delay: float = 0.5,
        enable_rate_limiting: bool = True,
        enable_adaptive: bool = True,
        worker_strategy: str = "balanced",
        monitor: Optional[EventDrivenMonitor] = None
    ):
        """
        Initialize unified download manager

        Args:
            max_workers: Maximum number of concurrent workers
            max_retries: Maximum retries per download
            base_delay: Base delay between requests
            enable_rate_limiting: Enable adaptive rate limiting
            enable_adaptive: Enable adaptive worker adjustment
            worker_strategy: Worker strategy ("conservative", "balanced", "aggressive")
            monitor: EventDrivenMonitor instance for real-time monitoring
        """
        super().__init__()

        # Core configuration
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_adaptive = enable_adaptive

        # Initialize adaptive strategy
        self.adaptive_strategy = AdaptiveStrategy(
            strategy_name=worker_strategy,
            max_workers=max_workers,
            enable_adaptive=enable_adaptive
        )

        # Initialize components
        self.statistics = DownloadStatistics()
        self.rate_controller = AdaptiveRateController(initial_rate=1.5) if enable_rate_limiting else None

        # Set monitor
        self.set_monitor(monitor)

        # Connect rate controller to adaptive strategy for worker reduction
        if self.rate_controller:
            self.rate_controller.set_worker_reduction_callback(self._handle_worker_reduction)

        # Thread-local downloader storage
        self.thread_local_storage = {}

        # Current active pools for different task types
        self.active_pools: Dict[str, WorkerPool] = {}

        logging.info(
            "Unified download manager initialized: %d max workers, strategy '%s', adaptive %s, monitoring %s",
            max_workers, worker_strategy,
            "enabled" if enable_adaptive else "disabled",
            "enabled" if monitor else "disabled"
        )

    def _handle_worker_reduction(self, reason: str):
        """Handle worker reduction triggered by rate controller"""
        logging.warning("Rate controller triggered worker reduction: %s", reason)

        # Apply reduction to adaptive strategy
        if self.enable_adaptive:
            self.adaptive_strategy.handle_rate_limit_event(reason)

        # Force immediate adjustment for all active pools
        reduction_factor = 0.5 if reason in ["rate_limit_429", "server_overload"] else 0.3

        for task_type, pool in self.active_pools.items():
            current_workers = pool.current_workers
            new_workers = max(1, int(current_workers * reduction_factor))

            if new_workers != current_workers:
                pool.adjust_worker_count(new_workers, f"rate controller ({reason})")
                logging.warning("Reduced %s workers: %d -> %d", task_type, current_workers, new_workers)

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

    def _create_worker_pool(self, task_type: str) -> WorkerPool:
        """Create worker pool with appropriate strategy for task type"""
        strategy = self.adaptive_strategy.get_worker_strategy(task_type)

        # Create new pool with strategy-specific configuration
        pool = WorkerPool(
            initial_workers=strategy.initial_workers,
            max_workers=strategy.max_workers
        )

        # Connect to monitoring if available
        if self.monitor:
            pool.set_monitor_callback(self._worker_pool_event_callback)

        # Store for cleanup and tracking
        self.active_pools[task_type] = pool

        logging.info("Created %s worker pool: %d workers (max: %d)",
                    task_type, strategy.initial_workers, strategy.max_workers)

        return pool

    def _worker_pool_event_callback(self, event_type: str, worker_id: int, **data):
        """Callback to receive events from worker pool"""
        if event_type == 'worker_count_changed':
            old_count = data.get('old_count', 0)
            new_count = data.get('new_count', 0)
            reason = data.get('reason', 'unknown')

            # Update monitoring with new worker count
            if self.monitor:
                with self.monitor.stats_lock:
                    # Ensure we have worker states up to new_count
                    for i in range(1, new_count + 1):
                        if i not in self.monitor.worker_states:
                            from ..monitoring import WorkerState
                            self.monitor.worker_states[i] = WorkerState(worker_id=i)

                    # Update current worker count in stats
                    self.monitor.stats.current_worker_count = new_count

    def _execute_download_task(self, task: DownloadTask) -> tuple[str, bool, Optional[bytes]]:
        """Execute a single download task with rate limiting and monitoring"""
        # Get worker pool for this task type
        if task.task_type not in self.active_pools:
            self._create_worker_pool(task.task_type)

        pool = self.active_pools[task.task_type]
        worker_id = pool._get_worker_id()

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
            # Execute based on task type with strategy-specific configuration
            strategy = self.adaptive_strategy.get_worker_strategy(task.task_type)

            if task.task_type == 'guide_block':
                content = downloader.download_with_retry(
                    url=task.url,
                    method="GET",
                    max_retries=self.max_retries,
                    timeout=strategy.timeout
                )
            elif task.task_type == 'series_details':
                data_encoded = task.data.encode('utf-8') if task.data else None
                content = downloader.download_with_retry_urllib(
                    url=task.url,
                    data=data_encoded,
                    max_retries=self.max_retries,
                    timeout=strategy.timeout
                )
            else:
                logging.error("Unknown task type: %s", task.task_type)
                content = None

            duration = time.time() - start_time

            # Update rate controller with detailed response info
            if self.rate_controller:
                response_text = ""
                status_code = None

                if content:
                    try:
                        response_text = content.decode('utf-8', errors='ignore')[:1000]
                    except:
                        response_text = ""

                self.rate_controller.after_request(
                    success=content is not None,
                    response_text=response_text,
                    status_code=status_code,
                    error=None
                )

            if content:
                # Success - record adaptive metrics
                self.statistics.record_success(len(content))

                if self.enable_adaptive:
                    self.adaptive_strategy.record_performance(
                        task_type=task.task_type,
                        success=True,
                        response_time=duration,
                        bytes_downloaded=len(content)
                    )

                self.emit_event(
                    EventType.TASK_COMPLETED, worker_id, task.task_id,
                    duration=duration, bytes_downloaded=len(content)
                )

                logging.debug("Download %s: Success (%d bytes)", task.task_id, len(content))
                return task.task_id, True, content
            else:
                # Failure
                self.statistics.record_failure()

                if self.enable_adaptive:
                    self.adaptive_strategy.record_performance(
                        task_type=task.task_type,
                        success=False,
                        response_time=duration
                    )

                self.emit_event(EventType.TASK_FAILED, worker_id, task.task_id,
                              duration=duration, error="No content received")

                logging.warning("Download %s: Failed", task.task_id)
                return task.task_id, False, None

        except Exception as e:
            duration = time.time() - start_time
            error_str = str(e)

            self.statistics.record_failure()

            # Extract status code from error if available
            status_code = None
            if "429" in error_str:
                status_code = 429
            elif "403" in error_str:
                status_code = 403
            elif "502" in error_str:
                status_code = 502
            elif "503" in error_str:
                status_code = 503
            elif "504" in error_str:
                status_code = 504

            # Update rate controller with error details
            if self.rate_controller:
                self.rate_controller.after_request(
                    success=False,
                    response_text="",
                    status_code=status_code,
                    error=error_str
                )

            # Record adaptive metrics for failures
            if self.enable_adaptive:
                self.adaptive_strategy.record_performance(
                    task_type=task.task_type,
                    success=False,
                    response_time=duration,
                    error=error_str
                )

            # Additional statistics for specific errors
            if status_code == 429 or "Too Many Requests" in error_str:
                self.statistics.record_rate_limit()
                logging.warning("Download %s: Rate limited (429)", task.task_id)

            self.emit_event(EventType.TASK_FAILED, worker_id, task.task_id,
                          duration=duration, error=error_str, status_code=status_code)

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
        """Download guide blocks with unified worker strategy"""
        start_time = time.time()
        results = {}
        download_tasks = []

        # Reset statistics for this batch
        self.statistics.reset()

        # Process tasks - separate downloads from cache hits
        cached_count = 0
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
                if self.monitor:
                    self.monitor.stats.cached_tasks += 1
                cached_count += 1
                logging.debug("Using cached: %s", filename)
            else:
                download_task = create_guide_task(grid_time, filename, url)
                download_tasks.append(download_task)

        # Emit batch started event
        self.emit_event(EventType.BATCH_STARTED, 0, None,
               total_tasks=len(tasks),
               cached_tasks=cached_count,
               task_type="guide_blocks")

        # Execute downloads with unified strategy
        if download_tasks:
            # Get worker strategy for guide blocks
            strategy = self.adaptive_strategy.get_worker_strategy("guide_block")

            # Create or get worker pool for guide blocks
            if "guide_block" not in self.active_pools:
                self.active_pools["guide_block"] = self._create_worker_pool("guide_block")

            pool = self.active_pools["guide_block"]

            # Apply strategy-specific rate limiting
            if self.rate_controller:
                self.rate_controller.rate_limiter.max_requests_per_second = strategy.rate_limit
                self.rate_controller.rate_limiter.min_interval = 1.0 / strategy.rate_limit

            logging.info("Executing %d guide block downloads with %d workers (strategy: %s)",
                        len(download_tasks), strategy.current_workers, self.adaptive_strategy.strategy_name)

            # Create simple pass-through callback
            simple_callback = SimpleProgressCallback(
                task_type="guide blocks",
                original_callback=progress_callback
            )

            download_results = pool.execute_tasks(
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

        # Try rate recovery after successful batch
        if self.rate_controller:
            self.rate_controller.try_recover_rate()

        # Log summary with unified strategy reporting
        self._log_task_summary("Guide blocks", elapsed, "guide_block")

        return results

    def download_series_details(
        self,
        series_list: List[str],
        cache_manager,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Dict]:
        """Download series details with dedicated worker strategy"""
        start_time = time.time()
        results = {}
        download_tasks = []

        # Emit batch started event
        self.emit_event(EventType.BATCH_STARTED, 0, None,
                       total_tasks=len(series_list), task_type="series_details")

        # Process series list - separate downloads from cache hits
        cached_count = 0
        for series_id in series_list:
            cached_details = cache_manager.load_series_details(series_id)

            # Check if cached details are valid and not empty
            if cached_details and isinstance(cached_details, dict) and len(cached_details) > 0:
                # Additional validation - check for essential keys
                if any(key in cached_details for key in ['seriesDescription', 'seriesGenres', 'overviewTab', 'upcomingEpisodeTab']):
                    results[series_id] = cached_details
                    self.statistics.record_cached()
                    cached_count += 1
                    logging.debug("Using cached series details: %s", series_id)
                else:
                    logging.debug("Cached series %s exists but is empty/invalid, will re-download", series_id)
                    data = f"programSeriesID={series_id}"
                    download_task = create_series_task(series_id, data)
                    download_tasks.append(download_task)
            else:
                logging.debug("No valid cache for series %s, will download", series_id)
                data = f"programSeriesID={series_id}"
                download_task = create_series_task(series_id, data)
                download_tasks.append(download_task)

        # Execute downloads with dedicated series strategy
        if download_tasks:
            # Get worker strategy for series details
            strategy = self.adaptive_strategy.get_worker_strategy("series_details")

            # Create or get worker pool for series details
            if "series_details" not in self.active_pools:
                self.active_pools["series_details"] = self._create_worker_pool("series_details")

            pool = self.active_pools["series_details"]

            # Apply strategy-specific rate limiting
            if self.rate_controller:
                original_rate = self.rate_controller.rate_limiter.max_requests_per_second
                self.rate_controller.rate_limiter.max_requests_per_second = strategy.rate_limit
                self.rate_controller.rate_limiter.min_interval = 1.0 / strategy.rate_limit
                logging.info("Applied series rate limiting: %.1f req/s", strategy.rate_limit)

            logging.info("Executing %d series downloads with %d workers (strategy: %s)",
                        len(download_tasks), strategy.current_workers, self.adaptive_strategy.strategy_name)

            # Create simple pass-through callback
            simple_callback = SimpleProgressCallback(
                task_type="series details",
                original_callback=progress_callback
            )

            download_results = pool.execute_tasks(
                tasks=download_tasks,
                task_executor=self._execute_download_task,
                progress_callback=simple_callback
            )

            # Restore original rate limiting if needed
            if self.rate_controller and 'original_rate' in locals():
                self.rate_controller.rate_limiter.max_requests_per_second = original_rate
                self.rate_controller.rate_limiter.min_interval = 1.0 / original_rate

            # Process results with explicit cache saving
            for task_id, result in download_results.items():
                if result.success and result.content:
                    try:
                        details = json.loads(result.content)
                        # Force cache save and verify
                        save_success = cache_manager.save_series_details(task_id, result.content)
                        if save_success:
                            results[task_id] = details
                            logging.debug("Saved series details to cache: %s", task_id)
                        else:
                            logging.warning("Failed to save series details to cache: %s", task_id)
                            # Still include in results even if cache save failed
                            results[task_id] = details
                    except json.JSONDecodeError:
                        logging.warning("Invalid JSON for series: %s", task_id)
                    except Exception as e:
                        logging.warning("Error processing series %s: %s", task_id, str(e))

        # Update statistics and emit completion
        elapsed = time.time() - start_time
        self.statistics.update_total_time(elapsed)

        self.emit_event(EventType.BATCH_COMPLETED, 0, None,
                       total_time=elapsed, successful_tasks=self.statistics.get_stats_copy()['successful'])

        # Try rate recovery after successful batch
        if self.rate_controller:
            self.rate_controller.try_recover_rate()

        # Log summary with unified strategy reporting
        self._log_task_summary("Series details", elapsed, "series_details")

        # Enhanced cache verification logging
        logging.info("Series details cache verification:")
        if download_tasks:
            successful_downloads = len([r for r in download_results.values() if r.success])
            logging.info("  Downloaded and cached: %d series", successful_downloads)
        else:
            logging.info("  Downloaded and cached: 0 series (all from cache)")
        logging.info("  From cache: %d series", cached_count)
        logging.info("  Total available: %d series", len(results))

        return results

    def _log_task_summary(self, task_name: str, elapsed_time: float, task_type: str):
        """Log task summary with strategy information"""
        # Get current strategy and pool info
        strategy = self.adaptive_strategy.get_worker_strategy(task_type)
        pool = self.active_pools.get(task_type)

        current_workers = pool.current_workers if pool else strategy.current_workers

        reporter = DetailedStatisticsReporter(
            self.statistics,
            current_workers,
            strategy.max_workers,
            current_workers < strategy.max_workers,  # worker_reduction_active
            self.consecutive_429s
        )

        # Enhanced summary with strategy info
        logging.info("%s completed (strategy: %s):", task_name, self.adaptive_strategy.strategy_name)
        logging.info("  Workers: %d/%d (adaptive: %s)",
                    current_workers, strategy.max_workers,
                    "enabled" if self.enable_adaptive else "disabled")
        logging.info("  Rate limit: %.1f req/s", strategy.rate_limit)

        reporter.log_summary(task_name, elapsed_time)

    @property
    def current_workers(self) -> int:
        """Get current total worker count across all pools"""
        return sum(pool.current_workers for pool in self.active_pools.values())

    @property
    def consecutive_429s(self) -> int:
        """Get consecutive 429 count from rate controller"""
        if self.rate_controller:
            return self.rate_controller.consecutive_429s
        return 0

    def get_detailed_statistics(self) -> Dict[str, Any]:
        """Get detailed download statistics for external reporting"""
        # Get base statistics
        reporter = DetailedStatisticsReporter(
            self.statistics,
            self.current_workers,
            self.max_workers,
            self.current_workers < self.max_workers,
            self.consecutive_429s
        )
        base_stats = reporter.get_detailed_statistics()

        # Add strategy information
        base_stats.update({
            'worker_strategy': self.adaptive_strategy.get_strategy_info(),
            'active_pools': {
                task_type: {
                    'current_workers': pool.current_workers,
                    'max_workers': pool.max_workers,
                    'statistics': pool.get_worker_statistics()
                }
                for task_type, pool in self.active_pools.items()
            }
        })

        # Add rate controller statistics if available
        if self.rate_controller:
            rate_stats = self.rate_controller.get_comprehensive_stats()
            base_stats.update({
                'rate_controller': rate_stats
            })

        # Add adaptive strategy statistics if available
        if self.enable_adaptive:
            adaptive_stats = self.adaptive_strategy.get_performance_summary()
            base_stats.update({
                'adaptive_strategy': adaptive_stats
            })

        return base_stats

    def reset_statistics(self):
        """Reset statistics for new batch"""
        self.statistics.reset()
        if self.enable_adaptive:
            self.adaptive_strategy.reset_performance_history()

    def cleanup(self):
        """Cleanup resources with proper shutdown"""
        logging.info("Cleaning up unified download manager resources")

        # Clean up all active worker pools
        for task_type, pool in self.active_pools.items():
            logging.debug("Cleaning up %s worker pool", task_type)
            pool.cleanup()

        self.active_pools.clear()

        # Clean up thread-local downloaders
        for downloader in self.thread_local_storage.values():
            try:
                downloader.close()
            except Exception as e:
                logging.warning("Error closing downloader: %s", str(e))

        self.thread_local_storage.clear()

        # Log final adaptive strategy summary
        if self.enable_adaptive:
            summary = self.adaptive_strategy.get_performance_summary()
            logging.info("Adaptive strategy final summary: %s", summary.get('performance_trend', 'unknown'))

        # Log final statistics if there were rate limit issues
        stats = self.statistics.get_stats_copy()
        if stats.get('rate_limit_hits', 0) > 0:
            logging.info("Session summary: encountered %d rate limit errors, "
                       "performed %d worker adaptations",
                       stats['rate_limit_hits'], stats.get('worker_reductions', 0))

            if self.current_workers < self.max_workers:
                logging.info("Final state: adaptive worker reduction active")


# Clean API alias without legacy compatibility
ParallelDownloadManager = UnifiedDownloadManager
