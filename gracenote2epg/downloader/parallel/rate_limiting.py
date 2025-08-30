"""
gracenote2epg.downloader.parallel.rate_limiting - Rate limiting and WAF detection

Thread-safe rate limiting and Web Application Firewall detection for download control.
"""

import logging
import random
import threading
import time
from typing import Optional


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

    def get_current_rate(self) -> float:
        """Get current rate limit setting"""
        with self.lock:
            return self.max_requests_per_second


class WAFDetector:
    """Web Application Firewall detection and handling"""

    def __init__(self):
        self.waf_indicators = [
            "Human Verification",
            "captcha-container",
            "AwsWafIntegration",
            "403 Forbidden",
            "Access Denied",
            "challenge.js",
            "cloudflare",
            "DDoS protection",
            "Rate limit exceeded",
            "Too many requests"
        ]
        self.waf_event = threading.Event()
        self.waf_event.set()  # Initially clear
        self.waf_blocks = 0
        self.lock = threading.Lock()

    def is_waf_blocked(self, response_text: str, status_code: Optional[int] = None) -> bool:
        """Detect WAF blocking from response content or status code"""
        # Check status code first
        if status_code in [403, 429, 503]:
            return True

        # Check response content for WAF indicators
        if response_text:
            return any(indicator.lower() in response_text.lower()
                      for indicator in self.waf_indicators)

        return False

    def handle_waf_block(self, extra_delay_range: tuple = (3, 8)) -> float:
        """Handle WAF blocking with appropriate backoff"""
        with self.lock:
            self.waf_blocks += 1

        if self.waf_event.is_set():
            self.waf_event.clear()

            extra_delay = random.uniform(*extra_delay_range)
            logging.warning("WAF block detected! Global backoff for %.1f seconds", extra_delay)

            def clear_waf_block():
                time.sleep(extra_delay)
                self.waf_event.set()
                logging.info("WAF backoff completed")

            threading.Thread(target=clear_waf_block, daemon=True).start()
            return extra_delay

        return 0.0

    def wait_for_clearance(self, timeout: float = 5.0) -> bool:
        """Wait for WAF clearance with timeout"""
        return self.waf_event.wait(timeout=timeout)

    def get_waf_stats(self) -> dict:
        """Get WAF detection statistics"""
        with self.lock:
            return {
                'total_blocks': self.waf_blocks,
                'currently_blocked': not self.waf_event.is_set()
            }


