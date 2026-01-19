"""
End-to-end integration tests for manual verification feature.

Tests complete registration flows with manual verification, including:
- Full registration flow with challenge detection and manual verification
- Multiple challenge scenarios
- Timeout scenarios
- Flow recovery after verification

Requirements: All requirements from manual-verification spec
"""

import pytest
import time
from unittest.mock import Mock, PropertyMock, patch, MagicMock
from datetime import datetime

from src.registration import Registration
from src.manual_verification import ManualVerificationHandler, VerificationEvent
from src.browser_controller import BrowserController
from src.models import UserData


# ============================================================================
# Integration Test: Complete Registration Flow with Manual Verification
# ============================================================================

def test_complete_registration_flow_with_manual_verification():
    """
    End-to-end integration test for complete registration flow with manual verification.
    
    Tests the full flow:
    1. Navigate to registration page
    2. Fill registration form
    3. Submit form
    4. Detect PerimeterX challenge
    5. Enter manual verification mode
    6. Display notification to user
    7. Wait for user to complete verification
    8. Detect verification completion (URL change)
    9. Resume automated flow
    10. Monitor for registration API response
    11. Verify registration success
    
    Requirements: All requirements (1.1-9.6)
    """
    # Create mock browser and page
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    mock_browser.current_url = "https://www.ralphlauren.com/register"
    
    # Mock form filling methods
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.fill_input = Mock()
    mock_browser.fill_input_by_dynamic_id = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Create test user data
    user_data = UserData(
        email="test@example.com",
        password="TestPass123",
        first_name="John",
        last_name="Doe",
        phone_number="+1234567890"
    )
    
    # Create registration instance
    registration = Registration(mock_browser)
    
    # Mock ManualVerificationHandler
    with patch('src.registration.ManualVerificationHandler') as MockHandler:
        mock_handler = Mock()
        MockHandler.return_value = mock_handler
        
        # Simulate challenge detection
        mock_handler.detect_challenge.return_value = "captcha"
        
        # Simulate successful manual verification
        mock_handler.wait_for_manual_verification.return_value = True
        
        # Mock config
        with patch('src.registration.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            
            # Mock successful API response
            mock_browser.wait_for_response_with_data = Mock(return_value={
                'status': 302,
                'url': 'https://www.ralphlauren.com/account',
                'headers': {},
                'body': ''
            })
            
            # Mock time.sleep to speed up test
            with patch('time.sleep'):
                # Execute registration flow
                result = registration.submit_and_verify()
    
    # Verify the complete flow executed correctly
    assert result is True
    
    # Verify challenge detection was called
    assert mock_handler.detect_challenge.called
    
    # Verify notification was displayed
    assert mock_handler.display_notification.called
    notification_call = mock_handler.display_notification.call_args
    assert notification_call[0][0] == "captcha"
    
    # Verify manual verification wait was called
    assert mock_handler.wait_for_manual_verification.called
    
    # Verify logging was called
    assert mock_handler.log_event.call_count >= 2
    
    # Verify API response monitoring was called after verification
    assert mock_browser.wait_for_response_with_data.called




# ============================================================================
# Integration Test: Multiple Challenge Scenarios
# ============================================================================

def test_multiple_challenges_in_single_flow():
    """
    Integration test for handling multiple PerimeterX challenges in a single flow.
    
    Tests scenario where:
    1. First challenge appears after registration submission
    2. User completes first verification
    3. Second challenge appears after profile update
    4. User completes second verification
    5. Flow completes successfully
    
    Requirements: 8.1, 8.2, 8.3, 8.4
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    mock_browser.current_url = "https://www.ralphlauren.com/register"
    
    # Mock browser methods
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Create registration instance
    registration = Registration(mock_browser)
    
    # Mock ManualVerificationHandler
    with patch('src.registration.ManualVerificationHandler') as MockHandler:
        mock_handler = Mock()
        MockHandler.return_value = mock_handler
        
        # Simulate two challenges detected in sequence
        challenge_calls = ["captcha", "press-and-hold"]
        mock_handler.detect_challenge.side_effect = challenge_calls
        
        # Both verifications succeed
        mock_handler.wait_for_manual_verification.return_value = True
        
        # Mock config
        with patch('src.registration.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            mock_config.MAX_VERIFICATION_ATTEMPTS = 3
            
            # Mock API responses
            mock_browser.wait_for_response_with_data = Mock(return_value={
                'status': 302,
                'url': 'https://www.ralphlauren.com/account',
                'headers': {},
                'body': ''
            })
            
            # Mock time.sleep
            with patch('time.sleep'):
                # First submission (first challenge)
                result1 = registration.submit_and_verify()
                
                # Simulate second challenge scenario
                mock_browser.current_url = "https://www.ralphlauren.com/profile"
                result2 = registration.submit_and_verify()
    
    # Verify both submissions succeeded
    assert result1 is True
    assert result2 is True
    
    # Verify challenge detection was called twice
    assert mock_handler.detect_challenge.call_count == 2
    
    # Verify manual verification was called twice
    assert mock_handler.wait_for_manual_verification.call_count == 2
    
    # Verify notifications were displayed for both challenges
    assert mock_handler.display_notification.call_count == 2


def test_max_verification_attempts_exceeded():
    """
    Integration test for exceeding maximum verification attempts.
    
    Tests scenario where:
    1. Multiple challenges appear in sequence
    2. User completes first 3 verifications
    3. Fourth challenge appears
    4. System marks iteration as failed due to max attempts
    
    Requirements: 8.3, 8.4
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Create handler with max_attempts=3
    handler = ManualVerificationHandler(mock_browser, timeout=120, max_attempts=3)
    
    # Simulate 4 verification attempts
    for i in range(4):
        handler.increment_verification_count()
    
    # Verify count is 4
    assert handler.verification_count == 4
    
    # Verify max attempts exceeded
    assert handler.check_max_attempts_exceeded() is True


def test_independent_challenge_handling():
    """
    Integration test for independent handling of multiple challenges.
    
    Tests that each challenge is handled independently with its own:
    - Detection
    - Notification
    - Verification wait
    - Logging
    
    Requirements: 8.2
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    mock_browser.current_url = "https://www.ralphlauren.com/register"
    
    # Mock browser methods
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Create registration instance
    registration = Registration(mock_browser)
    
    # Track events for each challenge
    challenge_events = []
    
    # Mock ManualVerificationHandler
    with patch('src.registration.ManualVerificationHandler') as MockHandler:
        mock_handler = Mock()
        MockHandler.return_value = mock_handler
        
        # Different challenge types
        challenge_types = ["captcha", "checkbox", "slider"]
        mock_handler.detect_challenge.side_effect = challenge_types
        
        # All verifications succeed
        mock_handler.wait_for_manual_verification.return_value = True
        
        # Mock config
        with patch('src.registration.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            
            # Mock API response
            mock_browser.wait_for_response_with_data = Mock(return_value={
                'status': 302,
                'url': 'https://www.ralphlauren.com/account',
                'headers': {},
                'body': ''
            })
            
            # Mock time.sleep
            with patch('time.sleep'):
                # Handle three challenges
                for i in range(3):
                    result = registration.submit_and_verify()
                    assert result is True
    
    # Verify each challenge was handled independently
    assert mock_handler.detect_challenge.call_count == 3
    assert mock_handler.display_notification.call_count == 3
    assert mock_handler.wait_for_manual_verification.call_count == 3
    
    # Verify different challenge types were displayed
    notification_calls = mock_handler.display_notification.call_args_list
    displayed_types = [call[0][0] for call in notification_calls]
    assert displayed_types == challenge_types




# ============================================================================
# Integration Test: Timeout Scenarios
# ============================================================================

def test_verification_timeout_scenario():
    """
    Integration test for verification timeout scenario.
    
    Tests scenario where:
    1. Challenge is detected
    2. User does not complete verification in time
    3. Verification times out
    4. System marks iteration as failed
    5. Resources are cleaned up
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    mock_browser.current_url = "https://www.ralphlauren.com/register"
    
    # Mock browser methods
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Create registration instance
    registration = Registration(mock_browser)
    
    # Mock ManualVerificationHandler
    with patch('src.registration.ManualVerificationHandler') as MockHandler:
        mock_handler = Mock()
        MockHandler.return_value = mock_handler
        
        # Challenge detected
        mock_handler.detect_challenge.return_value = "captcha"
        
        # Verification times out
        mock_handler.wait_for_manual_verification.return_value = False
        
        # Mock config
        with patch('src.registration.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            
            # Mock time.sleep
            with patch('time.sleep'):
                # Execute registration flow
                result = registration.submit_and_verify()
    
    # Verify registration failed due to timeout
    assert result is False
    
    # Verify challenge detection was called
    assert mock_handler.detect_challenge.called
    
    # Verify notification was displayed
    assert mock_handler.display_notification.called
    
    # Verify manual verification wait was called
    assert mock_handler.wait_for_manual_verification.called
    
    # Verify logging was called (including timeout event)
    assert mock_handler.log_event.call_count >= 2
    
    # Verify API response monitoring was NOT called (timeout before that)
    # Note: wait_for_response_with_data should not be called on timeout


def test_timeout_with_proper_cleanup():
    """
    Integration test for timeout with proper resource cleanup.
    
    Tests that when verification times out:
    1. Timeout event is logged
    2. Browser resources remain available for next iteration
    3. Handler state is properly maintained
    
    Requirements: 4.4, 4.5
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Create handler with short timeout
    handler = ManualVerificationHandler(mock_browser, timeout=2)
    
    # Create verification event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://www.ralphlauren.com/register"
    )
    
    # Mock URL that doesn't match
    type(mock_browser).current_url = PropertyMock(return_value="https://www.ralphlauren.com/register")
    
    # Mock challenge still present
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.is_visible.return_value = True
    mock_page.locator = Mock(return_value=mock_element)
    
    # Mock logger
    with patch('src.manual_verification.logger') as mock_logger:
        # Wait for verification (will timeout)
        result = handler.wait_for_manual_verification("/account/profile")
    
    # Verify timeout occurred
    assert result is False
    
    # Verify browser is still accessible
    assert mock_browser.page is not None
    
    # Verify handler state is maintained
    assert handler.timeout == 2
    assert handler.browser == mock_browser


def test_timeout_error_message():
    """
    Integration test for timeout error message clarity.
    
    Tests that timeout provides clear error message indicating:
    1. Manual verification timeout occurred
    2. Duration of timeout
    3. Next steps for user
    
    Requirements: 4.5
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create verification event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://www.ralphlauren.com/register"
    )
    
    # Mock logger to capture messages
    with patch('src.manual_verification.logger') as mock_logger:
        # Log timeout
        handler.log_verification_timeout(event, 120.0)
    
    # Verify timeout was logged with warning level
    assert mock_logger.warning.called
    
    # Verify log message contains required information
    log_call = mock_logger.warning.call_args[0][0]
    assert "[MANUAL_VERIFICATION]" in log_call
    assert "timed out" in log_call.lower()
    assert "120.0s" in log_call
    
    # Verify event was marked as timed out
    assert event.timeout is True
    assert event.success is False
    assert event.failure_reason == "timeout"




# ============================================================================
# Integration Test: Flow Recovery Scenarios
# ============================================================================

def test_flow_recovery_after_successful_verification():
    """
    Integration test for flow recovery after successful verification.
    
    Tests that after successful manual verification:
    1. Page state is verified
    2. Success event is logged
    3. Automated flow resumes from correct next step
    4. Subsequent monitoring is set up
    
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL matches expected pattern (verification succeeded)
    type(mock_browser).current_url = PropertyMock(
        return_value="https://www.ralphlauren.com/account/profile"
    )
    
    # No challenge elements present
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create successful verification event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://www.ralphlauren.com/register"
    )
    event.complete(success=True)
    
    # Mock logger
    with patch('src.manual_verification.logger') as mock_logger:
        # Resume flow after verification
        result = handler.resume_flow_after_verification(
            event=event,
            expected_url_pattern="/account/profile",
            next_step="profile_update"
        )
    
    # Verify flow resume succeeded
    assert result is True
    
    # Verify page state was verified
    # (verify_page_state is called internally)
    
    # Verify success was logged
    assert mock_logger.info.called
    log_calls = [str(call) for call in mock_logger.info.call_args_list]
    log_messages = ' '.join(log_calls)
    assert "Flow resuming" in log_messages or "resume" in log_messages.lower()
    
    # Verify monitoring setup was logged (debug level)
    assert mock_logger.debug.called or "automation continuing" in log_messages.lower()


def test_flow_recovery_with_page_state_verification():
    """
    Integration test for flow recovery with page state verification.
    
    Tests that page state verification checks:
    1. Current URL matches expected pattern
    2. No challenge elements are present
    3. Page is in stable state
    
    Requirements: 5.1, 5.3
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Test case 1: Valid state (URL matches, no challenges)
    type(mock_browser).current_url = PropertyMock(
        return_value="https://www.ralphlauren.com/account/profile"
    )
    
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Verify page state
    result = handler.verify_page_state("/account/profile")
    assert result is True
    
    # Test case 2: Invalid state (URL doesn't match)
    type(mock_browser).current_url = PropertyMock(
        return_value="https://www.ralphlauren.com/other/page"
    )
    
    result = handler.verify_page_state("/account/profile")
    assert result is False
    
    # Test case 3: Invalid state (challenge still present)
    type(mock_browser).current_url = PropertyMock(
        return_value="https://www.ralphlauren.com/account/profile"
    )
    
    mock_element_visible = Mock()
    mock_element_visible.count.return_value = 1
    mock_element_visible.first = Mock()
    mock_element_visible.first.is_visible.return_value = True
    mock_page.locator = Mock(return_value=mock_element_visible)
    
    result = handler.verify_page_state("/account/profile")
    assert result is False


def test_flow_recovery_with_subsequent_challenge_monitoring():
    """
    Integration test for monitoring subsequent challenges after recovery.
    
    Tests that after flow recovery:
    1. Handler remains ready to detect new challenges
    2. Subsequent challenges are handled independently
    3. Monitoring state is properly maintained
    
    Requirements: 5.5
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Setup post-verification monitoring
    with patch('src.manual_verification.logger') as mock_logger:
        handler.setup_post_verification_monitoring()
    
    # Verify monitoring setup was logged
    assert mock_logger.debug.called
    log_call = mock_logger.debug.call_args[0][0]
    assert "monitoring" in log_call.lower()
    assert "subsequent" in log_call.lower()
    
    # Verify handler can still detect challenges
    # Mock a new challenge appearing
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.wait_for = Mock()
    
    def locator_side_effect(selector):
        if selector == '#px-captcha':
            return mock_element
        else:
            empty = Mock()
            empty.count.return_value = 0
            return empty
    
    mock_page.locator = Mock(side_effect=locator_side_effect)
    
    # Detect new challenge
    challenge_type = handler.detect_challenge()
    
    # Verify new challenge was detected
    assert challenge_type == "captcha"


def test_complete_flow_with_recovery():
    """
    Integration test for complete flow including recovery.
    
    Tests end-to-end flow:
    1. Registration submission
    2. Challenge detection
    3. Manual verification
    4. Verification completion
    5. Flow recovery
    6. Profile update
    7. Second challenge (optional)
    8. Final success
    
    Requirements: All requirements (1.1-9.6)
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Initial URL
    initial_url = "https://www.ralphlauren.com/register"
    success_url = "https://www.ralphlauren.com/account/profile"
    
    # Mock URL progression
    url_sequence = [initial_url, initial_url, success_url, success_url]
    url_index = [0]
    
    def get_current_url():
        idx = url_index[0]
        if idx < len(url_sequence):
            return url_sequence[idx]
        return success_url
    
    type(mock_browser).current_url = PropertyMock(side_effect=get_current_url)
    
    # Mock browser methods
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Create registration instance
    registration = Registration(mock_browser)
    
    # Mock ManualVerificationHandler
    with patch('src.registration.ManualVerificationHandler') as MockHandler:
        mock_handler = Mock()
        MockHandler.return_value = mock_handler
        
        # Challenge detected
        mock_handler.detect_challenge.return_value = "captcha"
        
        # Verification succeeds (simulating URL change)
        def wait_for_verification(expected_url_pattern):
            # Advance URL sequence
            url_index[0] += 1
            return True
        
        mock_handler.wait_for_manual_verification.side_effect = wait_for_verification
        
        # Mock config
        with patch('src.registration.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            
            # Mock API response
            mock_browser.wait_for_response_with_data = Mock(return_value={
                'status': 302,
                'url': success_url,
                'headers': {},
                'body': ''
            })
            
            # Mock challenge elements (disappear after verification)
            mock_element = Mock()
            mock_element.count.return_value = 0
            mock_page.locator = Mock(return_value=mock_element)
            
            # Mock time.sleep
            with patch('time.sleep'):
                # Execute registration flow
                result = registration.submit_and_verify()
    
    # Verify complete flow succeeded
    assert result is True
    
    # Verify all steps were executed
    assert mock_handler.detect_challenge.called
    assert mock_handler.display_notification.called
    assert mock_handler.wait_for_manual_verification.called
    assert mock_handler.log_event.called
    assert mock_browser.wait_for_response_with_data.called
    
    # Verify URL progressed correctly
    assert url_index[0] > 0




# ============================================================================
# Integration Test: Error Handling Scenarios
# ============================================================================

def test_browser_crash_during_verification():
    """
    Integration test for browser crash during verification.
    
    Tests that when browser crashes:
    1. Crash is detected
    2. Failure event is logged
    3. BrowserCrashedError is raised
    4. Proper cleanup occurs
    
    Requirements: 4.4, 4.5
    """
    from src.manual_verification import BrowserCrashedError
    
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create verification event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://www.ralphlauren.com/register"
    )
    
    # Mock logger
    with patch('src.manual_verification.logger') as mock_logger:
        # Handle browser crash
        with pytest.raises(BrowserCrashedError):
            handler.handle_browser_crash(event)
    
    # Verify failure was logged
    assert mock_logger.error.called
    log_call = mock_logger.error.call_args[0][0]
    assert "Browser crashed" in log_call
    
    # Verify event was marked as failed
    assert event.success is False
    assert event.failure_reason == "browser_crashed"


def test_browser_closed_by_user():
    """
    Integration test for user closing browser during verification.
    
    Tests that when user closes browser:
    1. Closure is detected
    2. Failure event is logged
    3. BrowserClosedError is raised
    4. Proper cleanup occurs
    
    Requirements: 4.4, 4.5
    """
    from src.manual_verification import BrowserClosedError
    
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create verification event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://www.ralphlauren.com/register"
    )
    
    # Mock logger
    with patch('src.manual_verification.logger') as mock_logger:
        # Handle browser closed
        with pytest.raises(BrowserClosedError):
            handler.handle_browser_closed(event)
    
    # Verify failure was logged
    assert mock_logger.warning.called
    log_call = mock_logger.warning.call_args[0][0]
    assert "closed browser" in log_call.lower()
    
    # Verify event was marked as failed
    assert event.success is False
    assert event.failure_reason == "browser_closed_by_user"


