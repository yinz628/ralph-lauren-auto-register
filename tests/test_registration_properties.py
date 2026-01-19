"""
Property-based tests for Registration module.

Uses hypothesis library for property-based testing of registration flow
with manual verification integration.
"""

import pytest
from datetime import datetime
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, PropertyMock, patch, MagicMock

from src.registration import Registration
from src.models import UserData


# Strategy for generating challenge types
challenge_type_strategy = st.sampled_from([
    "captcha",
    "press-and-hold",
    "checkbox",
    "slider",
    "challenge",
    "unknown"
])

# Strategy for generating user data
def user_data_strategy():
    """Generate random UserData for testing."""
    return st.builds(
        UserData,
        email=st.emails(),
        password=st.text(min_size=8, max_size=20),
        first_name=st.text(min_size=2, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        last_name=st.text(min_size=2, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        month=st.sampled_from(["January", "February", "March", "April", "May", "June", 
                               "July", "August", "September", "October", "November", "December"]),
        day=st.integers(min_value=1, max_value=28)
    )


@given(
    challenge_detected=st.booleans(),
    challenge_type=challenge_type_strategy
)
@settings(max_examples=100, deadline=None)
def test_automation_pause_guarantee(challenge_detected, challenge_type):
    """
    **Feature: manual-verification, Property 2: 自动化暂停保证**
    
    *For any* detected PerimeterX challenge, the system SHALL immediately enter
    manual verification mode without attempting any automatic solving methods,
    and all automated interactions SHALL be paused.
    
    **Validates: Requirements 2.1, 9.1, 9.6**
    """
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    mock_browser.current_url = "https://www.ralphlauren.com/register"
    
    # Mock wait_for_element to return True for submit button
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Mock wait_for_response_with_data to return success
    mock_browser.wait_for_response_with_data = Mock(return_value={
        'status': 302,
        'url': 'https://www.ralphlauren.com/account',
        'headers': {},
        'body': ''
    })
    
    # Create registration instance
    registration = Registration(mock_browser)
    
    # Mock ManualVerificationHandler
    with patch('src.registration.ManualVerificationHandler') as MockHandler:
        mock_handler_instance = Mock()
        MockHandler.return_value = mock_handler_instance
        
        # Configure challenge detection
        if challenge_detected:
            mock_handler_instance.detect_challenge.return_value = challenge_type
            mock_handler_instance.wait_for_manual_verification.return_value = True
        else:
            mock_handler_instance.detect_challenge.return_value = None
        
        # Mock config
        with patch('src.registration.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            
            # Mock time.sleep to speed up test
            with patch('time.sleep'):
                # Call submit_and_verify
                result = registration.submit_and_verify()
        
        # Verify challenge detection was called
        assert mock_handler_instance.detect_challenge.called
        
        if challenge_detected:
            # When challenge is detected:
            # 1. Manual verification handler should be created
            assert MockHandler.called
            
            # 2. Display notification should be called (if enabled)
            assert mock_handler_instance.display_notification.called
            notification_call = mock_handler_instance.display_notification.call_args
            assert notification_call[0][0] == challenge_type
            
            # 3. Wait for manual verification should be called
            assert mock_handler_instance.wait_for_manual_verification.called
            
            # 4. Log event should be called (at least twice: start and end)
            assert mock_handler_instance.log_event.call_count >= 2
            
            # 5. NO automatic solving methods should be called
            # The old _handle_px_challenge and _solve_px_press_hold methods have been removed
            # We verify this by checking that wait_for_manual_verification was called instead
            
            # 6. Automation should pause (wait_for_manual_verification is the pause)
            # Verify that after challenge detection, we wait for manual completion
            assert mock_handler_instance.wait_for_manual_verification.called
            
            # 7. Result should be True (verification succeeded)
            assert result is True
        else:
            # When no challenge is detected:
            # 1. Manual verification handler should still be created
            assert MockHandler.called
            
            # 2. Display notification should NOT be called
            assert not mock_handler_instance.display_notification.called
            
            # 3. Wait for manual verification should NOT be called
            assert not mock_handler_instance.wait_for_manual_verification.called
            
            # 4. Should proceed directly to monitoring API response
            assert mock_browser.wait_for_response_with_data.called
            
            # 5. Result should be True (registration succeeded)
            assert result is True


@given(
    challenge_type=challenge_type_strategy,
    verification_timeout=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_automation_pause_with_timeout(challenge_type, verification_timeout):
    """
    **Feature: manual-verification, Property 2: 自动化暂停保证 (Timeout)**
    
    *For any* detected PerimeterX challenge that times out, the system SHALL
    return False and not proceed with automated interactions.
    
    **Validates: Requirements 2.1, 4.2, 9.6**
    """
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    mock_browser.current_url = "https://www.ralphlauren.com/register"
    
    # Mock wait_for_element to return True for submit button
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Mock wait_for_response_with_data to return success (only called if verification succeeds)
    mock_browser.wait_for_response_with_data = Mock(return_value={
        'status': 302,
        'url': 'https://www.ralphlauren.com/account',
        'headers': {},
        'body': ''
    })
    
    # Create registration instance
    registration = Registration(mock_browser)
    
    # Mock ManualVerificationHandler
    with patch('src.registration.ManualVerificationHandler') as MockHandler:
        mock_handler_instance = Mock()
        MockHandler.return_value = mock_handler_instance
        
        # Challenge is always detected
        mock_handler_instance.detect_challenge.return_value = challenge_type
        
        # Configure verification result
        mock_handler_instance.wait_for_manual_verification.return_value = not verification_timeout
        
        # Mock config
        with patch('src.registration.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            
            # Mock time.sleep to speed up test
            with patch('time.sleep'):
                # Call submit_and_verify
                result = registration.submit_and_verify()
        
        # Verify challenge detection was called
        assert mock_handler_instance.detect_challenge.called
        
        # Verify manual verification was attempted
        assert mock_handler_instance.wait_for_manual_verification.called
        
        if verification_timeout:
            # When verification times out:
            # 1. Result should be False
            assert result is False
            
            # 2. Log event should be called with timeout
            assert mock_handler_instance.log_event.call_count >= 2
            
            # 3. API response monitoring should NOT be called
            assert not mock_browser.wait_for_response_with_data.called
        else:
            # When verification succeeds:
            # 1. Result should be True
            assert result is True
            
            # 2. Log event should be called with success
            assert mock_handler_instance.log_event.call_count >= 2
            
            # 3. API response monitoring should be called
            assert mock_browser.wait_for_response_with_data.called


@given(
    challenge_type=challenge_type_strategy,
    notifications_enabled=st.booleans()
)
@settings(max_examples=50, deadline=None)
def test_automation_pause_notification_control(challenge_type, notifications_enabled):
    """
    **Feature: manual-verification, Property 2: 自动化暂停保证 (Notifications)**
    
    *For any* detected PerimeterX challenge, notifications SHALL be displayed
    only when ENABLE_VERIFICATION_NOTIFICATIONS is True.
    
    **Validates: Requirements 2.2, 2.4**
    """
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    mock_browser.current_url = "https://www.ralphlauren.com/register"
    
    # Mock wait_for_element to return True for submit button
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Mock wait_for_response_with_data to return success
    mock_browser.wait_for_response_with_data = Mock(return_value={
        'status': 302,
        'url': 'https://www.ralphlauren.com/account',
        'headers': {},
        'body': ''
    })
    
    # Create registration instance
    registration = Registration(mock_browser)
    
    # Mock ManualVerificationHandler
    with patch('src.registration.ManualVerificationHandler') as MockHandler:
        mock_handler_instance = Mock()
        MockHandler.return_value = mock_handler_instance
        
        # Challenge is always detected
        mock_handler_instance.detect_challenge.return_value = challenge_type
        mock_handler_instance.wait_for_manual_verification.return_value = True
        
        # Mock config with notification setting
        with patch('src.registration.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = notifications_enabled
            
            # Mock time.sleep to speed up test
            with patch('time.sleep'):
                # Call submit_and_verify
                result = registration.submit_and_verify()
        
        # Verify challenge detection was called
        assert mock_handler_instance.detect_challenge.called
        
        if notifications_enabled:
            # Notification should be displayed
            assert mock_handler_instance.display_notification.called
        else:
            # Notification should NOT be displayed
            assert not mock_handler_instance.display_notification.called
        
        # Verification should still proceed regardless of notification setting
        assert mock_handler_instance.wait_for_manual_verification.called
        assert result is True


@given(
    challenge_type=challenge_type_strategy
)
@settings(max_examples=50, deadline=None)
def test_automation_pause_event_logging(challenge_type):
    """
    **Feature: manual-verification, Property 2: 自动化暂停保证 (Logging)**
    
    *For any* detected PerimeterX challenge, verification events SHALL be
    logged with all required information.
    
    **Validates: Requirements 2.5, 7.1, 7.2, 7.3**
    """
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    mock_browser.current_url = "https://www.ralphlauren.com/register"
    
    # Mock wait_for_element to return True for submit button
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Mock wait_for_response_with_data to return success
    mock_browser.wait_for_response_with_data = Mock(return_value={
        'status': 302,
        'url': 'https://www.ralphlauren.com/account',
        'headers': {},
        'body': ''
    })
    
    # Create registration instance
    registration = Registration(mock_browser)
    
    # Mock ManualVerificationHandler
    with patch('src.registration.ManualVerificationHandler') as MockHandler:
        mock_handler_instance = Mock()
        MockHandler.return_value = mock_handler_instance
        
        # Challenge is always detected
        mock_handler_instance.detect_challenge.return_value = challenge_type
        mock_handler_instance.wait_for_manual_verification.return_value = True
        
        # Mock config
        with patch('src.registration.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            
            # Mock VerificationEvent
            with patch('src.registration.VerificationEvent') as MockEvent:
                mock_event = Mock()
                MockEvent.return_value = mock_event
                
                # Mock datetime
                with patch('src.registration.datetime') as mock_datetime:
                    mock_now = Mock()
                    mock_datetime.now.return_value = mock_now
                    
                    # Mock time.sleep to speed up test
                    with patch('time.sleep'):
                        # Call submit_and_verify
                        result = registration.submit_and_verify()
                
                # Verify VerificationEvent was created with correct parameters
                assert MockEvent.called
                event_call = MockEvent.call_args
                assert event_call[1]['challenge_type'] == challenge_type
                assert event_call[1]['start_time'] == mock_now
                assert event_call[1]['page_url'] == mock_browser.current_url
                
                # Verify event.complete was called
                assert mock_event.complete.called
                complete_call = mock_event.complete.call_args
                assert complete_call[1]['success'] is True
                
                # Verify log_event was called at least twice (start and end)
                assert mock_handler_instance.log_event.call_count >= 2
                
                # Verify first log_event call was with the event
                first_log_call = mock_handler_instance.log_event.call_args_list[0]
                assert first_log_call[0][0] == mock_event
        
        assert result is True
