"""
gracenote2epg.downloader.parallel.worker_pool - Precise worker pool management

Enhanced worker pool with accurate ThreadPoolExecutor tracking and proper state management.
Eliminates worker count inconsistencies and provides precise monitoring integration.
"""

import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Callable, Any, Tuple

from .tasks import DownloadTask, DownloadResult


class WorkerState:
    """Track individual worker state and performance with enhanced metrics"""

    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.is_busy = False
        self.current_task: Optional[str] = None
        self.task_start_time: Optional[float] = None
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.bytes_downloaded = 0
        self.total_duration = 0.0
        self.last_activity = time.time()
        self.thread_id: Optional[int] = None  # Track actual thread ID

    def start_task(self, task_id: str, thread_id: Optional[int] = None):
        """Mark worker as starting a task"""
        self.is_busy = True
        self.current_task = task_id
        self.task_start_time = time.time()
        self.last_activity = time.time()
        if thread_id:
            self.thread_id = thread_id

    def complete_task(self, success: bool, bytes_downloaded: int = 0, duration: float = 0.0):
        """Mark task as completed"""
        if success:
            self.tasks_completed += 1
            self.bytes_downloaded += bytes_downloaded
        else:
            self.tasks_failed += 1

        self.total_duration += duration
        self.reset_task()

    def reset_task(self):
        """Reset current task state"""
        self.is_busy = False
        self.current_task = None
        self.task_start_time = None
        self.last_activity = time.time()
        # Keep thread_id for tracking

    def get_current_task_duration(self) -> float:
        """Get duration of current task"""
        if self.task_start_time is None:
            return 0.0
        return time.time() - self.task_start_time

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive worker performance metrics"""
        total_tasks = self.tasks_completed + self.tasks_failed
        success_rate = (self.tasks_completed / total_tasks * 100) if total_tasks > 0 else 0

        avg_duration = (self.total_duration / self.tasks_completed) if self.tasks_completed > 0 else 0

        return {
            'worker_id': self.worker_id,
            'thread_id': self.thread_id,
            'total_tasks': total_tasks,
            'completed': self.tasks_completed,
            'failed': self.tasks_failed,
            'success_rate': success_rate,
            'bytes_downloaded': self.bytes_downloaded,
            'average_duration': avg_duration,
            'is_busy': self.is_busy,
            'current_task': self.current_task,
            'current_task_duration': self.get_current_task_duration(),
            'last_activity': self.last_activity
        }


class PreciseWorkerPool:
    """
    Precise worker pool with accurate ThreadPoolExecutor tracking

    Key improvements:
    - Actual ThreadPoolExecutor size matches reported worker count
    - Proper worker state tracking with thread ID correlation
    - Dynamic pool recreation when worker count changes
    - Accurate monitoring integration
    - Python 3.8+ compatibility
    """

    def __init__(self, initial_workers: int = 4, max_workers: int = 10):
        self.initial_workers = initial_workers
        self.max_workers = max_workers
        self.min_workers = 1

        # Worker state tracking - accurate correlation
        self.worker_states: Dict[int, WorkerState] = {}
        self.worker_id_counter = 0
        self.thread_to_worker_id: Dict[int, int] = {}
        self.stats_lock = threading.Lock()

        # Current pool state
        self._current_workers = initial_workers
        self._executor: Optional[ThreadPoolExecutor] = None
        self._executor_lock = threading.Lock()
        self._active_futures = set()  # Track active futures for proper cleanup

        # Performance tracking
        self.performance_history = []
        self.last_adjustment = 0

        # Monitoring callback
        self.monitor_callback: Optional[Callable] = None

        # Initialize worker states for initial workers
        self._initialize_worker_states(initial_workers)

        logging.debug("PreciseWorkerPool initialized: %d workers (max: %d)",
                     initial_workers, max_workers)

    def _initialize_worker_states(self, count: int):
        """Initialize worker states for given count"""
        with self.stats_lock:
            # Clear existing states
            self.worker_states.clear()
            self.thread_to_worker_id.clear()
            self.worker_id_counter = 0

            # Create new worker states (starting from ID 1)
            for i in range(count):
                self.worker_id_counter += 1
                worker_id = self.worker_id_counter
                self.worker_states[worker_id] = WorkerState(worker_id)

    @property
    def current_workers(self) -> int:
        """Get current number of workers (matches actual ThreadPoolExecutor size)"""
        return self._current_workers

    def set_monitor_callback(self, callback: Callable):
        """Set monitoring callback to emit events"""
        self.monitor_callback = callback
        logging.debug("Monitor callback set for PreciseWorkerPool")

    def _emit_worker_event(self, event_type: str, **data):
        """Emit worker-related event to monitor"""
        if self.monitor_callback:
            try:
                self.monitor_callback(event_type, 0, **data)
                logging.debug("Emitted worker event: %s", event_type)
            except Exception as e:
                logging.debug("Error in monitor callback: %s", e)

    def _get_or_create_executor(self) -> ThreadPoolExecutor:
        """Get current executor or create new one if worker count changed"""
        with self._executor_lock:
            if self._executor is None:
                logging.debug("Creating ThreadPoolExecutor with %d workers", self._current_workers)
                self._executor = ThreadPoolExecutor(max_workers=self._current_workers)
            return self._executor

    def _recreate_executor_if_needed(self, new_worker_count: int):
        """Recreate executor if worker count has changed"""
        with self._executor_lock:
            if new_worker_count != self._current_workers:
                old_count = self._current_workers

                # Shutdown old executor if it exists
                if self._executor is not None:
                    logging.debug("Shutting down executor (workers: %d -> %d)",
                                 old_count, new_worker_count)

                    # Cancel any pending futures
                    for future in self._active_futures:
                        future.cancel()
                    self._active_futures.clear()

                    # Shutdown without timeout parameter for Python 3.8 compatibility
                    self._executor.shutdown(wait=False)

                # Create new executor with correct worker count
                self._current_workers = new_worker_count
                self._executor = ThreadPoolExecutor(max_workers=new_worker_count)

                # Reinitialize worker states to match
                self._initialize_worker_states(new_worker_count)

                # Emit worker adjustment event
                self._emit_worker_event('worker_count_changed',
                                       old_count=old_count,
                                       new_count=new_worker_count,
                                       reason="pool recreation")

                logging.info("ThreadPoolExecutor recreated: %d workers (was %d)",
                           new_worker_count, old_count)

    def _get_worker_id(self) -> int:
        """Get worker ID for current thread with accurate tracking"""
        thread_id = threading.get_ident()

        with self.stats_lock:
            if thread_id not in self.thread_to_worker_id:
                # Find available worker state or create new one
                available_worker = None
                for worker_state in self.worker_states.values():
                    if not worker_state.is_busy and worker_state.thread_id is None:
                        available_worker = worker_state
                        break

                if available_worker is None:
                    # Create new worker state (shouldn't happen in normal operation)
                    self.worker_id_counter += 1
                    worker_id = self.worker_id_counter
                    self.worker_states[worker_id] = WorkerState(worker_id)
                    available_worker = self.worker_states[worker_id]
                    logging.debug("Created additional worker %d for thread %s", worker_id, thread_id)

                self.thread_to_worker_id[thread_id] = available_worker.worker_id
                available_worker.thread_id = thread_id

            return self.thread_to_worker_id[thread_id]

    def _get_worker_state(self) -> WorkerState:
        """Get worker state for current thread"""
        worker_id = self._get_worker_id()
        return self.worker_states[worker_id]

    def adjust_worker_count(self, target_workers: int, reason: str = "adaptive"):
        """Adjust the number of workers with proper executor recreation"""
        target_workers = max(self.min_workers, min(self.max_workers, target_workers))

        if target_workers != self._current_workers:
            logging.info("Adjusting worker count: %d -> %d (%s)",
                        self._current_workers, target_workers, reason)

            # Recreate executor with new worker count
            self._recreate_executor_if_needed(target_workers)
            self.last_adjustment = time.time()

    def execute_tasks(self,
                     tasks: List[DownloadTask],
                     task_executor: Callable[[DownloadTask], Tuple[str, bool, Optional[bytes]]],
                     progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, DownloadResult]:
        """
        Execute tasks with precise worker tracking and proper ThreadPoolExecutor management

        Args:
            tasks: List of tasks to execute
            task_executor: Function to execute individual tasks
            progress_callback: Optional progress callback function

        Returns:
            Dictionary of task_id -> DownloadResult
        """
        results = {}

        if not tasks:
            return results

        # Get actual executor (creates if needed)
        executor = self._get_or_create_executor()

        # Log actual vs reported worker count for verification
        actual_max_workers = executor._max_workers
        if actual_max_workers != self._current_workers:
            logging.warning("ThreadPoolExecutor mismatch: reported %d, actual %d",
                           self._current_workers, actual_max_workers)

        logging.info("Executing %d tasks with %d workers (ThreadPoolExecutor max: %d)",
                    len(tasks), self._current_workers, actual_max_workers)

        # Emit execution start event
        self._emit_worker_event('batch_execution_started',
                               effective_workers=self._current_workers,
                               total_tasks=len(tasks),
                               actual_executor_workers=actual_max_workers)

        # Submit all tasks
        future_to_task = {}
        for task in tasks:
            future = executor.submit(self._execute_with_tracking, task, task_executor)
            future_to_task[future] = task
            self._active_futures.add(future)

        completed = 0
        total = len(tasks)

        try:
            for future in as_completed(future_to_task):
                self._active_futures.discard(future)
                task = future_to_task[future]

                try:
                    result = future.result(timeout=30)
                    if result:
                        results[result.task_id] = result

                    completed += 1

                    # Progress reporting
                    if progress_callback:
                        progress_callback(completed, total)

                    # Periodic performance tracking
                    if completed % 20 == 0:
                        self._record_performance_sample()

                except Exception as e:
                    logging.error("Error processing task %s: %s", task.task_id, str(e))

                    # Create failed result
                    failed_result = DownloadResult(
                        task_id=task.task_id,
                        success=False,
                        error=str(e)
                    )
                    results[task.task_id] = failed_result
                    completed += 1

                    # Progress reporting for failed tasks too
                    if progress_callback:
                        progress_callback(completed, total)

        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt received - shutting down gracefully...")

            # Cancel remaining futures
            for remaining_future in self._active_futures:
                remaining_future.cancel()
            self._active_futures.clear()

            # Re-raise to propagate the interrupt
            raise

        finally:
            # Clear active futures set
            self._active_futures.clear()

        # Emit execution completed event
        self._emit_worker_event('batch_execution_completed',
                               completed_tasks=len(results),
                               current_workers=self._current_workers)

        return results

    def _execute_with_tracking(self,
                              task: DownloadTask,
                              task_executor: Callable[[DownloadTask], Tuple[str, bool, Optional[bytes]]]) -> Optional[DownloadResult]:
        """Execute task with precise worker state tracking"""
        worker_state = self._get_worker_state()
        current_thread_id = threading.get_ident()

        worker_state.start_task(task.task_id, current_thread_id)
        start_time = time.time()

        try:
            # Execute the actual task
            task_id, success, content = task_executor(task)
            duration = time.time() - start_time

            # Create result
            result = DownloadResult(
                task_id=task_id,
                success=success,
                content=content,
                duration=duration
            )

            # Update worker state
            worker_state.complete_task(
                success=success,
                bytes_downloaded=result.bytes_downloaded,
                duration=duration
            )

            return result

        except Exception as e:
            duration = time.time() - start_time

            # Create failed result
            result = DownloadResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                duration=duration
            )

            worker_state.complete_task(success=False, duration=duration)
            return result

    def _record_performance_sample(self):
        """Record performance sample for adaptive decisions"""
        with self.stats_lock:
            total_completed = sum(ws.tasks_completed for ws in self.worker_states.values())
            total_failed = sum(ws.tasks_failed for ws in self.worker_states.values())
            total_tasks = total_completed + total_failed

            if total_tasks > 0:
                success_rate = total_completed / total_tasks
                avg_duration = sum(ws.total_duration for ws in self.worker_states.values()) / total_completed if total_completed > 0 else 0
                total_bytes = sum(ws.bytes_downloaded for ws in self.worker_states.values())

                sample = {
                    'timestamp': time.time(),
                    'workers': self._current_workers,
                    'success_rate': success_rate,
                    'avg_response_time': avg_duration,
                    'total_bytes': total_bytes
                }

                self.performance_history.append(sample)

                # Keep history bounded
                if len(self.performance_history) > 100:
                    self.performance_history = self.performance_history[-50:]

    def get_worker_statistics(self) -> Dict[str, Any]:
        """Get comprehensive and accurate worker statistics"""
        with self.stats_lock:
            total_completed = sum(ws.tasks_completed for ws in self.worker_states.values())
            total_failed = sum(ws.tasks_failed for ws in self.worker_states.values())
            total_bytes = sum(ws.bytes_downloaded for ws in self.worker_states.values())
            active_workers = sum(1 for ws in self.worker_states.values() if ws.is_busy)

            worker_details = [ws.get_performance_metrics() for ws in self.worker_states.values()]

            # Get actual executor information
            actual_executor_workers = 0
            if self._executor:
                actual_executor_workers = self._executor._max_workers

            return {
                'reported_workers': self._current_workers,
                'actual_executor_workers': actual_executor_workers,
                'initial_workers': self.initial_workers,
                'max_workers': self.max_workers,
                'active_workers': active_workers,
                'total_completed': total_completed,
                'total_failed': total_failed,
                'total_bytes': total_bytes,
                'worker_details': worker_details,
                'last_adjustment': self.last_adjustment,
                'executor_exists': self._executor is not None,
                'worker_count_consistent': self._current_workers == actual_executor_workers
            }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for adaptive decisions"""
        if not self.performance_history:
            return {
                'status': 'no_data',
                'current_workers': self._current_workers
            }

        recent_samples = self.performance_history[-5:] if len(self.performance_history) >= 5 else self.performance_history

        avg_success_rate = sum(s['success_rate'] for s in recent_samples) / len(recent_samples)
        avg_response_time = sum(s['avg_response_time'] for s in recent_samples) / len(recent_samples)

        return {
            'status': 'active',
            'current_workers': self._current_workers,
            'samples_count': len(self.performance_history),
            'avg_success_rate': avg_success_rate,
            'avg_response_time': avg_response_time,
            'last_adjustment': self.last_adjustment
        }

    def cleanup(self):
        """Clean up worker pool resources with proper executor shutdown"""
        logging.debug("Cleaning up PreciseWorkerPool")

        # Cancel active futures first
        with self._executor_lock:
            for future in self._active_futures:
                future.cancel()
            self._active_futures.clear()

        # Shutdown executor properly with Python version compatibility
        with self._executor_lock:
            if self._executor is not None:
                try:
                    # Check Python version for timeout parameter support
                    python_version = sys.version_info
                    if python_version >= (3, 9):
                        # Python 3.9+ supports timeout parameter
                        try:
                            self._executor.shutdown(wait=True, timeout=5)
                        except TypeError:
                            # Fallback if somehow timeout isn't supported
                            self._executor.shutdown(wait=True)
                    else:
                        # Python 3.8 and earlier - no timeout parameter
                        self._executor.shutdown(wait=True)
                    logging.debug("ThreadPoolExecutor shutdown completed")
                except Exception as e:
                    logging.warning("Error during executor shutdown: %s", e)
                finally:
                    self._executor = None

        # Reset worker states
        with self.stats_lock:
            for worker_state in self.worker_states.values():
                worker_state.reset_task()

            # Log final statistics
            if self.worker_states:
                total_tasks = sum(ws.tasks_completed + ws.tasks_failed for ws in self.worker_states.values())
                if total_tasks > 0:
                    logging.debug("Worker pool completed %d total tasks", total_tasks)


