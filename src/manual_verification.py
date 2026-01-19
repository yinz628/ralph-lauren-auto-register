"""
Manual Verification Handler module for Ralph Lauren Auto Register System.

Handles manual verification flow when PerimeterX challenges are detected,
pausing automation and waiting for user to complete verification manually.
"""

import time
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, List

from src.browser_controller import BrowserController


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class VerificationEvent:
    """验证事件记录
    
    Records details about a verification event including challenge type,
    timing information, and outcome status.
    
    Attributes:
        challenge_type: Type of challenge detected (e.g., "press-and-hold", "checkbox")
        start_time: Timestamp when verification started
        end_time: Timestamp when verification ended (None if still in progress)
        success: Whether verification completed successfully
        timeout: Whether verification timed out
        duration_seconds: Total duration of verification in seconds
        page_url: URL where challenge was detected
        failure_reason: Reason for failure if verification failed
    """
    challenge_type: str
    start_time: datetime
    page_url: str = ""
    end_time: Optional[datetime] = None
    success: bool = False
    timeout: bool = False
    duration_seconds: float = 0.0
    failure_reason: str = ""
    
    def to_dict(self) -> dict:
        """Convert VerificationEvent to dictionary format.
        
        Returns:
            Dictionary representation with ISO format timestamps
        """
        data = asdict(self)
        data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        return data
    
    def complete(self, success: bool, timeout: bool = False, failure_reason: str = "") -> None:
        """Mark verification event as complete.
        
        Args:
            success: Whether verification succeeded
            timeout: Whether verification timed out
            failure_reason: Reason for failure if applicable
        """
        self.end_time = datetime.now()
        self.success = success
        self.timeout = timeout
        self.failure_reason = failure_reason
        # Ensure duration is always non-negative (handle clock skew or test scenarios)
        duration = (self.end_time - self.start_time).total_seconds()
        self.duration_seconds = max(0.0, duration)


class BrowserCrashedError(Exception):
    """Exception raised when browser crashes during verification."""
    pass


class BrowserClosedError(Exception):
    """Exception raised when user closes browser during verification."""
    pass


class PageStateError(Exception):
    """Exception raised when page state doesn't match expected state."""
    pass


class LogWriteError(Exception):
    """Exception raised when log writing fails."""
    pass


