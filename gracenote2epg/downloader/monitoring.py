"""
gracenote2epg.downloader.monitoring - Real-time event-driven monitoring

Clean event-driven monitoring system without backward compatibility.
Direct communication between workers and monitor via events.
"""

import json
import logging
import threading
import time
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import Queue, Empty
from typing import Dict, List, Optional, Deque, Any, Callable
import sys


class EventType(Enum):
    """Monitoring event types"""
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    WORKER_IDLE = "worker_idle"
    WORKER_BUSY = "worker_busy"
    BATCH_STARTED = "batch_started"
    BATCH_COMPLETED = "batch_completed"
    RATE_LIMIT_HIT = "rate_limit_hit"
    WAF_DETECTED = "waf_detected"
    WORKER_COUNT_CHANGED = "worker_count_changed"


@dataclass
class MonitoringEvent:
    """Thread-safe monitoring event"""
    event_type: EventType
    timestamp: float
    worker_id: int
    task_id: Optional[str] = None
    data: Dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


@dataclass
class WorkerState:
    """Real-time worker state"""
    worker_id: int
    is_busy: bool = False
    current_task: Optional[str] = None
    task_start_time: Optional[float] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    bytes_downloaded: int = 0
    last_activity: float = 0

    def reset_task(self):
        """Reset current task state"""
        self.is_busy = False
        self.current_task = None
        self.task_start_time = None
        self.last_activity = time.time()


@dataclass
class RealTimeStats:
    """Thread-safe real-time statistics"""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cached_tasks: int = 0
    active_workers: int = 0
    current_worker_count: int = 0
    bytes_downloaded: int = 0
    requests_per_second: float = 0.0
    avg_response_time: float = 0.0
    waf_blocks: int = 0
    rate_limits: int = 0
    start_time: float = 0.0

    def get_completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks + self.cached_tasks) / self.total_tasks * 100


