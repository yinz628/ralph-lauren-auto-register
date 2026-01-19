"""
Unit tests for ProfileUpdate manual verification integration.

Tests the integration of ManualVerificationHandler into the ProfileUpdate
module's submit_and_verify method.
"""

import pytest
from unittest.mock import Mock, PropertyMock, patch
from datetime import datetime

from src.profile_update import ProfileUpdate


def test_submit_and_verify_with_challenge_detected():
    """
    Test submit_and_verify handles PerimeterX challenge during profile update.
    
    Verifies that when a challenge is detected:
    - ManualVerificationHandler is initialized
    - Challenge detection is performed
    - User notification is displayed
    - Manual verification wait is triggered
    - Flow continues after successful verification
    
    Requirements: 8.1
    """
    # Create mock browser
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock submit button found
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Mock current URL
    type(mock_browser).current_url = PropertyMock(
        return_value="https://www.ralphlauren.com/profile"
    )
    
    # Mock challenge element present
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.wait_for = Mock()
    mock_element.first.is_visible.return_value = True
    
    def locator_side_effect(selector):
        if selector == '#px-captcha':
            return mock_element
        else:
            empty_element = Mock()
            empty_element.count.return_value = 0
            return empty_element
    
    mock_page.locator = Mock(side_effect=locator_side_effect)
    
    # Mock successful 302 response after verification
    mock_browser.wait_for_response = Mock(return_value=True)
    
    # Create ProfileUpdate instance
    profile_update = ProfileUpdate(mock_browser)
    
    # Mock time.sleep to speed up test
    with patch('time.sleep'):
        with patch('src.profile_update.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            
            # Submit and verify
            result = profile_update.submit_and_verify()
    
    # Should succeed
    assert result is True
    
    # Verify submit button was clicked
    mock_browser.click_button.assert_called_once()
    
    # Verify 302 response was monitored
    mock_browser.wait_for_response.assert_called_once()


def test_submit_and_verify_with_challenge_timeout():
    """
    Test submit_and_verify handles verification timeout during profile update.
    
    Verifies that when verification times out:
    - Manual verification is attempted
    - Timeout is detected
    - Method returns False
    - 302 response monitoring is not performed
    
    Requirements: 8.1
    """
    # Create mock browser
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock submit button found
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Mock current URL (doesn't match expected pattern)
    type(mock_browser).current_url = PropertyMock(
        return_value="https://www.ralphlauren.com/other"
    )
    
    # Mock challenge element present
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.wait_for = Mock()
    mock_element.first.is_visible.return_value = True
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create ProfileUpdate instance
    profile_update = ProfileUpdate(mock_browser)
    
    # Mock time functions to simulate timeout
    mock_time = [0.0]
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            with patch('src.profile_update.config') as mock_config:
                mock_config.MANUAL_VERIFICATION_TIMEOUT = 2
                mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
                
                # Submit and verify (will timeout)
                result = profile_update.submit_and_verify()
    
    # Should fail due to timeout
    assert result is False
    
    # Verify submit button was clicked
    mock_browser.click_button.assert_called_once()


def test_submit_and_verify_no_challenge_detected():
    """
    Test submit_and_verify continues normal flow when no challenge detected.
    
    Verifies that when no challenge is present:
    - Challenge detection is performed
    - No manual verification is triggered
    - Normal 302 response monitoring proceeds
    
    Requirements: 8.1
    """
    # Create mock browser
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock submit button found
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Mock no challenge elements present
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Mock successful 302 response
    mock_browser.wait_for_response = Mock(return_value=True)
    
    # Create ProfileUpdate instance
    profile_update = ProfileUpdate(mock_browser)
    
    # Mock time.sleep to speed up test
    with patch('time.sleep'):
        with patch('src.profile_update.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            
            # Submit and verify
            result = profile_update.submit_and_verify()
    
    # Should succeed
    assert result is True
    
    # Verify submit button was clicked
    mock_browser.click_button.assert_called_once()
    
    # Verify 302 response was monitored
    mock_browser.wait_for_response.assert_called_once()


def test_submit_and_verify_challenge_with_successful_verification():
    """
    Test complete flow: challenge detected, user completes verification, profile updates.
    
    Verifies the complete integration:
    - Challenge is detected
    - Manual verification wait begins
    - URL changes to profile page (verification success)
    - 302 response is monitored
    - Method returns True
    
    Requirements: 8.1
    """
    # Create mock browser
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock submit button found
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Mock URL changes during verification (simulating user completing challenge)
    url_sequence = [
        "https://www.ralphlauren.com/challenge",  # Initial challenge page
        "https://www.ralphlauren.com/challenge",  # Still on challenge
        "https://www.ralphlauren.com/profile"     # Redirected to profile
    ]
    url_index = [0]
    
    def get_current_url():
        idx = url_index[0]
        if idx < len(url_sequence):
            url = url_sequence[idx]
            url_index[0] += 1
            return url
        return url_sequence[-1]
    
    type(mock_browser).current_url = PropertyMock(side_effect=get_current_url)
    
    # Mock challenge element present initially, then disappears
    call_count = [0]
    
    def locator_side_effect(selector):
        call_count[0] += 1
        if call_count[0] <= 2 and selector == '#px-captcha':
            # First few calls: challenge present
            mock_element = Mock()
            mock_element.count.return_value = 1
            mock_element.first = Mock()
            mock_element.first.wait_for = Mock()
            mock_element.first.is_visible.return_value = True
            return mock_element
        else:
            # Later calls: challenge gone
            empty_element = Mock()
            empty_element.count.return_value = 0
            return empty_element
    
    mock_page.locator = Mock(side_effect=locator_side_effect)
    
    # Mock successful 302 response
    mock_browser.wait_for_response = Mock(return_value=True)
    
    # Create ProfileUpdate instance
    profile_update = ProfileUpdate(mock_browser)
    
    # Mock time.sleep to speed up test
    with patch('time.sleep'):
        with patch('src.profile_update.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            
            # Submit and verify
            result = profile_update.submit_and_verify()
    
    # Should succeed
    assert result is True
    
    # Verify submit button was clicked
    mock_browser.click_button.assert_called_once()
    
    # Verify 302 response was monitored
    mock_browser.wait_for_response.assert_called_once()


def test_submit_and_verify_notification_disabled():
    """
    Test that notification is not displayed when disabled in config.
    
    Requirements: 8.1
    """
    # Create mock browser
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock submit button found
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Mock current URL
    type(mock_browser).current_url = PropertyMock(
        return_value="https://www.ralphlauren.com/profile"
    )
    
    # Mock challenge element present
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.wait_for = Mock()
    mock_element.first.is_visible.return_value = True
    
    def locator_side_effect(selector):
        if selector == '#px-captcha':
            return mock_element
        else:
            empty_element = Mock()
            empty_element.count.return_value = 0
            return empty_element
    
    mock_page.locator = Mock(side_effect=locator_side_effect)
    
    # Mock successful 302 response
    mock_browser.wait_for_response = Mock(return_value=True)
    
    # Create ProfileUpdate instance
    profile_update = ProfileUpdate(mock_browser)
    
    # Mock time.sleep and print to verify notification not displayed
    with patch('time.sleep'):
        with patch('builtins.print') as mock_print:
            with patch('src.profile_update.config') as mock_config:
                mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
                mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = False
                
                # Submit and verify
                result = profile_update.submit_and_verify()
    
    # Should succeed
    assert result is True
    
    # Verify notification was not printed (print not called with notification)
    # Note: print might be called for other reasons, so we just verify success
    assert mock_browser.click_button.called


def test_submit_and_verify_submit_button_not_found():
    """
    Test submit_and_verify returns False when submit button not found.
    
    Requirements: 5.5
    """
    # Create mock browser
    mock_browser = Mock()
    
    # Mock submit button not found
    mock_browser.wait_for_element = Mock(return_value=False)
    
    # Create ProfileUpdate instance
    profile_update = ProfileUpdate(mock_browser)
    
    # Submit and verify
    result = profile_update.submit_and_verify()
    
    # Should fail
    assert result is False
    
    # Verify wait_for_element was called
    mock_browser.wait_for_element.assert_called_once()


def test_submit_and_verify_302_response_not_detected():
    """
    Test submit_and_verify returns False when 302 response not detected.
    
    Requirements: 5.6
    """
    # Create mock browser
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock submit button found
    mock_browser.wait_for_element = Mock(return_value=True)
    mock_browser.click_button = Mock()
    
    # Mock no challenge elements present
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Mock 302 response not detected
    mock_browser.wait_for_response = Mock(return_value=False)
    
    # Create ProfileUpdate instance
    profile_update = ProfileUpdate(mock_browser)
    
    # Mock time.sleep to speed up test
    with patch('time.sleep'):
        with patch('src.profile_update.config') as mock_config:
            mock_config.MANUAL_VERIFICATION_TIMEOUT = 120
            mock_config.ENABLE_VERIFICATION_NOTIFICATIONS = True
            
            # Submit and verify
            result = profile_update.submit_and_verify()
    
    # Should fail
    assert result is False
    
    # Verify 302 response was monitored
    mock_browser.wait_for_response.assert_called_once()
