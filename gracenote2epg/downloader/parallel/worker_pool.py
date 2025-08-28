"""
gracenote2epg.downloader.parallel.worker_pool - Worker pool management

Thread pool management with adaptive concurrency and worker state tracking.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Callable, Any, Tuple

from .tasks import DownloadTask, DownloadResult


class WorkerState:
    """Track individual worker state and performance"""

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

    def start_task(self, task_id: str):
        """Mark worker as starting a task"""
        self.is_busy = True
        self.current_task = task_id
        self.task_start_time = time.time()
        self.last_activity = time.time()

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

    def get_current_task_duration(self) -> float:
        """Get duration of current task"""
        if self.task_start_time is None:
            return 0.0
        return time.time() - self.task_start_time

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get worker performance metrics"""
        total_tasks = self.tasks_completed + self.tasks_failed
        success_rate = (self.tasks_completed / total_tasks * 100) if total_tasks > 0 else 0

        avg_duration = (self.total_duration / self.tasks_completed) if self.tasks_completed > 0 else 0

        return {
            'worker_id': self.worker_id,
            'total_tasks': total_tasks,
            'completed': self.tasks_completed,
            'failed': self.tasks_failed,
            'success_rate': success_rate,
            'bytes_downloaded': self.bytes_downloaded,
            'average_duration': avg_duration,
            'is_busy': self.is_busy,
            'current_task': self.current_task,
            'current_task_duration': self.get_current_task_duration()
        }


