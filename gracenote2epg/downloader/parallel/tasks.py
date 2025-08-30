"""
gracenote2epg.downloader.parallel.tasks - Download task definitions and data structures

Task management and result structures for parallel downloading.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Any, Tuple


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


@dataclass
class DownloadResult:
    """Result of a download task execution"""
    task_id: str
    success: bool
    content: Optional[bytes] = None
    error: Optional[str] = None
    duration: float = 0.0
    bytes_downloaded: int = 0
    attempts: int = 1
    http_code: Optional[int] = None

    def __post_init__(self):
        if self.content and self.bytes_downloaded == 0:
            self.bytes_downloaded = len(self.content)


class TaskMetrics:
    """Track metrics for task execution"""
    
    def __init__(self):
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.cached_tasks = 0
        self.total_bytes = 0
        self.total_duration = 0.0
        
    def add_result(self, result: DownloadResult, was_cached: bool = False):
        """Add a result to metrics tracking"""
        if was_cached:
            self.cached_tasks += 1
        elif result.success:
            self.completed_tasks += 1
            self.total_bytes += result.bytes_downloaded
            self.total_duration += result.duration
        else:
            self.failed_tasks += 1
            
    def get_success_rate(self) -> float:
        """Calculate success rate for non-cached tasks"""
        total_attempted = self.completed_tasks + self.failed_tasks
        if total_attempted == 0:
            return 100.0
        return (self.completed_tasks / total_attempted) * 100.0
        
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_processed = self.completed_tasks + self.failed_tasks + self.cached_tasks
        if total_processed == 0:
            return 0.0
        return (self.cached_tasks / total_processed) * 100.0
        
    def get_average_speed(self) -> float:
        """Calculate average download speed in MB/s"""
        if self.total_duration == 0:
            return 0.0
        mb_downloaded = self.total_bytes / (1024 * 1024)
        return mb_downloaded / self.total_duration
        
    def get_throughput(self) -> float:
        """Calculate throughput in requests/second"""
        if self.total_duration == 0:
            return 0.0
        return self.completed_tasks / self.total_duration


def create_guide_task(grid_time: float, filename: str, url: str) -> DownloadTask:
    """Create a guide block download task"""
    return DownloadTask(
        task_id=filename,
        url=url,
        task_type='guide_block',
        priority=int(grid_time),
        metadata={'grid_time': grid_time}
    )


def create_series_task(series_id: str, data: str) -> DownloadTask:
    """Create a series details download task"""
    url = "https://tvlistings.gracenote.com/api/program/overviewDetails"
    return DownloadTask(
        task_id=series_id,
        url=url,
        task_type='series_details',
        data=data
    )


def validate_task_result(task: DownloadTask, result: DownloadResult) -> bool:
    """Validate that a task result is acceptable"""
    if not result.success or not result.content:
        return False
        
    # Basic content validation
    if len(result.content) < 10:
        return False
        
    # Task-specific validation
    if task.task_type == 'guide_block':
        # Guide blocks should be JSON
        try:
            import json
            json.loads(result.content)
            return True
        except json.JSONDecodeError:
            return False
            
    elif task.task_type == 'series_details':
        # Series details should also be JSON
        try:
            import json
            json.loads(result.content)
            return True
        except json.JSONDecodeError:
            return False
            
    return True
