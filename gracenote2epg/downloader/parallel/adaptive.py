"""
gracenote2epg.downloader.parallel.adaptive - Adaptive parallel downloader

Adaptive parallel downloader that automatically adjusts concurrency based on performance.
"""

import logging
import time
from typing import Dict, Any, List
from dataclasses import dataclass

from .worker_pool import WorkerPool, AdaptiveWorkerManager


@dataclass
class PerformanceMetric:
    """Performance measurement for adaptive decisions"""
    timestamp: float
    workers: int
    success_rate: float
    avg_response_time: float
    throughput: float
    error_rate: float


class AdaptiveParallelDownloader:
    """
    Adaptive parallel downloader that adjusts concurrency based on performance
    
    This class automatically scales worker count based on observed performance metrics
    including success rate, response time, and throughput.
    """

    def __init__(self, initial_workers: int = 2, max_workers: int = 8):
        self.initial_workers = initial_workers
        self.max_workers = max_workers
        self.min_workers = 1
        
        # Performance tracking
        self.performance_history: List[PerformanceMetric] = []
        self.max_history_size = 100
        self.adjustment_interval = 10  # seconds between adjustments
        self.last_adjustment = 0
        
        # Worker pool for actual work execution
        self.worker_pool = WorkerPool(initial_workers, max_workers)
        self.adaptive_manager = AdaptiveWorkerManager(self.worker_pool)
        
        # Performance thresholds
        self.good_success_rate = 0.95
        self.poor_success_rate = 0.80
        self.good_response_time = 2.0  # seconds
        self.poor_response_time = 5.0  # seconds
        self.good_throughput = 1.0     # items/second
        
        logging.info(
            "Adaptive parallel downloader initialized: %d initial workers (max: %d)",
            initial_workers,
            max_workers
        )

    def record_performance(self, 
                          success_rate: float, 
                          avg_response_time: float,
                          throughput: float = 0.0,
                          error_rate: float = 0.0):
        """
        Record performance metrics for adaptive decision making
        
        Args:
            success_rate: Percentage of successful requests (0-1.0)
            avg_response_time: Average response time in seconds
            throughput: Items processed per second
            error_rate: Error rate (0-1.0)
        """
        metric = PerformanceMetric(
            timestamp=time.time(),
            workers=self.worker_pool.current_workers,
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            throughput=throughput,
            error_rate=error_rate
        )
        
        self.performance_history.append(metric)
        
        # Keep history bounded
        if len(self.performance_history) > self.max_history_size:
            self.performance_history = self.performance_history[-self.max_history_size//2:]
        
        # Record with adaptive manager
        self.adaptive_manager.record_performance(success_rate, avg_response_time, throughput)
        
        # Trigger evaluation
        self._evaluate_performance()

    def _evaluate_performance(self):
        """Evaluate recent performance and adjust workers if needed"""
        current_time = time.time()
        
        # Check if enough time has passed since last adjustment
        if current_time - self.last_adjustment < self.adjustment_interval:
            return
            
        # Need minimum samples to make decisions
        if len(self.performance_history) < 3:
            return
            
        # Analyze recent performance (last 5 samples or all if less)
        recent_samples = self.performance_history[-5:]
        
        avg_success_rate = sum(m.success_rate for m in recent_samples) / len(recent_samples)
        avg_response_time = sum(m.avg_response_time for m in recent_samples) / len(recent_samples)
        avg_throughput = sum(m.throughput for m in recent_samples) / len(recent_samples)
        avg_error_rate = sum(m.error_rate for m in recent_samples) / len(recent_samples)
        
        current_workers = self.worker_pool.current_workers
        
        # Decision logic
        should_increase = self._should_increase_workers(
            avg_success_rate, avg_response_time, avg_throughput, avg_error_rate
        )
        
        should_decrease = self._should_decrease_workers(
            avg_success_rate, avg_response_time, avg_throughput, avg_error_rate
        )
        
        if should_increase and not should_decrease:
            self._increase_workers("performance analysis")
        elif should_decrease and not should_increase:
            self._decrease_workers("performance analysis")
            
        self.last_adjustment = current_time

    def _should_increase_workers(self, success_rate: float, response_time: float, 
                                throughput: float, error_rate: float) -> bool:
        """Determine if workers should be increased based on performance"""
        current_workers = self.worker_pool.current_workers
        
        # Don't increase if at maximum
        if current_workers >= self.max_workers:
            return False
            
        # Increase if performance is good across all metrics
        good_performance = (
            success_rate >= self.good_success_rate and
            response_time <= self.good_response_time and
            throughput >= self.good_throughput and
            error_rate <= 0.05
        )
        
        if good_performance:
            # Check if we've been stable at this performance level
            stable_performance = self._is_performance_stable(min_samples=3)
            return stable_performance
            
        return False

    def _should_decrease_workers(self, success_rate: float, response_time: float,
                                throughput: float, error_rate: float) -> bool:
        """Determine if workers should be decreased based on performance"""
        current_workers = self.worker_pool.current_workers
        
        # Don't decrease if at minimum
        if current_workers <= self.min_workers:
            return False
            
        # Decrease if performance is poor in any critical metric
        poor_performance = (
            success_rate <= self.poor_success_rate or
            response_time >= self.poor_response_time or
            error_rate >= 0.20
        )
        
        return poor_performance

    def _is_performance_stable(self, min_samples: int = 3) -> bool:
        """Check if recent performance has been stable"""
        if len(self.performance_history) < min_samples:
            return False
            
        recent = self.performance_history[-min_samples:]
        
        # Check stability in success rate (variation < 5%)
        success_rates = [m.success_rate for m in recent]
        success_variation = max(success_rates) - min(success_rates)
        
        # Check stability in response time (variation < 1 second)
        response_times = [m.avg_response_time for m in recent]
        response_variation = max(response_times) - min(response_times)
        
        return success_variation < 0.05 and response_variation < 1.0

    def _increase_workers(self, reason: str = "performance"):
        """Increase worker count by 1"""
        old_count = self.worker_pool.current_workers
        new_count = min(self.max_workers, old_count + 1)
        
        if new_count > old_count:
            self.worker_pool.adjust_worker_count(new_count, f"adaptive increase ({reason})")
            logging.info("Adaptive: Increased workers from %d to %d (%s)", 
                        old_count, new_count, reason)

    def _decrease_workers(self, reason: str = "performance"):
        """Decrease worker count by 1"""
        old_count = self.worker_pool.current_workers
        new_count = max(self.min_workers, old_count - 1)
        
        if new_count < old_count:
            self.worker_pool.adjust_worker_count(new_count, f"adaptive decrease ({reason})")
            logging.info("Adaptive: Decreased workers from %d to %d (%s)",
                        old_count, new_count, reason)

    def force_worker_adjustment(self, target_workers: int, reason: str = "manual"):
        """Manually force worker count adjustment"""
        target_workers = max(self.min_workers, min(self.max_workers, target_workers))
        self.worker_pool.adjust_worker_count(target_workers, f"forced ({reason})")
        self.last_adjustment = time.time()

    def get_optimal_workers(self) -> int:
        """Get current optimal number of workers based on recent performance"""
        return self.worker_pool.current_workers

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.performance_history:
            return {
                'status': 'no_data',
                'current_workers': self.worker_pool.current_workers,
                'initial_workers': self.initial_workers,
                'max_workers': self.max_workers
            }
        
        # Analyze recent performance
        recent_samples = self.performance_history[-10:] if len(self.performance_history) >= 10 else self.performance_history
        
        avg_success_rate = sum(m.success_rate for m in recent_samples) / len(recent_samples)
        avg_response_time = sum(m.avg_response_time for m in recent_samples) / len(recent_samples)
        avg_throughput = sum(m.throughput for m in recent_samples) / len(recent_samples)
        
        # Calculate performance trend
        trend = self._calculate_performance_trend()
        
        # Get worker statistics
        worker_stats = self.worker_pool.get_worker_statistics()
        
        return {
            'status': 'active',
            'current_workers': self.worker_pool.current_workers,
            'initial_workers': self.initial_workers,
            'max_workers': self.max_workers,
            'min_workers': self.min_workers,
            
            # Performance metrics
            'avg_success_rate': avg_success_rate,
            'avg_response_time': avg_response_time,
            'avg_throughput': avg_throughput,
            
            # Analysis
            'performance_trend': trend,
            'total_adjustments': len(self.performance_history),
            'last_adjustment': self.last_adjustment,
            
            # Worker details
            'worker_statistics': worker_stats,
            
            # Adaptive manager status
            'adaptive_manager': self.adaptive_manager.get_evaluation_summary() if self.adaptive_manager else None
        }

    def _calculate_performance_trend(self) -> str:
        """Calculate overall performance trend"""
        if len(self.performance_history) < 5:
            return "insufficient_data"
            
        # Compare first half vs second half of recent samples
        recent = self.performance_history[-10:]
        mid_point = len(recent) // 2
        
        first_half = recent[:mid_point]
        second_half = recent[mid_point:]
        
        first_avg_success = sum(m.success_rate for m in first_half) / len(first_half)
        second_avg_success = sum(m.success_rate for m in second_half) / len(second_half)
        
        first_avg_response = sum(m.avg_response_time for m in first_half) / len(first_half)
        second_avg_response = sum(m.avg_response_time for m in second_half) / len(second_half)
        
        # Determine trend
        success_improving = second_avg_success > first_avg_success
        response_improving = second_avg_response < first_avg_response
        
        if success_improving and response_improving:
            return "improving"
        elif not success_improving and not response_improving:
            return "degrading"
        else:
            return "stable"

    def reset_performance_history(self):
        """Reset performance history (useful for testing or fresh starts)"""
        self.performance_history.clear()
        self.last_adjustment = 0
        logging.info("Adaptive downloader: Performance history reset")

    def get_current_configuration(self) -> Dict[str, Any]:
        """Get current adaptive configuration"""
        return {
            'initial_workers': self.initial_workers,
            'current_workers': self.worker_pool.current_workers,
            'max_workers': self.max_workers,
            'min_workers': self.min_workers,
            'adjustment_interval': self.adjustment_interval,
            'thresholds': {
                'good_success_rate': self.good_success_rate,
                'poor_success_rate': self.poor_success_rate,
                'good_response_time': self.good_response_time,
                'poor_response_time': self.poor_response_time,
                'good_throughput': self.good_throughput
            }
        }

    def cleanup(self):
        """Clean up adaptive downloader resources"""
        logging.info("Cleaning up adaptive downloader")
        self.worker_pool.cleanup()
        
        # Log final summary
        if self.performance_history:
            summary = self.get_performance_summary()
            logging.info("Adaptive downloader final summary: %d adjustments made, "
                        "final worker count: %d, performance trend: %s",
                        summary['total_adjustments'], 
                        summary['current_workers'],
                        summary['performance_trend'])