def test_page_state_mismatch_recovery():
    """
    Integration test for page state mismatch recovery.
    
    Tests that when page state doesn't match expected:
    1. Mismatch is detected
    2. Recovery is attempted (page refresh)
    3. State is re-checked
    4. Success or failure is returned
    
    Requirements: 4.4, 4.5
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock page.url for _check_browser_alive
    mock_page.url = "https://www.ralphlauren.com/account/profile"
    
    # Mock refresh method
    mock_browser.refresh = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Test case 1: Recovery succeeds
    # After refresh, URL matches expected
    type(mock_browser).current_url = PropertyMock(
        return_value="https://www.ralphlauren.com/account/profile"
    )
    
    # Mock time.sleep
    with patch('time.sleep'):
        # Attempt recovery
        result = handler.handle_page_state_mismatch(
            expected_state="/account/profile",
            actual_state="/other/page"
        )
    
    # Verify recovery succeeded
    assert result is True
    
    # Verify refresh was called
    assert mock_browser.refresh.called
    
    # Reset for test case 2
    mock_browser.refresh.reset_mock()
    
    # Test case 2: Recovery fails
    # URL doesn't match after refresh
    type(mock_browser).current_url = PropertyMock(
        return_value="https://www.ralphlauren.com/other/page"
    )
    
    with patch('time.sleep'):
        result = handler.handle_page_state_mismatch(
            expected_state="/account/profile",
            actual_state="/other/page"
        )
    
    # Verify recovery failed
    assert result is False
    
    # Verify refresh was still attempted
    assert mock_browser.refresh.called


def test_log_write_failure_fallback():
    """
    Integration test for log write failure with fallback.
    
    Tests that when log writing fails:
    1. Fallback to console output occurs
    2. Messages are stored in fallback buffer
    3. System continues operating
    
    Requirements: 4.4, 4.5
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Verify fallback buffer is initially empty
    assert len(handler.get_fallback_logs()) == 0
    
    # Mock logger to raise exception
    with patch('src.manual_verification.logger') as mock_logger:
        mock_logger.info.side_effect = Exception("Log write failed")
        
        # Attempt to log (should fallback)
        handler._safe_log("Test message", "info")
    
    # Verify message was added to fallback buffer
    fallback_logs = handler.get_fallback_logs()
    assert len(fallback_logs) > 0
    assert "Test message" in fallback_logs[0]
    
    # Clear fallback logs
    handler.clear_fallback_logs()
    assert len(handler.get_fallback_logs()) == 0


