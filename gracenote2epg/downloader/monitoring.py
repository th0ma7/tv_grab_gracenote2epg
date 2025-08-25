"""
gracenote2epg.downloader.monitoring - Real-time monitoring and metrics

Provides real-time monitoring, progress tracking, and performance metrics
for parallel download operations. Moved from gracenote2epg_monitoring.py
"""

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Deque, Any
import sys


@dataclass
class DownloadMetric:
    """Single download metric data point"""
    timestamp: float
    task_id: str
    task_type: str
    duration: float
    success: bool
    bytes_downloaded: int
    retry_count: int
    worker_id: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            **asdict(self),
            'timestamp_str': datetime.fromtimestamp(self.timestamp).isoformat()
        }


class ProgressBar:
    """Terminal progress bar for downloads"""
    
    def __init__(self, total: int, width: int = 50, prefix: str = "Progress"):
        self.total = total
        self.width = width
        self.prefix = prefix
        self.current = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
        
    def update(self, current: int):
        """Update progress bar"""
        with self.lock:
            self.current = current
            self._render()
    
    def increment(self):
        """Increment progress by 1"""
        with self.lock:
            self.current += 1
            self._render()
    
    def _render(self):
        """Render progress bar to terminal"""
        if self.total == 0:
            return
        
        # Calculate percentage
        percent = (self.current / self.total) * 100
        
        # Calculate filled width
        filled = int(self.width * self.current / self.total)
        
        # Create bar
        bar = '█' * filled + '░' * (self.width - filled)
        
        # Calculate time
        elapsed = time.time() - self.start_time
        if self.current > 0:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = self._format_time(eta)
        else:
            eta_str = "N/A"
        
        # Print progress
        sys.stdout.write(f'\r{self.prefix}: |{bar}| {percent:.1f}% ({self.current}/{self.total}) ETA: {eta_str}')
        sys.stdout.flush()
        
        # New line when complete
        if self.current >= self.total:
            sys.stdout.write('\n')
            sys.stdout.flush()
    
    def _format_time(self, seconds: float) -> str:
        """Format time in human-readable format"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"


class RealTimeMonitor:
    """Real-time monitoring for parallel downloads"""
    
    def __init__(self, enable_console: bool = True, metrics_file: Optional[Path] = None):
        """
        Initialize monitor
        
        Args:
            enable_console: Show real-time console output
            metrics_file: Optional file to save metrics
        """
        self.enable_console = enable_console
        self.metrics_file = metrics_file
        
        # Metrics storage
        self.metrics: Deque[DownloadMetric] = deque(maxlen=1000)
        self.metrics_lock = threading.Lock()
        
        # Current state
        self.active_downloads: Dict[int, Dict] = {}  # worker_id -> task info
        self.download_counts = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'cached': 0
        }
        
        # Performance tracking
        self.response_times: Deque[float] = deque(maxlen=100)
        self.throughput_history: Deque[float] = deque(maxlen=60)  # Last minute
        
        # Display thread
        self.display_thread = None
        self.stop_display = threading.Event()
        
        # Progress bars
        self.progress_bars: Dict[str, ProgressBar] = {}
    
    def start(self):
        """Start monitoring"""
        if self.enable_console:
            self.stop_display.clear()
            self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
            self.display_thread.start()
        
        logging.info("Real-time monitoring started")
    
    def stop(self):
        """Stop monitoring"""
        if self.display_thread:
            self.stop_display.set()
            self.display_thread.join(timeout=2)
        
        # Save final metrics
        if self.metrics_file:
            self.save_metrics()
        
        logging.info("Real-time monitoring stopped")
    
    def record_download(self, metric: DownloadMetric):
        """Record a download metric"""
        with self.metrics_lock:
            self.metrics.append(metric)
            
            # Update counts
            self.download_counts['total'] += 1
            if metric.success:
                self.download_counts['successful'] += 1
            else:
                self.download_counts['failed'] += 1
            
            # Update performance metrics
            self.response_times.append(metric.duration)
            
            # Calculate throughput
            if metric.bytes_downloaded > 0 and metric.duration > 0:
                throughput_mbps = (metric.bytes_downloaded / (1024 * 1024)) / metric.duration
                self.throughput_history.append(throughput_mbps)
    
    def update_active_download(self, worker_id: int, task_info: Optional[Dict] = None):
        """Update active download status"""
        with self.metrics_lock:
            if task_info:
                self.active_downloads[worker_id] = {
                    **task_info,
                    'start_time': time.time()
                }
            else:
                # Clear completed download
                self.active_downloads.pop(worker_id, None)
    
    def create_progress_bar(self, name: str, total: int) -> ProgressBar:
        """Create a named progress bar"""
        progress_bar = ProgressBar(total=total, prefix=name)
        self.progress_bars[name] = progress_bar
        return progress_bar
    
    def _display_loop(self):
        """Main display loop for console output"""
        while not self.stop_display.wait(timeout=1.0):
            self._update_display()
    
    def _update_display(self):
        """Update console display"""
        # Clear screen (platform-specific)
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Header
        print("=" * 80)
        print("GRACENOTE2EPG - REAL-TIME MONITOR")
        print("=" * 80)
        
        # Current status
        print(f"\n📊 Download Statistics:")
        print(f"  Total: {self.download_counts['total']}")
        print(f"  ✅ Successful: {self.download_counts['successful']}")
        print(f"  ❌ Failed: {self.download_counts['failed']}")
        print(f"  💾 From Cache: {self.download_counts['cached']}")
        
        # Performance metrics
        if self.response_times:
            avg_response = sum(self.response_times) / len(self.response_times)
            print(f"\n⚡ Performance:")
            print(f"  Avg Response Time: {avg_response:.2f}s")
            
            if self.throughput_history:
                avg_throughput = sum(self.throughput_history) / len(self.throughput_history)
                print(f"  Avg Throughput: {avg_throughput:.2f} MB/s")
        
        # Active downloads
        if self.active_downloads:
            print(f"\n🔄 Active Downloads ({len(self.active_downloads)} workers):")
            for worker_id, info in self.active_downloads.items():
                elapsed = time.time() - info['start_time']
                print(f"  Worker {worker_id}: {info.get('task_id', 'Unknown')} ({elapsed:.1f}s)")
        
        # Success rate
        if self.download_counts['total'] > 0:
            success_rate = (self.download_counts['successful'] / 
                          (self.download_counts['successful'] + self.download_counts['failed'])) * 100
            print(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        print("\n" + "-" * 80)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get current statistics"""
        with self.metrics_lock:
            stats = {
                'counts': self.download_counts.copy(),
                'active_workers': len(self.active_downloads),
                'metrics_count': len(self.metrics)
            }
            
            if self.response_times:
                stats['avg_response_time'] = sum(self.response_times) / len(self.response_times)
                stats['min_response_time'] = min(self.response_times)
                stats['max_response_time'] = max(self.response_times)
            
            if self.throughput_history:
                stats['avg_throughput_mbps'] = sum(self.throughput_history) / len(self.throughput_history)
                stats['peak_throughput_mbps'] = max(self.throughput_history)
            
            return stats
    
    def save_metrics(self):
        """Save metrics to file"""
        if not self.metrics_file:
            return
        
        try:
            # Convert metrics to serializable format
            metrics_data = {
                'timestamp': datetime.now().isoformat(),
                'statistics': self.get_statistics(),
                'metrics': [m.to_dict() for m in self.metrics]
            }
            
            # Save to file
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            
            logging.info(f"Metrics saved to {self.metrics_file}")
            
        except Exception as e:
            logging.error(f"Failed to save metrics: {e}")