class WorkerPool:
    """Manage thread pool with adaptive worker count and state tracking"""

    def __init__(self, initial_workers: int = 4, max_workers: int = 10):
        self.initial_workers = initial_workers
        self.max_workers = max_workers
        self.current_workers = initial_workers
        self.min_workers = 1

        # Worker state tracking
        self.worker_states: Dict[int, WorkerState] = {}
        self.worker_id_counter = 0
        self.worker_id_map = {}
        self.thread_local = threading.local()
        self.stats_lock = threading.Lock()

        # Shutdown control
        self.shutdown_event = threading.Event()

        # Performance tracking
        self.performance_history = []
        self.last_adjustment = 0

    def _get_worker_id(self) -> int:
        """Get unique worker ID for current thread"""
        thread_id = threading.get_ident()
        if thread_id not in self.worker_id_map:
            with self.stats_lock:
                self.worker_id_counter += 1
                self.worker_id_map[thread_id] = self.worker_id_counter
                self.worker_states[self.worker_id_counter] = WorkerState(self.worker_id_counter)
        return self.worker_id_map[thread_id]

    def _get_worker_state(self) -> WorkerState:
        """Get worker state for current thread"""
        worker_id = self._get_worker_id()
        return self.worker_states[worker_id]

    def adjust_worker_count(self, target_workers: int, reason: str = "adaptive"):
        """Adjust the number of workers"""
        target_workers = max(self.min_workers, min(self.max_workers, target_workers))

        if target_workers != self.current_workers:
            old_workers = self.current_workers
            self.current_workers = target_workers
            self.last_adjustment = time.time()

            logging.info("Worker count adjusted from %d to %d (%s)",
                        old_workers, target_workers, reason)

    def reduce_workers_for_rate_limiting(self):
        """Reduce workers due to rate limiting"""
        if self.current_workers > 1:
            new_count = max(1, self.current_workers // 2)
            self.adjust_worker_count(new_count, "rate limiting")

    def try_increase_workers(self):
        """Try to increase workers if performance allows"""
        current_time = time.time()

        # Only adjust if enough time has passed
        if current_time - self.last_adjustment < 30:
            return

        # Check if we can increase
        if self.current_workers < self.max_workers:
            # Simple heuristic: increase if we haven't had adjustments recently
            new_count = min(self.max_workers, self.current_workers + 1)
            self.adjust_worker_count(new_count, "performance recovery")

    def execute_tasks(self,
                     tasks: List[DownloadTask],
                     task_executor: Callable[[DownloadTask], Tuple[str, bool, Optional[bytes]]],
                     progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, DownloadResult]:
        """
        Execute tasks using thread pool with adaptive worker management

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

        # Use current worker count, not initial
        effective_workers = min(self.current_workers, len(tasks))

        with ThreadPoolExecutor(max_workers=effective_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._execute_with_tracking, task, task_executor): task
                for task in tasks
            }

            completed = 0
            total = len(tasks)

            try:
                for future in as_completed(future_to_task):
                    if self.shutdown_event.is_set():
                        logging.info("Shutdown requested, cancelling remaining downloads")
                        break

                    task = future_to_task[future]

                    try:
                        result = future.result(timeout=30)
                        if result:
                            results[result.task_id] = result

                        completed += 1

                        # Progress reporting - call callback for every completion
                        # Let the callback decide if it should report or not
                        if progress_callback:
                            progress_callback(completed, total)

                        # Periodic worker adjustment check
                        if completed % 20 == 0:
                            self.try_increase_workers()

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
                self.shutdown_event.set()

                # Cancel remaining futures
                for remaining_future in future_to_task:
                    remaining_future.cancel()

                executor.shutdown(wait=False)
                raise

        return results

    def _execute_with_tracking(self,
                              task: DownloadTask,
                              task_executor: Callable[[DownloadTask], Tuple[str, bool, Optional[bytes]]]) -> Optional[DownloadResult]:
        """Execute task with worker state tracking"""
        worker_state = self._get_worker_state()
        worker_state.start_task(task.task_id)

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

    def get_worker_statistics(self) -> Dict[str, Any]:
        """Get comprehensive worker statistics"""
        with self.stats_lock:
            total_completed = sum(ws.tasks_completed for ws in self.worker_states.values())
            total_failed = sum(ws.tasks_failed for ws in self.worker_states.values())
            total_bytes = sum(ws.bytes_downloaded for ws in self.worker_states.values())
            active_workers = sum(1 for ws in self.worker_states.values() if ws.is_busy)

            worker_details = [ws.get_performance_metrics() for ws in self.worker_states.values()]

            return {
                'current_workers': self.current_workers,
                'initial_workers': self.initial_workers,
                'max_workers': self.max_workers,
                'active_workers': active_workers,
                'total_completed': total_completed,
                'total_failed': total_failed,
                'total_bytes': total_bytes,
                'worker_details': worker_details,
                'last_adjustment': self.last_adjustment
            }

    def cleanup(self):
        """Clean up worker pool resources"""
        self.shutdown_event.set()

        # Reset worker states
        with self.stats_lock:
            for worker_state in self.worker_states.values():
                worker_state.reset_task()


class AdaptiveWorkerManager:
    """Manage worker count adaptively based on performance"""

    def __init__(self, worker_pool: WorkerPool):
        self.worker_pool = worker_pool
        self.performance_samples = []
        self.max_samples = 50
        self.last_evaluation = 0
        self.evaluation_interval = 30  # seconds

    def record_performance(self, success_rate: float, avg_response_time: float, throughput: float):
        """Record performance sample"""
        sample = {
            'timestamp': time.time(),
            'workers': self.worker_pool.current_workers,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'throughput': throughput
        }

        self.performance_samples.append(sample)

        # Keep only recent samples
        if len(self.performance_samples) > self.max_samples:
            self.performance_samples = self.performance_samples[-self.max_samples:]

    def should_adjust_workers(self) -> bool:
        """Check if worker count should be adjusted"""
        current_time = time.time()

        # Only evaluate periodically
        if current_time - self.last_evaluation < self.evaluation_interval:
            return False

        # Need enough samples
        if len(self.performance_samples) < 5:
            return False

        self.last_evaluation = current_time
        return True

    def evaluate_and_adjust(self):
        """Evaluate performance and adjust worker count if needed"""
        if not self.should_adjust_workers():
            return

        recent_samples = self.performance_samples[-10:]  # Last 10 samples

        avg_success_rate = sum(s['success_rate'] for s in recent_samples) / len(recent_samples)
        avg_response_time = sum(s['avg_response_time'] for s in recent_samples) / len(recent_samples)
        avg_throughput = sum(s['throughput'] for s in recent_samples) / len(recent_samples)

        current_workers = self.worker_pool.current_workers

        # Decision logic
        if avg_success_rate > 95 and avg_response_time < 2.0 and avg_throughput > 1.0:
            # Good performance - try increasing workers
            if current_workers < self.worker_pool.max_workers:
                new_count = min(self.worker_pool.max_workers, current_workers + 1)
                self.worker_pool.adjust_worker_count(new_count, "performance good")

        elif avg_success_rate < 80 or avg_response_time > 5.0:
            # Poor performance - reduce workers
            if current_workers > self.worker_pool.min_workers:
                new_count = max(self.worker_pool.min_workers, current_workers - 1)
                self.worker_pool.adjust_worker_count(new_count, "performance degraded")

    def get_evaluation_summary(self) -> Dict[str, Any]:
        """Get summary of adaptive evaluation"""
        if not self.performance_samples:
            return {'status': 'no_data'}

        recent = self.performance_samples[-5:] if len(self.performance_samples) >= 5 else self.performance_samples

        return {
            'status': 'active',
            'samples_count': len(self.performance_samples),
            'current_workers': self.worker_pool.current_workers,
            'avg_success_rate': sum(s['success_rate'] for s in recent) / len(recent),
            'avg_response_time': sum(s['avg_response_time'] for s in recent) / len(recent),
            'avg_throughput': sum(s['throughput'] for s in recent) / len(recent),
            'last_evaluation': self.last_evaluation
        }