class ManualVerificationHandler:
    """Handles manual verification flow for PerimeterX challenges.
    
    This class manages the detection of PerimeterX challenges, displays
    notifications to users, and monitors for verification completion.
    """
    
    # Common PerimeterX challenge selectors
    PX_SELECTORS = [
        '#px-captcha',
        '[data-testid="px-captcha"]',
        '.px-captcha-container',
        '#challenge-container',
        'iframe[src*="captcha"]',
        'div[id*="px-captcha"]',
        'div[class*="px-captcha"]',
    ]
    
    def __init__(self, browser: BrowserController, timeout: int = 120, max_attempts: int = 3):
        """Initialize ManualVerificationHandler.
        
        Args:
            browser: BrowserController instance for page interaction
            timeout: Maximum time to wait for manual verification in seconds (default 120)
            max_attempts: Maximum number of verification attempts allowed (default 3)
        """
        self.browser = browser
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.verification_count = 0
        self.events: List[VerificationEvent] = []
        self._fallback_log_messages: List[str] = []  # Fallback for when file logging fails
    
    def detect_challenge(self) -> Optional[str]:
        """Detect PerimeterX challenge on the current page.
        
        Checks for common PerimeterX challenge elements and identifies
        the challenge type if present. Detection completes within 3 seconds.
        
        Returns:
            Challenge type string if detected, None otherwise
            
        Requirements: 1.1, 1.2, 1.3, 1.4
        """
        if not self.browser.page:
            return None
        
        detection_start = time.time()
        detection_timeout = 3.0  # 3 seconds timeout for detection
        
        try:
            # Check each selector with a short timeout
            for selector in self.PX_SELECTORS:
                # Check if we've exceeded the detection timeout
                elapsed = time.time() - detection_start
                if elapsed >= detection_timeout:
                    logger.debug(f"Challenge detection timeout reached after {elapsed:.2f}s")
                    return None
                
                try:
                    # Use a short timeout for each selector check
                    remaining_time = max(100, int((detection_timeout - elapsed) * 1000))
                    element = self.browser.page.locator(selector)
                    
                    # Quick check with timeout
                    if element.count() > 0:
                        # Check visibility with remaining timeout
                        try:
                            element.first.wait_for(state="visible", timeout=remaining_time)
                            # Determine challenge type based on selector
                            if 'captcha' in selector.lower():
                                challenge_type = "captcha"
                            elif 'challenge' in selector.lower():
                                challenge_type = "challenge"
                            else:
                                challenge_type = "unknown"
                            
                            logger.info(f"PerimeterX challenge detected: {challenge_type} (selector: {selector})")
                            return challenge_type
                        except Exception:
                            # Not visible, continue to next selector
                            continue
                except Exception:
                    # Element not found or error checking, continue
                    continue
            
            # No challenge detected within timeout
            return None
            
        except Exception as e:
            logger.warning(f"Error during challenge detection: {e}")
            return None
    
    def wait_for_manual_verification(self, expected_url_pattern: str) -> bool:
        """Wait for user to complete manual verification.
        
        Monitors the page for signs of verification completion:
        - URL changes to match expected pattern
        - Challenge elements disappear from page
        
        Args:
            expected_url_pattern: URL pattern that indicates successful verification
            
        Returns:
            True if verification completed successfully, False if timeout
            
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2
        """
        if not self.browser.page:
            return False
        
        start_time = time.time()
        check_interval = 1.0  # Check every second
        
        while True:
            elapsed = time.time() - start_time
            
            # Check for timeout
            if elapsed >= self.timeout:
                logger.warning(f"Manual verification timed out after {elapsed:.1f} seconds")
                return False
            
            try:
                # Check if URL matches expected pattern
                current_url = self.browser.current_url
                if expected_url_pattern in current_url:
                    logger.info(f"Verification complete - URL changed to: {current_url}")
                    return True
                
                # Check if challenge elements disappeared
                challenge_present = False
                for selector in self.PX_SELECTORS:
                    try:
                        element = self.browser.page.locator(selector)
                        if element.count() > 0 and element.first.is_visible():
                            challenge_present = True
                            break
                    except Exception:
                        continue
                
                if not challenge_present:
                    logger.info("Verification complete - challenge elements disappeared")
                    return True
                
            except Exception as e:
                logger.warning(f"Error during verification monitoring: {e}")
            
            # Wait before next check
            time.sleep(check_interval)
    
    def display_notification(self, challenge_type: str, remaining_time: Optional[int] = None) -> None:
        """Display notification to user about manual verification requirement.
        
        Args:
            challenge_type: Type of challenge detected
            remaining_time: Optional remaining time in seconds
            
        Requirements: 2.2, 2.4
        """
        if remaining_time is None:
            remaining_time = self.timeout
        
        notification = f"""
╔════════════════════════════════════════════════════════════╗
║  PerimeterX 验证挑战检测                                    ║
║                                                            ║
║  检测到挑战类型: {challenge_type:<40} ║
║                                                            ║
║  请在浏览器中手动完成验证                                    ║
║  验证成功后页面将自动跳转                                    ║
║                                                            ║
║  超时时间: {self.timeout} 秒                                           ║
║  剩余时间: {remaining_time} 秒                                           ║
╚════════════════════════════════════════════════════════════╝
        """
        print(notification)
        logger.info(f"[MANUAL_VERIFICATION] Challenge detected: {challenge_type}")
        logger.info(f"[MANUAL_VERIFICATION] Waiting for user to complete verification (timeout: {self.timeout}s)")
    
    def log_challenge_detection(self, challenge_type: str, page_url: str) -> VerificationEvent:
        """Log challenge detection event.
        
        Creates and logs a new verification event when a challenge is detected.
        
        Args:
            challenge_type: Type of challenge detected
            page_url: URL where challenge was detected
            
        Returns:
            VerificationEvent instance for tracking
            
        Requirements: 7.1, 2.5
        """
        event = VerificationEvent(
            challenge_type=challenge_type,
            start_time=datetime.now(),
            page_url=page_url
        )
        self.events.append(event)
        
        logger.info(
            f"[MANUAL_VERIFICATION] Challenge detected: {challenge_type} "
            f"at {event.start_time.isoformat()} on {page_url}"
        )
        
        return event
    
    def log_verification_entry(self, timeout_duration: int) -> None:
        """Log entry into manual verification mode.
        
        Args:
            timeout_duration: Timeout duration in seconds
            
        Requirements: 7.2, 2.5
        """
        logger.info(
            f"[MANUAL_VERIFICATION] Entering manual verification mode "
            f"(timeout: {timeout_duration}s)"
        )
    
    def log_verification_completion(self, event: VerificationEvent, duration: float) -> None:
        """Log successful verification completion.
        
        Args:
            event: VerificationEvent to complete
            duration: Duration in seconds
            
        Requirements: 7.3, 2.5
        """
        event.complete(success=True, timeout=False, failure_reason="")
        
        logger.info(
            f"[MANUAL_VERIFICATION] Verification completed successfully in {duration:.1f}s"
        )
    
    def log_verification_timeout(self, event: VerificationEvent, duration: float) -> None:
        """Log verification timeout event.
        
        Args:
            event: VerificationEvent to mark as timed out
            duration: Duration in seconds before timeout
            
        Requirements: 7.4, 2.5
        """
        event.complete(success=False, timeout=True, failure_reason="timeout")
        
        logger.warning(
            f"[MANUAL_VERIFICATION] Verification timed out after {duration:.1f}s"
        )
    
    def log_verification_failure(self, event: VerificationEvent, failure_reason: str) -> None:
        """Log verification failure event.
        
        Args:
            event: VerificationEvent to mark as failed
            failure_reason: Reason for failure
            
        Requirements: 7.5, 2.5
        """
        event.complete(success=False, timeout=False, failure_reason=failure_reason)
        
        logger.error(
            f"[MANUAL_VERIFICATION] Verification failed: {failure_reason}"
        )
    
    def log_event(self, event: VerificationEvent) -> None:
        """Log a verification event.
        
        This is a legacy method that logs events based on their state.
        Prefer using specific logging methods (log_challenge_detection,
        log_verification_completion, etc.) for new code.
        
        Args:
            event: VerificationEvent to log
            
        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 2.5
        """
        self.events.append(event)
        
        if event.end_time is None:
            # Event started
            logger.info(
                f"[MANUAL_VERIFICATION] Challenge detected: {event.challenge_type} "
                f"at {event.start_time.isoformat()} on {event.page_url}"
            )
        elif event.success:
            # Event completed successfully
            logger.info(
                f"[MANUAL_VERIFICATION] Verification completed successfully in {event.duration_seconds:.1f}s"
            )
        elif event.timeout:
            # Event timed out
            logger.warning(
                f"[MANUAL_VERIFICATION] Verification timed out after {event.duration_seconds:.1f}s"
            )
        else:
            # Event failed
            logger.error(
                f"[MANUAL_VERIFICATION] Verification failed: {event.failure_reason}"
            )
    
    def increment_verification_count(self) -> int:
        """Increment and return the verification count.
        
        Returns:
            Current verification count after increment
            
        Requirements: 8.1, 8.2
        """
        self.verification_count += 1
        logger.info(f"[MANUAL_VERIFICATION] Verification attempt {self.verification_count}/{self.max_attempts}")
        return self.verification_count
    
    def check_max_attempts_exceeded(self) -> bool:
        """Check if maximum verification attempts have been exceeded.
        
        Returns:
            True if max attempts exceeded, False otherwise
            
        Requirements: 8.3, 8.4
        """
        exceeded = self.verification_count > self.max_attempts
        if exceeded:
            logger.error(
                f"[MANUAL_VERIFICATION] Maximum verification attempts ({self.max_attempts}) exceeded. "
                f"Current count: {self.verification_count}"
            )
        return exceeded
    
    def reset_verification_count(self) -> None:
        """Reset verification count to zero.
        
        This should be called at the start of a new iteration or registration flow.
        
        Requirements: 8.1, 8.2
        """
        logger.debug(f"[MANUAL_VERIFICATION] Resetting verification count from {self.verification_count} to 0")
        self.verification_count = 0
    
    def handle_verification_attempt(self, challenge_type: str, page_url: str, expected_url_pattern: str) -> bool:
        """Handle a single verification attempt with counting and max attempts checking.
        
        This method combines verification counting, max attempts checking, and the
        actual verification wait logic into a single cohesive flow.
        
        Args:
            challenge_type: Type of challenge detected
            page_url: URL where challenge was detected
            expected_url_pattern: Expected URL pattern after successful verification
            
        Returns:
            True if verification succeeded, False if failed or max attempts exceeded
            
        Raises:
            Exception: If max attempts exceeded with failure reason
            
        Requirements: 8.1, 8.2, 8.3, 8.4
        """
        # Increment verification count
        self.increment_verification_count()
        
        # Check if max attempts exceeded (count > max_attempts means we've exceeded)
        if self.verification_count > self.max_attempts:
            # Log failure event
            event = self.log_challenge_detection(challenge_type, page_url)
            self.log_verification_failure(event, "max_attempts_exceeded")
            return False
        
        # Log challenge detection
        event = self.log_challenge_detection(challenge_type, page_url)
        
        # Display notification
        self.display_notification(challenge_type)
        
        # Log entry into verification mode
        self.log_verification_entry(self.timeout)
        
        # Wait for manual verification
        start_time = time.time()
        success = self.wait_for_manual_verification(expected_url_pattern)
        duration = time.time() - start_time
        
        # Log result
        if success:
            self.log_verification_completion(event, duration)
        else:
            self.log_verification_timeout(event, duration)
        
        return success
    
    def verify_page_state(self, expected_url_pattern: str) -> bool:
        """Verify that the current page state matches expected state after verification.
        
        This method checks that the page has successfully transitioned to the expected
        state after manual verification completion. It verifies:
        - Current URL matches the expected pattern
        - No challenge elements are present
        - Page is in a stable state
        
        Args:
            expected_url_pattern: Expected URL pattern that indicates successful state
            
        Returns:
            True if page state matches expected state, False otherwise
            
        Requirements: 5.1, 5.3
        """
        if not self.browser.page:
            logger.warning("[MANUAL_VERIFICATION] Cannot verify page state - no browser page available")
            return False
        
        try:
            # Check if URL matches expected pattern
            current_url = self.browser.current_url
            if expected_url_pattern not in current_url:
                logger.warning(
                    f"[MANUAL_VERIFICATION] Page state verification failed - "
                    f"URL does not match expected pattern. "
                    f"Current: {current_url}, Expected pattern: {expected_url_pattern}"
                )
                return False
            
            # Check that no challenge elements are present
            for selector in self.PX_SELECTORS:
                try:
                    element = self.browser.page.locator(selector)
                    if element.count() > 0 and element.first.is_visible():
                        logger.warning(
                            f"[MANUAL_VERIFICATION] Page state verification failed - "
                            f"challenge element still present: {selector}"
                        )
                        return False
                except Exception:
                    # Element not found or not visible - this is good
                    continue
            
            # Page state is valid
            logger.info(
                f"[MANUAL_VERIFICATION] Page state verified successfully - "
                f"URL: {current_url}"
            )
            return True
            
        except Exception as e:
            logger.error(
                f"[MANUAL_VERIFICATION] Error during page state verification: {e}"
            )
            return False
    
    def log_flow_resume_success(self, event: VerificationEvent, next_step: str) -> None:
        """Log successful flow resume after verification completion.
        
        This method logs that the automated flow is resuming after successful
        manual verification, including information about the next step.
        
        Args:
            event: VerificationEvent that completed successfully
            next_step: Description of the next step in the automated flow
            
        Requirements: 5.1, 5.2, 2.5
        """
        logger.info(
            f"[MANUAL_VERIFICATION] Flow resuming after successful verification. "
            f"Challenge type: {event.challenge_type}, "
            f"Duration: {event.duration_seconds:.1f}s, "
            f"Next step: {next_step}"
        )
    
    def setup_post_verification_monitoring(self) -> None:
        """Setup monitoring for subsequent challenges after verification completes.
        
        This method prepares the handler to detect and handle any additional
        challenges that may appear after the current verification completes.
        It ensures the system remains ready to pause automation again if needed.
        
        Requirements: 5.5
        """
        logger.debug(
            "[MANUAL_VERIFICATION] Post-verification monitoring active - "
            "ready to detect subsequent challenges"
        )
        # Note: The handler is always ready to detect challenges via detect_challenge()
        # This method serves as a marker that monitoring is active and logs the state
    
    def resume_flow_after_verification(self, event: VerificationEvent, expected_url_pattern: str, next_step: str = "continue") -> bool:
        """Resume automated flow after successful manual verification.
        
        This method orchestrates the flow resume process:
        1. Verifies the page state matches expected state
        2. Logs the successful flow resume
        3. Sets up monitoring for subsequent challenges
        
        Args:
            event: VerificationEvent that completed successfully
            expected_url_pattern: Expected URL pattern for verification
            next_step: Description of the next step (default: "continue")
            
        Returns:
            True if flow can resume successfully, False if state verification fails
            
        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
        """
        # Verify page state matches expected state
        if not self.verify_page_state(expected_url_pattern):
            logger.error(
                "[MANUAL_VERIFICATION] Cannot resume flow - page state verification failed"
            )
            return False
        
        # Log successful flow resume
        self.log_flow_resume_success(event, next_step)
        
        # Setup monitoring for subsequent challenges
        self.setup_post_verification_monitoring()
        
        logger.info(
            "[MANUAL_VERIFICATION] Flow resume complete - automation continuing"
        )
        
        return True
    
    def _check_browser_alive(self) -> bool:
        """Check if browser is still alive and responsive.
        
        Returns:
            True if browser is alive, False otherwise
            
        Requirements: 4.4, 4.5
        """
        try:
            if not self.browser or not self.browser.page:
                return False
            
            # Try to access page URL to verify browser is responsive
            _ = self.browser.page.url
            return True
        except Exception as e:
            logger.debug(f"Browser alive check failed: {e}")
            return False
    
    def handle_browser_crash(self, event: VerificationEvent) -> None:
        """Handle browser crash during verification.
        
        Logs the crash event and marks verification as failed.
        
        Args:
            event: VerificationEvent to mark as failed
            
        Raises:
            BrowserCrashedError: Always raised after logging
            
        Requirements: 4.4, 4.5
        """
        failure_reason = "browser_crashed"
        self.log_verification_failure(event, failure_reason)
        
        logger.error(
            "[MANUAL_VERIFICATION] Browser crashed during verification. "
            "Verification cannot continue."
        )
        
        raise BrowserCrashedError("Browser crashed during manual verification")
    
    def handle_browser_closed(self, event: VerificationEvent) -> None:
        """Handle user closing browser during verification.
        
        Logs the event and marks verification as failed.
        
        Args:
            event: VerificationEvent to mark as failed
            
        Raises:
            BrowserClosedError: Always raised after logging
            
        Requirements: 4.4, 4.5
        """
        failure_reason = "browser_closed_by_user"
        self.log_verification_failure(event, failure_reason)
        
        logger.warning(
            "[MANUAL_VERIFICATION] User closed browser during verification. "
            "Verification aborted."
        )
        
        raise BrowserClosedError("User closed browser during manual verification")
    
    def handle_page_state_mismatch(self, expected_state: str, actual_state: str) -> bool:
        """Handle page state mismatch after verification.
        
        Attempts to recover by refreshing the page and re-checking state.
        
        Args:
            expected_state: Expected page state (URL pattern or description)
            actual_state: Actual page state found
            
        Returns:
            True if recovery successful, False otherwise
            
        Requirements: 4.4, 4.5
        """
        logger.warning(
            f"[MANUAL_VERIFICATION] Page state mismatch detected. "
            f"Expected: {expected_state}, Actual: {actual_state}"
        )
        
        try:
            # Attempt recovery by refreshing page
            logger.info("[MANUAL_VERIFICATION] Attempting recovery by refreshing page...")
            
            if not self._check_browser_alive():
                logger.error("[MANUAL_VERIFICATION] Browser not responsive, cannot refresh")
                return False
            
            self.browser.refresh()
            time.sleep(2)  # Wait for page to load
            
            # Re-check state after refresh
            current_url = self.browser.current_url
            if expected_state in current_url:
                logger.info(
                    "[MANUAL_VERIFICATION] Recovery successful - page state now matches expected"
                )
                return True
            else:
                logger.error(
                    f"[MANUAL_VERIFICATION] Recovery failed - page state still mismatched. "
                    f"Current URL: {current_url}"
                )
                return False
                
        except Exception as e:
            logger.error(
                f"[MANUAL_VERIFICATION] Error during page state recovery: {e}"
            )
            return False
    
    def _safe_log(self, message: str, level: str = "info") -> None:
        """Safely log a message with fallback to console if file logging fails.
        
        Args:
            message: Message to log
            level: Log level (info, warning, error, debug)
            
        Requirements: 4.4, 4.5
        """
        try:
            # Try normal logging
            log_func = getattr(logger, level, logger.info)
            log_func(message)
        except Exception as e:
            # Fallback to console output
            print(f"[LOG_FALLBACK] {level.upper()}: {message}")
            print(f"[LOG_FALLBACK] Logging error: {e}")
            
            # Store in fallback buffer
            self._fallback_log_messages.append(f"{level.upper()}: {message}")
    
    def get_fallback_logs(self) -> List[str]:
        """Get fallback log messages when file logging failed.
        
        Returns:
            List of fallback log messages
            
        Requirements: 4.4, 4.5
        """
        return self._fallback_log_messages.copy()
    
    def clear_fallback_logs(self) -> None:
        """Clear fallback log messages.
        
        Requirements: 4.4, 4.5
        """
        self._fallback_log_messages.clear()
    
    def wait_for_manual_verification_with_error_handling(
        self, 
        expected_url_pattern: str,
        event: VerificationEvent
    ) -> bool:
        """Wait for manual verification with comprehensive error handling.
        
        This is an enhanced version of wait_for_manual_verification that includes
        error handling for browser crashes, user closing browser, and other errors.
        
        Args:
            expected_url_pattern: URL pattern that indicates successful verification
            event: VerificationEvent to update on errors
            
        Returns:
            True if verification completed successfully, False if timeout or error
            
        Raises:
            BrowserCrashedError: If browser crashes during verification
            BrowserClosedError: If user closes browser during verification
            
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.4, 4.5
        """
        if not self.browser.page:
            self._safe_log(
                "[MANUAL_VERIFICATION] Cannot wait for verification - no browser page available",
                "error"
            )
            return False
        
        start_time = time.time()
        check_interval = 1.0  # Check every second
        last_browser_check = start_time
        browser_check_interval = 5.0  # Check browser health every 5 seconds
        
        while True:
            elapsed = time.time() - start_time
            
            # Check for timeout
            if elapsed >= self.timeout:
                self._safe_log(
                    f"[MANUAL_VERIFICATION] Manual verification timed out after {elapsed:.1f} seconds",
                    "warning"
                )
                return False
            
            # Periodic browser health check
            if time.time() - last_browser_check >= browser_check_interval:
                if not self._check_browser_alive():
                    # Browser is not responsive
                    try:
                        # Try one more time to confirm
                        time.sleep(1)
                        if not self._check_browser_alive():
                            # Browser definitely crashed or was closed
                            self.handle_browser_crash(event)
                    except Exception:
                        self.handle_browser_crash(event)
                
                last_browser_check = time.time()
            
            try:
                # Check if URL matches expected pattern
                current_url = self.browser.current_url
                if expected_url_pattern in current_url:
                    self._safe_log(
                        f"[MANUAL_VERIFICATION] Verification complete - URL changed to: {current_url}",
                        "info"
                    )
                    return True
                
                # Check if challenge elements disappeared
                challenge_present = False
                for selector in self.PX_SELECTORS:
                    try:
                        element = self.browser.page.locator(selector)
                        if element.count() > 0 and element.first.is_visible():
                            challenge_present = True
                            break
                    except Exception:
                        continue
                
                if not challenge_present:
                    self._safe_log(
                        "[MANUAL_VERIFICATION] Verification complete - challenge elements disappeared",
                        "info"
                    )
                    return True
                
            except AttributeError as e:
                # Browser page might have been closed
                self._safe_log(
                    f"[MANUAL_VERIFICATION] Browser page access error: {e}",
                    "error"
                )
                self.handle_browser_closed(event)
            except Exception as e:
                self._safe_log(
                    f"[MANUAL_VERIFICATION] Error during verification monitoring: {e}",
                    "warning"
                )
                # Continue monitoring unless it's a critical error
                if "browser" in str(e).lower() or "page" in str(e).lower():
                    # Might be browser crash
                    if not self._check_browser_alive():
                        self.handle_browser_crash(event)
            
            # Wait before next check
            time.sleep(check_interval)