class AdaptiveWorkerManager:
    """
    Enhanced adaptive worker manager with task-type awareness

    Manages worker count adjustments based on performance metrics and task characteristics.
    """

    def __init__(self, worker_pool: PreciseWorkerPool, task_type: str = "unknown"):
        self.worker_pool = worker_pool
        self.task_type = task_type
        self.performance_samples = []
        self.max_samples = 50
        self.last_evaluation = 0
        self.evaluation_interval = 20  # seconds

        # Task-specific thresholds
        self.thresholds = self._get_task_specific_thresholds(task_type)

    def _get_task_specific_thresholds(self, task_type: str) -> Dict[str, Any]:
        """Get performance thresholds specific to task type"""
        if task_type == 'guide_block':
            return {
                'good_success_rate': 0.95,
                'poor_success_rate': 0.85,
                'good_response_time': 3.0,
                'poor_response_time': 8.0,
                'good_throughput': 100000,  # 100KB/s
                'aggressive_adjustment': True
            }
        elif task_type == 'series_details':
            return {
                'good_success_rate': 0.90,
                'poor_success_rate': 0.75,
                'good_response_time': 2.0,
                'poor_response_time': 5.0,
                'good_throughput': 10000,   # 10KB/s
                'aggressive_adjustment': False
            }
        else:
            # Default conservative thresholds
            return {
                'good_success_rate': 0.90,
                'poor_success_rate': 0.80,
                'good_response_time': 2.5,
                'poor_response_time': 6.0,
                'good_throughput': 50000,   # 50KB/s
                'aggressive_adjustment': False
            }

    def record_performance(self, success_rate: float, avg_response_time: float,
                          throughput: float = 0.0, error_rate: float = 0.0):
        """
        Record performance metrics for adaptive decision making

        Args:
            success_rate: Percentage of successful requests (0-1.0)
            avg_response_time: Average response time in seconds
            throughput: Bytes processed per second
            error_rate: Error rate (0-1.0)
        """
        sample = {
            'timestamp': time.time(),
            'task_type': self.task_type,
            'workers': self.worker_pool.current_workers,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'throughput': throughput,
            'error_rate': error_rate
        }

        self.performance_samples.append(sample)

        # Keep history bounded
        if len(self.performance_samples) > self.max_samples:
            self.performance_samples = self.performance_samples[-self.max_samples//2:]

        # Trigger evaluation
        self._evaluate_performance()

    def _evaluate_performance(self):
        """Evaluate recent performance and adjust workers if needed"""
        current_time = time.time()

        # Check if enough time has passed since last adjustment
        if current_time - self.last_evaluation < self.evaluation_interval:
            return

        # Need minimum samples to make decisions
        if len(self.performance_samples) < 3:
            return

        # Analyze recent performance (last 5 samples or all if less)
        recent_samples = self.performance_samples[-5:]

        avg_success_rate = sum(s['success_rate'] for s in recent_samples) / len(recent_samples)
        avg_response_time = sum(s['avg_response_time'] for s in recent_samples) / len(recent_samples)
        avg_throughput = sum(s['throughput'] for s in recent_samples) / len(recent_samples)
        avg_error_rate = sum(s['error_rate'] for s in recent_samples) / len(recent_samples)

        # Decision logic using task-specific thresholds
        thresholds = self.thresholds

        should_increase = (
            avg_success_rate >= thresholds['good_success_rate'] and
            avg_response_time <= thresholds['good_response_time'] and
            avg_throughput >= thresholds['good_throughput'] and
            avg_error_rate <= 0.05
        )

        should_decrease = (
            avg_success_rate <= thresholds['poor_success_rate'] or
            avg_response_time >= thresholds['poor_response_time'] or
            avg_error_rate >= 0.15
        )

        if should_increase and not should_decrease:
            self._adjust_workers(1, f"good performance ({self.task_type})")
        elif should_decrease and not should_increase:
            # More aggressive decrease for series downloads
            decrease_amount = 2 if (self.task_type == 'series_details' and
                                  thresholds['aggressive_adjustment']) else 1
            self._adjust_workers(-decrease_amount, f"poor performance ({self.task_type})")

        self.last_evaluation = current_time

    def _adjust_workers(self, change: int, reason: str):
        """Adjust worker count by specified amount"""
        current_workers = self.worker_pool.current_workers
        new_workers = max(self.worker_pool.min_workers,
                         min(self.worker_pool.max_workers, current_workers + change))

        if new_workers != current_workers:
            self.worker_pool.adjust_worker_count(new_workers, f"adaptive ({reason})")

    def get_evaluation_summary(self) -> Dict[str, Any]:
        """Get summary of adaptive evaluation with task-specific information"""
        if not self.performance_samples:
            return {
                'status': 'no_data',
                'task_type': self.task_type,
                'current_workers': self.worker_pool.current_workers
            }

        recent = self.performance_samples[-5:] if len(self.performance_samples) >= 5 else self.performance_samples

        return {
            'status': 'active',
            'task_type': self.task_type,
            'samples_count': len(self.performance_samples),
            'current_workers': self.worker_pool.current_workers,
            'thresholds': self.thresholds,
            'avg_success_rate': sum(s['success_rate'] for s in recent) / len(recent),
            'avg_response_time': sum(s['avg_response_time'] for s in recent) / len(recent),
            'avg_throughput': sum(s['throughput'] for s in recent) / len(recent),
            'last_evaluation': self.last_evaluation
        }


# Clean API aliases
WorkerPool = PreciseWorkerPool