class EventDrivenMonitor:
    """Event-driven monitor with direct worker-monitor communication"""

    def __init__(self,
                 enable_console: bool = True,
                 enable_web_api: bool = False,
                 web_port: int = 9989,
                 metrics_file: Optional[Path] = None):
        """
        Initialize event-driven monitor

        Args:
            enable_console: Real-time console display
            enable_web_api: Web API for external monitoring
            web_port: Web API port (default: 9989)
            metrics_file: File to save metrics
        """
        self.enable_console = enable_console
        self.enable_web_api = enable_web_api
        self.web_port = web_port
        self.metrics_file = metrics_file

        # Thread-safe communication
        self.event_queue = Queue()
        self.stats_lock = threading.RLock()

        # Real-time state
        self.stats = RealTimeStats()
        self.worker_states: Dict[int, WorkerState] = {}
        self.recent_events: Deque[MonitoringEvent] = deque(maxlen=1000)
        self.response_times: Deque[float] = deque(maxlen=100)
        self.throughput_history: Deque[tuple] = deque(maxlen=60)  # (timestamp, mbps)

        # Processing threads
        self.event_processor = None
        self.console_updater = None
        self.web_server = None
        self.stop_event = threading.Event()

        # Event callbacks
        self.event_callbacks: Dict[EventType, List[Callable]] = defaultdict(list)

        # Named progress bars
        self.progress_bars: Dict[str, Dict] = {}

        logging.info("Event-driven monitor initialized (console: %s, web: %s, port: %d)",
                    enable_console, enable_web_api, web_port)

    def start(self):
        """Start monitoring"""
        self.stats.start_time = time.time()
        self.stop_event.clear()

        # Event processing thread
        self.event_processor = threading.Thread(
            target=self._process_events,
            daemon=True,
            name="EventProcessor"
        )
        self.event_processor.start()

        # Console display thread
        if self.enable_console:
            self.console_updater = threading.Thread(
                target=self._update_console,
                daemon=True,
                name="ConsoleUpdater"
            )
            self.console_updater.start()

        # Web API if enabled
        if self.enable_web_api:
            self._start_web_server()

        logging.info("Real-time monitoring started")

    def stop(self):
        """Stop monitoring"""
        self.stop_event.set()

        # Wait for threads to finish
        if self.event_processor:
            self.event_processor.join(timeout=2)

        if self.console_updater:
            self.console_updater.join(timeout=1)

        if self.web_server:
            self._stop_web_server()

        # Save final metrics
        if self.metrics_file:
            self.save_metrics()

        logging.info("Real-time monitoring stopped")

    def emit_event(self, event_type: EventType, worker_id: int,
                   task_id: str = None, **data):
        """
        Emit monitoring event (thread-safe)

        Args:
            event_type: Event type
            worker_id: Worker ID
            task_id: Task ID (optional)
            **data: Additional data
        """
        event = MonitoringEvent(
            event_type=event_type,
            timestamp=time.time(),
            worker_id=worker_id,
            task_id=task_id,
            data=data
        )

        try:
            self.event_queue.put_nowait(event)
        except Exception as e:
            logging.warning("Failed to emit monitoring event: %s", e)

    def register_callback(self, event_type: EventType, callback: Callable):
        """Register callback for event type"""
        self.event_callbacks[event_type].append(callback)

    def create_progress_tracker(self, name: str, total: int) -> 'ProgressTracker':
        """Create named progress tracker"""
        with self.stats_lock:
            self.progress_bars[name] = {
                'total': total,
                'completed': 0,
                'start_time': time.time()
            }

        return ProgressTracker(self, name)

    def _process_events(self):
        """Main event processing thread"""
        while not self.stop_event.is_set():
            try:
                # Process events in batches for efficiency
                events_batch = []

                # Collect available events (non-blocking)
                try:
                    # First event (blocking with timeout)
                    event = self.event_queue.get(timeout=0.1)
                    events_batch.append(event)

                    # Additional events (non-blocking)
                    while True:
                        try:
                            event = self.event_queue.get_nowait()
                            events_batch.append(event)
                            if len(events_batch) >= 50:  # Limit batch size
                                break
                        except Empty:
                            break

                except Empty:
                    continue

                # Process batch
                self._process_events_batch(events_batch)

            except Exception as e:
                logging.error("Error processing monitoring events: %s", e)

    def _process_events_batch(self, events: List[MonitoringEvent]):
        """Process event batch"""
        with self.stats_lock:
            for event in events:
                self._process_single_event(event)
                self.recent_events.append(event)

    def _process_single_event(self, event: MonitoringEvent):
        """Process individual event"""
        worker_id = event.worker_id

        # Initialize worker state if needed (starting from worker ID 1)
        if worker_id > 0 and worker_id not in self.worker_states:
            self.worker_states[worker_id] = WorkerState(worker_id=worker_id)

        # Only process worker events for valid worker IDs (> 0)
        if worker_id > 0:
            worker_state = self.worker_states[worker_id]

            # Process by event type
            if event.event_type == EventType.TASK_STARTED:
                worker_state.is_busy = True
                worker_state.current_task = event.task_id
                worker_state.task_start_time = event.timestamp
                worker_state.last_activity = event.timestamp

            elif event.event_type == EventType.TASK_COMPLETED:
                if worker_id in self.worker_states:
                    worker_state.tasks_completed += 1
                    worker_state.reset_task()
                self.stats.completed_tasks += 1

                # Record response time
                duration = event.data.get('duration', 0)
                if duration > 0:
                    self.response_times.append(duration)

                # Record bytes downloaded
                bytes_dl = event.data.get('bytes_downloaded', 0)
                if bytes_dl > 0:
                    if worker_id in self.worker_states:
                        worker_state.bytes_downloaded += bytes_dl
                    self.stats.bytes_downloaded += bytes_dl

                    # Calculate throughput
                    if duration > 0:
                        throughput_mbps = (bytes_dl / (1024 * 1024)) / duration
                        self.throughput_history.append((event.timestamp, throughput_mbps))

            elif event.event_type == EventType.TASK_FAILED:
                if worker_id in self.worker_states:
                    worker_state.tasks_failed += 1
                    worker_state.reset_task()
                self.stats.failed_tasks += 1

        # Process global events regardless of worker ID
        if event.event_type == EventType.BATCH_STARTED:
            self.stats.total_tasks = event.data.get('total_tasks', 0)
            self.stats.cached_tasks += event.data.get('cached_tasks', 0)

        elif event.event_type == EventType.WAF_DETECTED:
            self.stats.waf_blocks += 1

        elif event.event_type == EventType.RATE_LIMIT_HIT:
            self.stats.rate_limits += 1

        # Update global stats
        self._update_derived_stats()

        # Call callbacks
        for callback in self.event_callbacks[event.event_type]:
            try:
                callback(event)
            except Exception as e:
                logging.warning("Error in event callback: %s", e)

    def _update_derived_stats(self):
        """Update derived statistics"""
        # Active workers (only count workers with ID > 0)
        self.stats.active_workers = sum(
            1 for ws in self.worker_states.values() if ws.is_busy and ws.worker_id > 0
        )

        # Current worker count (total registered valid workers)
        self.stats.current_worker_count = len([w for w in self.worker_states.keys() if w > 0])

        # Average response time
        if self.response_times:
            self.stats.avg_response_time = sum(self.response_times) / len(self.response_times)

        # Requests per second
        elapsed = time.time() - self.stats.start_time
        if elapsed > 0:
            total_requests = self.stats.completed_tasks + self.stats.failed_tasks
            self.stats.requests_per_second = total_requests / elapsed

    def _update_console(self):
        """Optimized console update thread"""
        last_update = 0

        while not self.stop_event.wait(timeout=0.5):
            current_time = time.time()

            # Limit console updates (max 2 times per second)
            if current_time - last_update < 0.5:
                continue

            try:
                self._render_console()
                last_update = current_time
            except Exception as e:
                logging.error("Error updating console: %s", e)

    def _render_console(self):
        """Render optimized console display with improved alignment"""
        with self.stats_lock:
            stats_copy = RealTimeStats(**asdict(self.stats))
            # Only include valid workers (ID > 0) and sort them properly
            workers_copy = {k: WorkerState(**asdict(v)) for k, v in self.worker_states.items() if k > 0}
            progress_copy = self.progress_bars.copy()

        # Clear screen
        import os
        if os.name == 'nt':
            os.system('cls')
        else:
            print('\033[2J\033[H', end='')

        # Header
        print("=" * 80)
        print("GRACENOTE2EPG - REAL-TIME MONITOR")
        print("=" * 80)

        # Workers status with actual count (only show valid workers)
        if workers_copy:
            active_count = sum(1 for w in workers_copy.values() if w.is_busy)
            total_workers = len(workers_copy)
            print(f"\nWorkers ({active_count}/{total_workers} active):")

            # Sort workers by ID for consistent display
            for worker in sorted(workers_copy.values(), key=lambda x: x.worker_id):
                if worker.is_busy:
                    elapsed = time.time() - worker.task_start_time if worker.task_start_time else 0
                    task_display = worker.current_task[:10] if worker.current_task else "unknown"
                    print(f"  Worker {worker.worker_id}: {task_display} ({elapsed:.1f}s)")
                else:
                    print(f"  Worker {worker.worker_id}: idle ({worker.tasks_completed} completed)")

        # Progress bars with improved alignment and chronological order
        if progress_copy:
            print()  # Add spacing before progress bars

            # Calculate maximum name width for alignment
            max_name_width = max(len(name) for name in progress_copy.keys()) if progress_copy else 0
            max_name_width = max(max_name_width, 16)  # Minimum width for readability

            # Define chronological order for progress bars
            progress_order = [
                "Downloading Guide",
                "Parsing Guide",
                "Downloading Details",
                "Processing Details",
                "Generating XMLTV"
            ]

            # Display progress bars in chronological order
            displayed_names = set()
            for ordered_name in progress_order:
                if ordered_name in progress_copy:
                    displayed_names.add(ordered_name)
                    name = ordered_name
                    progress = progress_copy[name]
                    total = progress['total']
                    completed = progress['completed']

                    # Get cache info if available
                    cached = progress.get('cached', 0)

                    if total > 0:
                        pct = (completed / total) * 100
                        bar_width = 30
                        filled = int(bar_width * completed / total)
                        bar = '█' * filled + '░' * (bar_width - filled)

                        # Enhanced formatting with cache info
                        name_padded = name.ljust(max_name_width)
                        if cached > 0:
                            print(f"  {name_padded}: |{bar}| {pct:.1f}% ({completed}/{total}, {cached} cached)")
                        else:
                            print(f"  {name_padded}: |{bar}| {pct:.1f}% ({completed}/{total})")

            # Display any remaining progress bars not in the predefined order
            for name in sorted(progress_copy.keys()):
                if name not in displayed_names:
                    progress = progress_copy[name]
                    total = progress['total']
                    completed = progress['completed']
                    cached = progress.get('cached', 0)

                    if total > 0:
                        pct = (completed / total) * 100
                        bar_width = 30
                        filled = int(bar_width * completed / total)
                        bar = '█' * filled + '░' * (bar_width - filled)

                        # Enhanced formatting with cache info
                        name_padded = name.ljust(max_name_width)
                        if cached > 0:
                            print(f"  {name_padded}: |{bar}| {pct:.1f}% ({completed}/{total}, {cached} cached)")
                        else:
                            print(f"  {name_padded}: |{bar}| {pct:.1f}% ({completed}/{total})")

        # Performance summary (simplified)
        if stats_copy.requests_per_second > 0 and any(w.is_busy for w in workers_copy.values()):
            print(f"\nCurrent: {stats_copy.requests_per_second:.1f} req/s, {stats_copy.avg_response_time:.2f}s avg")

        # Alerts
        alerts = []
        if stats_copy.waf_blocks > 0:
            alerts.append(f"WAF blocks: {stats_copy.waf_blocks}")
        if stats_copy.rate_limits > 0:
            alerts.append(f"Rate limits: {stats_copy.rate_limits}")

        if alerts:
            print(f"\nAlerts: {' | '.join(alerts)}")

        print(f"\nLast update: {datetime.now().strftime('%H:%M:%S')}")
        if self.enable_web_api:
            print(f"API: http://localhost:{self.web_port}/stats")
        print("-" * 80)

        # Force flush
        sys.stdout.flush()

    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics (thread-safe)"""
        with self.stats_lock:
            # Only include valid workers (ID > 0)
            valid_workers = {k: asdict(v) for k, v in self.worker_states.items() if k > 0}

            return {
                'stats': asdict(self.stats),
                'workers': valid_workers,
                'progress_bars': self.progress_bars.copy(),
                'recent_events_count': len(self.recent_events),
                'avg_response_time': self.stats.avg_response_time,
                'requests_per_second': self.stats.requests_per_second
            }

    def save_metrics(self):
        """Save metrics"""
        if not self.metrics_file:
            return

        try:
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'statistics': self.get_statistics(),
                'events': [asdict(event) for event in list(self.recent_events)]
            }

            with open(self.metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)

            logging.info(f"Metrics saved to {self.metrics_file}")
        except Exception as e:
            logging.error(f"Failed to save metrics: {e}")

    def _start_web_server(self):
        """Start web server for monitoring API"""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            import json

            monitor = self

            class MonitoringHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/stats':
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()

                        stats = monitor.get_statistics()
                        self.wfile.write(json.dumps(stats).encode())
                    else:
                        self.send_response(404)
                        self.end_headers()

                def log_message(self, format, *args):
                    # Suppress HTTP logs to avoid spam
                    pass

            def run_server():
                server = HTTPServer(('localhost', self.web_port), MonitoringHandler)
                self.web_server = server
                logging.info(f"Web monitoring API started on http://localhost:{self.web_port}/stats")
                server.serve_forever()

            web_thread = threading.Thread(target=run_server, daemon=True)
            web_thread.start()

        except Exception as e:
            logging.warning(f"Could not start web server: {e}")

    def _stop_web_server(self):
        """Stop web server"""
        if self.web_server:
            self.web_server.shutdown()


class ProgressTracker:
    """Progress tracker for specific batch"""

    def __init__(self, monitor: EventDrivenMonitor, name: str):
        self.monitor = monitor
        self.name = name

    def update(self, completed: int):
        """Update progress"""
        with self.monitor.stats_lock:
            if self.name in self.monitor.progress_bars:
                self.monitor.progress_bars[self.name]['completed'] = completed

    def increment(self):
        """Increment progress by 1"""
        with self.monitor.stats_lock:
            if self.name in self.monitor.progress_bars:
                self.monitor.progress_bars[self.name]['completed'] += 1


class MonitoringMixin:
    """Mixin to add monitoring support to download classes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor: Optional[EventDrivenMonitor] = None

    def set_monitor(self, monitor: EventDrivenMonitor):
        """Associate monitor"""
        self.monitor = monitor

    def emit_event(self, event_type: EventType, worker_id: int, task_id: str = None, **data):
        """Emit event if monitor is configured"""
        if self.monitor:
            self.monitor.emit_event(event_type, worker_id, task_id, **data)