class AdaptiveRateController:
    """Adaptive rate controller that manages both rate limiting and WAF detection"""

    def __init__(self, initial_rate: float = 2.0):
        self.rate_limiter = RateLimiter(initial_rate)
        self.waf_detector = WAFDetector()
        self.consecutive_429s = 0
        self.last_429_time = 0
        self.worker_reduction_active = False
        self.lock = threading.Lock()

        # Enhanced tracking for worker reduction triggers
        self.worker_reduction_callback = None
        self.reduction_threshold = 2  # Trigger after 2 consecutive 429s

    def set_worker_reduction_callback(self, callback):
        """Set callback to trigger worker reduction"""
        self.worker_reduction_callback = callback
        logging.debug("Worker reduction callback set for AdaptiveRateController")

    def before_request(self) -> bool:
        """Call before making a request. Returns True if request should proceed."""
        # Wait for WAF clearance
        if not self.waf_detector.wait_for_clearance():
            return False

        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        return True

    def after_request(self, success: bool, response_text: str = "",
                     status_code: Optional[int] = None, error: Optional[str] = None):
        """Call after request completion to update adaptive behavior"""

        # Check for WAF blocking first
        if status_code == 403 or self.waf_detector.is_waf_blocked(response_text, status_code):
            self.waf_detector.handle_waf_block()
            # Trigger immediate worker reduction for WAF blocks
            if self.worker_reduction_callback:
                logging.warning("WAF block detected - triggering worker reduction")
                self.worker_reduction_callback("waf_block")
            return

        # Check for rate limiting with aggressive response
        if status_code == 429 or (error and ("429" in error or "Too Many Requests" in error.lower())):
            self._handle_429_error()
            return

        # Check for other server errors that might indicate overload
        if status_code in [502, 503, 504] or (error and any(code in error for code in ["502", "503", "504"])):
            self._handle_server_overload()
            return

        # Normal success/failure handling
        self.rate_limiter.adjust_rate(success)

        # Reset consecutive 429s on success
        if success:
            with self.lock:
                if self.consecutive_429s > 0:
                    old_count = self.consecutive_429s
                    self.consecutive_429s = max(0, self.consecutive_429s - 1)
                    if old_count > 0 and self.consecutive_429s == 0:
                        logging.info("Rate limiting subsided - consecutive 429s reset from %d", old_count)

    def _handle_429_error(self):
        """Handle HTTP 429 rate limit errors with aggressive worker reduction"""
        current_time = time.time()

        with self.lock:
            self.consecutive_429s += 1
            self.last_429_time = current_time

            logging.warning("HTTP 429 rate limit error #%d detected", self.consecutive_429s)

            # Aggressive rate reduction for ANY 429 error
            if self.consecutive_429s == 1:
                # First 429: reduce rate by 50%
                reduction_factor = 0.5
                new_rate = max(0.5, self.rate_limiter.max_requests_per_second * reduction_factor)

                logging.warning("First 429 error - reducing rate to %.1f req/s", new_rate)
                self.rate_limiter.max_requests_per_second = new_rate
                self.rate_limiter.min_interval = 1.0 / new_rate

            elif self.consecutive_429s >= self.reduction_threshold:
                # Multiple 429s: aggressive reduction and trigger worker reduction
                reduction_factor = min(0.1, 0.3 ** (self.consecutive_429s - 1))
                new_rate = max(0.2, self.rate_limiter.max_requests_per_second * reduction_factor)

                logging.warning(
                    "Multiple 429 errors (%d consecutive) - aggressive rate reduction to %.1f req/s",
                    self.consecutive_429s, new_rate
                )

                self.rate_limiter.max_requests_per_second = new_rate
                self.rate_limiter.min_interval = 1.0 / new_rate

                # Trigger worker reduction
                if self.worker_reduction_callback:
                    logging.warning("429 threshold exceeded - triggering worker reduction")
                    self.worker_reduction_callback("rate_limit_429")
                    self.worker_reduction_active = True

    def _handle_server_overload(self):
        """Handle server overload errors (502, 503, 504)"""
        with self.lock:
            logging.warning("Server overload detected (502/503/504) - reducing rate and workers")

            # Reduce rate significantly
            new_rate = max(0.2, self.rate_limiter.max_requests_per_second * 0.3)
            self.rate_limiter.max_requests_per_second = new_rate
            self.rate_limiter.min_interval = 1.0 / new_rate

            # Trigger worker reduction
            if self.worker_reduction_callback:
                logging.warning("Server overload - triggering worker reduction")
                self.worker_reduction_callback("server_overload")
                self.worker_reduction_active = True

    def try_recover_rate(self):
        """Try to recover rate if no recent errors"""
        current_time = time.time()

        with self.lock:
            # Only try recovery if we've been stable for a while
            if (self.consecutive_429s > 0 and
                current_time - self.last_429_time > 60):  # Increased to 60 seconds

                self.consecutive_429s = max(0, self.consecutive_429s - 1)

                # Gradual rate increase only when completely clear
                if self.consecutive_429s == 0:
                    current_rate = self.rate_limiter.max_requests_per_second
                    new_rate = min(5.0, current_rate * 1.1)  # Conservative increase

                    if new_rate > current_rate:
                        logging.info("Rate limiting recovery - gradually increasing rate to %.1f req/s", new_rate)
                        self.rate_limiter.max_requests_per_second = new_rate
                        self.rate_limiter.min_interval = 1.0 / new_rate

                        # Allow worker recovery after rate recovery
                        if self.worker_reduction_active and current_time - self.last_429_time > 120:
                            self.worker_reduction_active = False
                            logging.info("Rate controller: worker reduction period ended")

    def get_comprehensive_stats(self) -> dict:
        """Get comprehensive statistics from all components"""
        waf_stats = self.waf_detector.get_waf_stats()

        with self.lock:
            return {
                'current_rate': self.rate_limiter.get_current_rate(),
                'consecutive_429s': self.consecutive_429s,
                'worker_reduction_active': self.worker_reduction_active,
                'waf_blocks': waf_stats['total_blocks'],
                'waf_currently_blocked': waf_stats['currently_blocked'],
                'last_429_time': self.last_429_time,
                'reduction_threshold': self.reduction_threshold
            }

    def force_worker_reduction(self, reason: str = "manual"):
        """Force worker reduction (for testing or manual intervention)"""
        if self.worker_reduction_callback:
            logging.warning("Forcing worker reduction: %s", reason)
            self.worker_reduction_callback(reason)
            with self.lock:
                self.worker_reduction_active = True