class PerformanceAnalyzer:
    """Analyze performance metrics and provide recommendations"""
    
    def __init__(self, metrics: List[DownloadMetric]):
        self.metrics = metrics
    
    def analyze(self) -> Dict[str, Any]:
        """Perform comprehensive performance analysis"""
        if not self.metrics:
            return {'error': 'No metrics available'}
        
        analysis = {
            'summary': self._analyze_summary(),
            'bottlenecks': self._identify_bottlenecks(),
            'patterns': self._analyze_patterns(),
            'recommendations': self._generate_recommendations()
        }
        
        return analysis
    
    def _analyze_summary(self) -> Dict:
        """Analyze summary statistics"""
        total = len(self.metrics)
        successful = sum(1 for m in self.metrics if m.success)
        failed = total - successful
        
        durations = [m.duration for m in self.metrics]
        bytes_total = sum(m.bytes_downloaded for m in self.metrics)
        
        return {
            'total_downloads': total,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'total_bytes': bytes_total,
            'total_mb': bytes_total / (1024 * 1024),
            'avg_duration': sum(durations) / len(durations) if durations else 0,
            'min_duration': min(durations) if durations else 0,
            'max_duration': max(durations) if durations else 0
        }
    
    def _identify_bottlenecks(self) -> List[str]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Check for high failure rate
        summary = self._analyze_summary()
        if summary['success_rate'] < 80:
            bottlenecks.append(f"High failure rate: {100-summary['success_rate']:.1f}%")
        
        # Check for slow downloads
        if summary['avg_duration'] > 5.0:
            bottlenecks.append(f"Slow average download time: {summary['avg_duration']:.1f}s")
        
        # Check for retry storms
        high_retry_count = sum(1 for m in self.metrics if m.retry_count > 2)
        if high_retry_count > len(self.metrics) * 0.1:
            bottlenecks.append(f"High retry rate: {high_retry_count} downloads needed >2 retries")
        
        # Check for worker imbalance
        worker_loads = {}
        for m in self.metrics:
            worker_loads[m.worker_id] = worker_loads.get(m.worker_id, 0) + 1
        
        if worker_loads:
            max_load = max(worker_loads.values())
            min_load = min(worker_loads.values())
            if max_load > min_load * 2:
                bottlenecks.append(f"Worker load imbalance: {max_load} vs {min_load}")
        
        return bottlenecks
    
    def _analyze_patterns(self) -> Dict:
        """Analyze download patterns"""
        patterns = {}
        
        # Time-based patterns
        if self.metrics:
            start_time = min(m.timestamp for m in self.metrics)
            end_time = max(m.timestamp for m in self.metrics)
            total_duration = end_time - start_time
            
            patterns['total_duration'] = total_duration
            patterns['downloads_per_second'] = len(self.metrics) / total_duration if total_duration > 0 else 0
            
            # Analyze by task type
            by_type = {}
            for m in self.metrics:
                if m.task_type not in by_type:
                    by_type[m.task_type] = {
                        'count': 0,
                        'success': 0,
                        'total_duration': 0,
                        'total_bytes': 0
                    }
                
                by_type[m.task_type]['count'] += 1
                if m.success:
                    by_type[m.task_type]['success'] += 1
                by_type[m.task_type]['total_duration'] += m.duration
                by_type[m.task_type]['total_bytes'] += m.bytes_downloaded
            
            patterns['by_task_type'] = by_type
        
        return patterns
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        summary = self._analyze_summary()
        bottlenecks = self._identify_bottlenecks()
        
        # Based on success rate
        if summary['success_rate'] < 80:
            recommendations.append("Reduce worker count to improve stability")
            recommendations.append("Enable rate limiting to avoid server rejection")
        
        # Based on duration
        if summary['avg_duration'] > 5.0:
            recommendations.append("Check network connectivity and latency")
            recommendations.append("Consider using fewer workers if server is throttling")
        elif summary['avg_duration'] < 1.0 and summary['success_rate'] > 95:
            recommendations.append("Can safely increase worker count for better performance")
        
        # Based on bottlenecks
        if any('retry' in b.lower() for b in bottlenecks):
            recommendations.append("Implement exponential backoff for retries")
            recommendations.append("Check for WAF or rate limiting on server")
        
        if any('imbalance' in b.lower() for b in bottlenecks):
            recommendations.append("Use work-stealing queue for better load distribution")
        
        return recommendations


