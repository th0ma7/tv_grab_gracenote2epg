"""
gracenote2epg.downloader.parallel.adaptive - Unified adaptive strategy system

Implements proper worker strategies for different task types with true adaptive behavior.
Eliminates worker count inconsistencies and provides clear strategy separation.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .worker_pool import WorkerPool


@dataclass
class WorkerStrategy:
    """Worker configuration strategy for specific task types"""
    task_type: str
    initial_workers: int
    max_workers: int
    min_workers: int
    rate_limit: float
    timeout: int
    conservative: bool
    burst_allowed: bool

    # Current state (modified during adaptive adjustments)
    current_workers: int = None

    def __post_init__(self):
        if self.current_workers is None:
            self.current_workers = self.initial_workers


@dataclass
class PerformanceMetric:
    """Performance measurement for adaptive decisions"""
    timestamp: float
    task_type: str
    workers: int
    success_rate: float
    avg_response_time: float
    throughput: float
    error_rate: float
    bytes_downloaded: int = 0


class AdaptiveStrategy:
    """
    Unified adaptive strategy that manages worker allocation for different task types

    Provides separate, optimized strategies for:
    - Guide block downloads (larger files, can handle more workers)
    - Series detail downloads (smaller files, rate-limit sensitive)
    """

    # Predefined worker strategies
    STRATEGIES = {
        'conservative': {
            'guide_block': WorkerStrategy(
                task_type='guide_block',
                initial_workers=2,
                max_workers=3,
                min_workers=1,
                rate_limit=3.0,
                timeout=8,
                conservative=True,
                burst_allowed=False
            ),
            'series_details': WorkerStrategy(
                task_type='series_details',
                initial_workers=1,
                max_workers=2,
                min_workers=1,
                rate_limit=1.5,
                timeout=6,
                conservative=True,
                burst_allowed=False
            )
        },
        'balanced': {
            'guide_block': WorkerStrategy(
                task_type='guide_block',
                initial_workers=4,
                max_workers=6,
                min_workers=2,
                rate_limit=5.0,
                timeout=8,
                conservative=False,
                burst_allowed=True
            ),
            'series_details': WorkerStrategy(
                task_type='series_details',
                initial_workers=2,
                max_workers=3,
                min_workers=1,
                rate_limit=2.5,
                timeout=6,
                conservative=True,
                burst_allowed=False
            )
        },
        'aggressive': {
            'guide_block': WorkerStrategy(
                task_type='guide_block',
                initial_workers=6,
                max_workers=10,
                min_workers=3,
                rate_limit=8.0,
                timeout=10,
                conservative=False,
                burst_allowed=True
            ),
            'series_details': WorkerStrategy(
                task_type='series_details',
                initial_workers=3,
                max_workers=4,
                min_workers=1,
                rate_limit=4.0,
                timeout=8,
                conservative=False,
                burst_allowed=True
            )
        }
    }

    def __init__(self, strategy_name: str = "balanced", max_workers: int = 4, enable_adaptive: bool = True):
        """
        Initialize adaptive strategy system

        Args:
            strategy_name: Strategy preset ("conservative", "balanced", "aggressive")
            max_workers: Global maximum workers constraint
            enable_adaptive: Enable adaptive worker adjustment
        """
        self.strategy_name = strategy_name
        self.global_max_workers = max_workers
        self.enable_adaptive = enable_adaptive

        # Performance tracking
        self.performance_history: List[PerformanceMetric] = []
        self.max_history_size = 200
        self.adjustment_interval = 15  # seconds between adjustments
        self.last_adjustment: Dict[str, float] = {}

        # Load and constrain strategy based on global max_workers
        self.strategies = self._load_and_constrain_strategies()

        # Performance thresholds for adaptive decisions
        self.thresholds = {
            'increase_workers': {
                'success_rate': 0.95,
                'avg_response_time': 2.0,
                'stable_duration': 30,  # seconds of stable performance
                'no_errors_for': 60     # seconds without errors
            },
            'decrease_workers': {
                'success_rate': 0.80,
                'avg_response_time': 5.0,
                'error_rate': 0.15,
                'consecutive_failures': 3
            }
        }

        logging.info(
            "Adaptive strategy initialized: '%s' (global max: %d workers, adaptive: %s)",
            strategy_name, max_workers, "enabled" if enable_adaptive else "disabled"
        )

        # Log strategy details
        self._log_strategy_details()

    def _load_and_constrain_strategies(self) -> Dict[str, WorkerStrategy]:
        """Load strategy and constrain based on global max_workers"""
        if self.strategy_name not in self.STRATEGIES:
            logging.warning("Unknown strategy '%s', using 'balanced'", self.strategy_name)
            self.strategy_name = "balanced"

        base_strategies = self.STRATEGIES[self.strategy_name].copy()

        # Constrain strategies based on global max_workers
        constrained_strategies = {}

        for task_type, strategy in base_strategies.items():
            # Create new strategy with constrained values
            constrained_strategy = WorkerStrategy(
                task_type=strategy.task_type,
                initial_workers=min(strategy.initial_workers, self.global_max_workers),
                max_workers=min(strategy.max_workers, self.global_max_workers),
                min_workers=strategy.min_workers,
                rate_limit=strategy.rate_limit,
                timeout=strategy.timeout,
                conservative=strategy.conservative,
                burst_allowed=strategy.burst_allowed
            )

            # Ensure initial_workers doesn't exceed max_workers after constraint
            constrained_strategy.initial_workers = min(
                constrained_strategy.initial_workers,
                constrained_strategy.max_workers
            )

            constrained_strategies[task_type] = constrained_strategy

            if (strategy.max_workers > self.global_max_workers or
                strategy.initial_workers > self.global_max_workers):
                logging.debug(
                    "Constrained %s strategy: %d->%d initial, %d->%d max workers",
                    task_type,
                    strategy.initial_workers, constrained_strategy.initial_workers,
                    strategy.max_workers, constrained_strategy.max_workers
                )

        return constrained_strategies

    def _log_strategy_details(self):
        """Log detailed strategy configuration"""
        logging.info("Worker strategy details:")

        for task_type, strategy in self.strategies.items():
            logging.info("  %s:", task_type)
            logging.info("    Workers: %d initial, %d-%d range",
                        strategy.initial_workers, strategy.min_workers, strategy.max_workers)
            logging.info("    Rate limit: %.1f req/s", strategy.rate_limit)
            logging.info("    Timeout: %ds", strategy.timeout)
            logging.info("    Mode: %s", "conservative" if strategy.conservative else "optimized")

    def get_worker_strategy(self, task_type: str) -> WorkerStrategy:
        """Get worker strategy for specific task type"""
        if task_type not in self.strategies:
            # Default fallback strategy
            logging.warning("No strategy defined for task type '%s', using balanced guide strategy", task_type)
            return self.strategies.get('guide_block', self.strategies['series_details'])

        return self.strategies[task_type]

    def record_performance(self,
                          task_type: str,
                          success: bool,
                          response_time: float,
                          bytes_downloaded: int = 0,
                          error: Optional[str] = None):
        """
        Record performance metrics for adaptive decision making

        Args:
            task_type: Type of task ('guide_block' or 'series_details')
            success: Whether the request was successful
            response_time: Response time in seconds
            bytes_downloaded: Bytes downloaded (for throughput calculation)
            error: Error string if any
        """
        if not self.enable_adaptive:
            return

        strategy = self.get_worker_strategy(task_type)

        # Calculate metrics
        error_rate = 0.0 if success else 1.0
        throughput = bytes_downloaded / response_time if response_time > 0 else 0.0

        metric = PerformanceMetric(
            timestamp=time.time(),
            task_type=task_type,
            workers=strategy.current_workers,
            success_rate=1.0 if success else 0.0,
            avg_response_time=response_time,
            throughput=throughput,
            error_rate=error_rate,
            bytes_downloaded=bytes_downloaded
        )

        self.performance_history.append(metric)

        # Keep history bounded
        if len(self.performance_history) > self.max_history_size:
            self.performance_history = self.performance_history[-self.max_history_size//2:]

        # Trigger evaluation for this task type
        self._evaluate_task_performance(task_type)

    def _evaluate_task_performance(self, task_type: str):
        """Evaluate recent performance for specific task type and adjust if needed"""
        if not self.enable_adaptive:
            return

        current_time = time.time()

        # Check if enough time has passed since last adjustment for this task type
        last_adj = self.last_adjustment.get(task_type, 0)
        if current_time - last_adj < self.adjustment_interval:
            return

        # Get recent metrics for this task type
        recent_metrics = [
            m for m in self.performance_history[-20:]
            if m.task_type == task_type and current_time - m.timestamp < 60
        ]

        if len(recent_metrics) < 3:
            return  # Need minimum samples

        # Calculate aggregated metrics
        avg_success_rate = sum(m.success_rate for m in recent_metrics) / len(recent_metrics)
        avg_response_time = sum(m.avg_response_time for m in recent_metrics) / len(recent_metrics)
        avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        avg_throughput = sum(m.throughput for m in recent_metrics) / len(recent_metrics)

        strategy = self.get_worker_strategy(task_type)

        # Decision logic based on task-specific thresholds
        should_increase = self._should_increase_workers(
            task_type, avg_success_rate, avg_response_time, avg_error_rate, avg_throughput
        )

        should_decrease = self._should_decrease_workers(
            task_type, avg_success_rate, avg_response_time, avg_error_rate
        )

        if should_increase and not should_decrease:
            self._increase_workers(task_type, "performance analysis")
        elif should_decrease and not should_increase:
            self._decrease_workers(task_type, "performance analysis")

        self.last_adjustment[task_type] = current_time

    def _should_increase_workers(self, task_type: str, success_rate: float,
                                response_time: float, error_rate: float, throughput: float) -> bool:
        """Determine if workers should be increased for task type"""
        strategy = self.get_worker_strategy(task_type)

        # Don't increase if at maximum
        if strategy.current_workers >= strategy.max_workers:
            return False

        thresholds = self.thresholds['increase_workers']

        # Task-specific logic
        if task_type == 'guide_block':
            # Guide blocks: increase if performance is good and we can handle more load
            good_performance = (
                success_rate >= thresholds['success_rate'] and
                response_time <= thresholds['avg_response_time'] and
                error_rate <= 0.05 and
                throughput > 50000  # At least 50KB/s per request
            )
        else:  # series_details
            # Series details: more conservative - only increase if very stable
            good_performance = (
                success_rate >= 0.98 and  # Higher threshold for series
                response_time <= 1.5 and  # Lower response time threshold
                error_rate <= 0.02 and    # Very low error tolerance
                self._no_recent_429s(60)  # No 429s in last 60 seconds
            )

        if good_performance:
            # Check performance stability
            return self._is_performance_stable(task_type, min_samples=3)

        return False

    def _should_decrease_workers(self, task_type: str, success_rate: float,
                                response_time: float, error_rate: float) -> bool:
        """Determine if workers should be decreased for task type"""
        strategy = self.get_worker_strategy(task_type)

        # Don't decrease if at minimum
        if strategy.current_workers <= strategy.min_workers:
            return False

        thresholds = self.thresholds['decrease_workers']

        # Decrease if performance is poor in any critical metric
        poor_performance = (
            success_rate <= thresholds['success_rate'] or
            response_time >= thresholds['avg_response_time'] or
            error_rate >= thresholds['error_rate']
        )

        # Task-specific additional checks
        if task_type == 'series_details':
            # Series downloads are more sensitive to rate limiting
            if self._has_recent_429s(30):  # Any 429 in last 30 seconds
                poor_performance = True

        return poor_performance

    def _is_performance_stable(self, task_type: str, min_samples: int = 3) -> bool:
        """Check if recent performance has been stable for task type"""
        recent_metrics = [
            m for m in self.performance_history[-min_samples*2:]
            if m.task_type == task_type
        ]

        if len(recent_metrics) < min_samples:
            return False

        recent_metrics = recent_metrics[-min_samples:]

        # Check stability in success rate (variation < 5%)
        success_rates = [m.success_rate for m in recent_metrics]
        success_variation = max(success_rates) - min(success_rates)

        # Check stability in response time (variation < 1 second)
        response_times = [m.avg_response_time for m in recent_metrics]
        response_variation = max(response_times) - min(response_times)

        return success_variation < 0.05 and response_variation < 1.0

    def _no_recent_429s(self, seconds: int) -> bool:
        """Check if there have been no 429 errors in recent timeframe"""
        current_time = time.time()
        recent_errors = [
            m for m in self.performance_history
            if current_time - m.timestamp < seconds and m.error_rate > 0
        ]
        return len(recent_errors) == 0

    def _has_recent_429s(self, seconds: int) -> bool:
        """Check if there have been 429 errors in recent timeframe"""
        return not self._no_recent_429s(seconds)

    def _increase_workers(self, task_type: str, reason: str = "performance"):
        """Increase worker count for specific task type"""
        strategy = self.get_worker_strategy(task_type)
        old_count = strategy.current_workers
        new_count = min(strategy.max_workers, old_count + 1)

        if new_count > old_count:
            strategy.current_workers = new_count
            logging.info("Adaptive: Increased %s workers from %d to %d (%s)",
                        task_type, old_count, new_count, reason)

    def _decrease_workers(self, task_type: str, reason: str = "performance"):
        """Decrease worker count for specific task type"""
        strategy = self.get_worker_strategy(task_type)
        old_count = strategy.current_workers
        new_count = max(strategy.min_workers, old_count - 1)

        if new_count < old_count:
            strategy.current_workers = new_count
            logging.info("Adaptive: Decreased %s workers from %d to %d (%s)",
                        task_type, old_count, new_count, reason)

    def handle_rate_limit_event(self, reason: str):
        """Handle rate limit events with immediate worker reduction"""
        logging.warning("Adaptive strategy handling rate limit event: %s", reason)

        # Apply immediate reduction to both strategies
        for task_type in self.strategies:
            strategy = self.strategies[task_type]
            old_count = strategy.current_workers

            if reason == "waf_block":
                # WAF block: reduce to minimum immediately
                new_count = strategy.min_workers
            elif reason in ["rate_limit_429", "server_overload"]:
                # Rate limiting: aggressive reduction
                new_count = max(strategy.min_workers, old_count // 2)
            else:
                # Other reasons: conservative reduction
                new_count = max(strategy.min_workers, old_count - 1)

            if new_count != old_count:
                strategy.current_workers = new_count
                self.last_adjustment[task_type] = time.time()
                logging.warning("Rate limit adaptation: %s workers %d -> %d",
                              task_type, old_count, new_count)

    def get_optimal_workers(self, task_type: str) -> int:
        """Get current optimal number of workers for task type"""
        strategy = self.get_worker_strategy(task_type)
        return strategy.current_workers

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary across all task types"""
        if not self.performance_history:
            return {
                'status': 'no_data',
                'strategy_name': self.strategy_name,
                'global_max_workers': self.global_max_workers,
                'adaptive_enabled': self.enable_adaptive,
                'strategies': {
                    task_type: {
                        'current_workers': strategy.current_workers,
                        'max_workers': strategy.max_workers,
                        'rate_limit': strategy.rate_limit
                    }
                    for task_type, strategy in self.strategies.items()
                }
            }

        # Analyze performance by task type
        task_summaries = {}

        for task_type in self.strategies:
            task_metrics = [m for m in self.performance_history if m.task_type == task_type]

            if task_metrics:
                recent_metrics = task_metrics[-10:] if len(task_metrics) >= 10 else task_metrics

                avg_success_rate = sum(m.success_rate for m in recent_metrics) / len(recent_metrics)
                avg_response_time = sum(m.avg_response_time for m in recent_metrics) / len(recent_metrics)
                avg_throughput = sum(m.throughput for m in recent_metrics) / len(recent_metrics)

                task_summaries[task_type] = {
                    'samples': len(task_metrics),
                    'avg_success_rate': avg_success_rate,
                    'avg_response_time': avg_response_time,
                    'avg_throughput': avg_throughput,
                    'performance_trend': self._calculate_performance_trend(task_type),
                    'current_workers': self.strategies[task_type].current_workers,
                    'max_workers': self.strategies[task_type].max_workers
                }
            else:
                task_summaries[task_type] = {
                    'samples': 0,
                    'performance_trend': 'no_data',
                    'current_workers': self.strategies[task_type].current_workers,
                    'max_workers': self.strategies[task_type].max_workers
                }

        return {
            'status': 'active',
            'strategy_name': self.strategy_name,
            'global_max_workers': self.global_max_workers,
            'adaptive_enabled': self.enable_adaptive,
            'total_samples': len(self.performance_history),
            'task_summaries': task_summaries,
            'last_adjustments': self.last_adjustment.copy()
        }

    def _calculate_performance_trend(self, task_type: str) -> str:
        """Calculate performance trend for specific task type"""
        task_metrics = [m for m in self.performance_history if m.task_type == task_type]

        if len(task_metrics) < 6:
            return "insufficient_data"

        # Compare first half vs second half of recent samples
        recent = task_metrics[-10:]
        mid_point = len(recent) // 2

        first_half = recent[:mid_point]
        second_half = recent[mid_point:]

        if not first_half or not second_half:
            return "insufficient_data"

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

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get current strategy configuration information"""
        return {
            'name': self.strategy_name,
            'global_max_workers': self.global_max_workers,
            'adaptive_enabled': self.enable_adaptive,
            'strategies': {
                task_type: {
                    'initial_workers': strategy.initial_workers,
                    'current_workers': strategy.current_workers,
                    'max_workers': strategy.max_workers,
                    'min_workers': strategy.min_workers,
                    'rate_limit': strategy.rate_limit,
                    'timeout': strategy.timeout,
                    'conservative': strategy.conservative,
                    'burst_allowed': strategy.burst_allowed
                }
                for task_type, strategy in self.strategies.items()
            },
            'thresholds': self.thresholds,
            'adjustment_interval': self.adjustment_interval
        }

    def force_worker_adjustment(self, task_type: str, target_workers: int, reason: str = "manual"):
        """Manually force worker count adjustment for specific task type"""
        strategy = self.get_worker_strategy(task_type)
        target_workers = max(strategy.min_workers, min(strategy.max_workers, target_workers))

        old_count = strategy.current_workers
        strategy.current_workers = target_workers
        self.last_adjustment[task_type] = time.time()

        logging.info("Forced %s worker adjustment: %d -> %d (%s)",
                    task_type, old_count, target_workers, reason)

    def reset_performance_history(self):
        """Reset performance history (useful for new sessions)"""
        self.performance_history.clear()
        self.last_adjustment.clear()

        # Reset all strategies to initial values
        for strategy in self.strategies.values():
            strategy.current_workers = strategy.initial_workers

        logging.info("Adaptive strategy: Performance history and workers reset to initial values")

    def get_total_active_workers(self) -> int:
        """Get total number of currently active workers across all task types"""
        return sum(strategy.current_workers for strategy in self.strategies.values())

    def cleanup(self):
        """Clean up adaptive strategy resources"""
        logging.info("Cleaning up adaptive strategy")

        # Log final summary if we have data
        if self.performance_history:
            summary = self.get_performance_summary()
            logging.info("Adaptive strategy final summary:")
            logging.info("  Strategy: %s", summary['strategy_name'])
            logging.info("  Total adjustments: %d samples across %d task types",
                        summary['total_samples'], len(summary['task_summaries']))

            for task_type, task_summary in summary['task_summaries'].items():
                if task_summary['samples'] > 0:
                    logging.info("  %s: %s trend, %d/%d workers",
                                task_type, task_summary['performance_trend'],
                                task_summary['current_workers'], task_summary['max_workers'])


# Factory function for creating strategies
def create_adaptive_strategy(strategy_name: str = "balanced",
                           max_workers: int = 4,
                           enable_adaptive: bool = True) -> AdaptiveStrategy:
    """
    Factory function to create adaptive strategy with validation

    Args:
        strategy_name: Strategy preset name
        max_workers: Global maximum workers
        enable_adaptive: Enable adaptive adjustments

    Returns:
        Configured AdaptiveStrategy instance
    """
    valid_strategies = list(AdaptiveStrategy.STRATEGIES.keys())

    if strategy_name not in valid_strategies:
        logging.warning("Invalid strategy '%s', available: %s. Using 'balanced'",
                       strategy_name, valid_strategies)
        strategy_name = "balanced"

    if max_workers < 1:
        max_workers = 1
        enable_adaptive = False  # Can't adapt with only 1 worker
    elif max_workers > 10:
        logging.warning("Limiting max_workers to 10 to prevent server overload")
        max_workers = 10

    return AdaptiveStrategy(
        strategy_name=strategy_name,
        max_workers=max_workers,
        enable_adaptive=enable_adaptive
    )


def get_recommended_strategy(max_workers: int) -> str:
    """Get recommended strategy based on worker count"""
    if max_workers <= 2:
        return "conservative"
    elif max_workers <= 6:
        return "balanced"
    else:
        return "aggressive"