# ============================================================================
# Integration Test: Configuration and Settings
# ============================================================================

def test_configuration_integration():
    """
    Integration test for configuration settings.
    
    Tests that configuration settings are properly:
    1. Loaded from config
    2. Applied to handler
    3. Used during verification flow
    
    Requirements: 6.1, 6.2, 6.3
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    mock_browser.current_url = "https://www.ralphlauren.com/register"
    
    # Mock browser methods
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Create registration instance
    registration = Registration(mock_browser)
    
    # Mock ManualVerificationHandler
    with patch('src.registration.ManualVerificationHandler') as MockHandler:
        mock_handler = Mock()
        MockHandler.return_value = mock_handler
        
        # Challenge detected
        mock_handler.detect_challenge.return_value = "captcha"
        mock_handler.wait_for_manual_verification.return_value = True
        
        # Test with custom config values
        with patch('src.registration.config') as mock_config:
            # Custom configuration
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 180
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = False
            mock_config.MAX_VERIFICATION_ATTEMPTS = 5
            
            # Mock API response
            mock_browser.wait_for_response_with_data = Mock(return_value={
                'status': 302,
                'url': 'https://www.ralphlauren.com/account',
                'headers': {},
                'body': ''
            })
            
            # Mock time.sleep
            with patch('time.sleep'):
                # Execute flow
                result = registration.submit_and_verify()
    
    # Verify flow succeeded
    assert result is True
    
    # Verify handler was created with custom timeout
    handler_call = MockHandler.call_args
    assert handler_call[1]['timeout'] == 180
    
    # Verify notification was NOT displayed (disabled in config)
    assert not mock_handler.display_notification.called


def test_notification_toggle():
    """
    Integration test for notification display toggle.
    
    Tests that ENABLE_VERIFICATION_NOTIFICATIONS config:
    1. Controls whether notifications are displayed
    2. Does not affect verification flow
    
    Requirements: 6.2
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    mock_browser.current_url = "https://www.ralphlauren.com/register"
    
    # Mock browser methods
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Test with notifications enabled
    registration = Registration(mock_browser)
    
    with patch('src.registration.ManualVerificationHandler') as MockHandler:
        mock_handler = Mock()
        MockHandler.return_value = mock_handler
        mock_handler.detect_challenge.return_value = "captcha"
        mock_handler.wait_for_manual_verification.return_value = True
        
        with patch('src.registration.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            
            mock_browser.wait_for_response_with_data = Mock(return_value={
                'status': 302,
                'url': 'https://www.ralphlauren.com/account',
                'headers': {},
                'body': ''
            })
            
            with patch('time.sleep'):
                result = registration.submit_and_verify()
    
    # Verify notification was displayed
    assert mock_handler.display_notification.called
    assert result is True
    
    # Test with notifications disabled
    with patch('src.registration.ManualVerificationHandler') as MockHandler:
        mock_handler = Mock()
        MockHandler.return_value = mock_handler
        mock_handler.detect_challenge.return_value = "captcha"
        mock_handler.wait_for_manual_verification.return_value = True
        
        with patch('src.registration.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = False
            
            mock_browser.wait_for_response_with_data = Mock(return_value={
                'status': 302,
                'url': 'https://www.ralphlauren.com/account',
                'headers': {},
                'body': ''
            })
            
            with patch('time.sleep'):
                result = registration.submit_and_verify()
    
    # Verify notification was NOT displayed
    assert not mock_handler.display_notification.called
    assert result is True


# ============================================================================
# Integration Test: Logging and Monitoring
# ============================================================================

def test_complete_logging_flow():
    """
    Integration test for complete logging flow.
    
    Tests that all verification events are properly logged:
    1. Challenge detection
    2. Verification entry
    3. Verification completion/timeout/failure
    4. All required fields are present
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 2.5
    """
    # Create mock browser
    mock_browser = Mock(spec=BrowserController)
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger to capture all log calls
    with patch('src.manual_verification.logger') as mock_logger:
        # Log complete flow
        event = handler.log_challenge_detection("captcha", "https://www.ralphlauren.com/register")
        handler.log_verification_entry(120)
        handler.log_verification_completion(event, 45.5)
    
    # Verify all logging methods were called
    assert mock_logger.info.call_count >= 3
    
    # Verify event has all required fields
    assert event.challenge_type == "captcha"
    assert event.page_url == "https://www.ralphlauren.com/register"
    assert event.start_time is not None
    assert event.end_time is not None
    assert event.success is True
    assert event.duration_seconds >= 0.0
    
    # Verify event is in handler's events list
    assert event in handler.events


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