class MetricsExporter:
    """Export metrics in various formats"""
    
    @staticmethod
    def to_csv(metrics: List[DownloadMetric], filepath: Path):
        """Export metrics to CSV"""
        import csv
        
        with open(filepath, 'w', newline='') as f:
            if not metrics:
                return
            
            # Write header
            fieldnames = ['timestamp', 'task_id', 'task_type', 'duration', 
                         'success', 'bytes_downloaded', 'retry_count', 'worker_id']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write metrics
            for metric in metrics:
                writer.writerow(asdict(metric))
        
        logging.info(f"Metrics exported to CSV: {filepath}")
    
    @staticmethod
    def to_json(metrics: List[DownloadMetric], filepath: Path):
        """Export metrics to JSON"""
        data = {
            'export_time': datetime.now().isoformat(),
            'metric_count': len(metrics),
            'metrics': [m.to_dict() for m in metrics]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logging.info(f"Metrics exported to JSON: {filepath}")
    
    @staticmethod
    def to_prometheus(metrics: List[DownloadMetric]) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        # Calculate aggregates
        total = len(metrics)
        successful = sum(1 for m in metrics if m.success)
        failed = total - successful
        total_bytes = sum(m.bytes_downloaded for m in metrics)
        avg_duration = sum(m.duration for m in metrics) / total if total > 0 else 0
        
        # Format as Prometheus metrics
        lines.append('# HELP gracenote2epg_downloads_total Total number of downloads')
        lines.append('# TYPE gracenote2epg_downloads_total counter')
        lines.append(f'gracenote2epg_downloads_total {total}')
        
        lines.append('# HELP gracenote2epg_downloads_successful Successful downloads')
        lines.append('# TYPE gracenote2epg_downloads_successful counter')
        lines.append(f'gracenote2epg_downloads_successful {successful}')
        
        lines.append('# HELP gracenote2epg_downloads_failed Failed downloads')
        lines.append('# TYPE gracenote2epg_downloads_failed counter')
        lines.append(f'gracenote2epg_downloads_failed {failed}')
        
        lines.append('# HELP gracenote2epg_bytes_downloaded Total bytes downloaded')
        lines.append('# TYPE gracenote2epg_bytes_downloaded counter')
        lines.append(f'gracenote2epg_bytes_downloaded {total_bytes}')
        
        lines.append('# HELP gracenote2epg_download_duration_seconds Average download duration')
        lines.append('# TYPE gracenote2epg_download_duration_seconds gauge')
        lines.append(f'gracenote2epg_download_duration_seconds {avg_duration:.3f}')
        
        return '\n'.join(lines)
