"""
Unit tests for MainRunner timeout handling.

Tests the MainRunner's ability to handle manual verification timeouts,
including logging timeout events and continuing to next iteration.

Requirements: 4.3, 4.4, 4.5
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from main import MainRunner
from src.config import Config
from src.models import UserData


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=Config)
    config.API_URL = "http://test-api.com"
    config.OUTPUT_FILE = "test_output.json"
    config.ITERATION_COUNT = 3
    config.ITERATION_INTERVAL = 1
    config.MONTH = "January"
    config.MANUAL_VERIFICATION_TIMEOUT = 120
    config.ENABLE_VERIFICATION_NOTIFICATIONS = True
    config.MAX_VERIFICATION_ATTEMPTS = 3
    return config


@pytest.fixture
def mock_user_data():
    """Create mock user data for testing."""
    return UserData(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password="TestPass123!",
        phone_number="1234567890"
    )


def test_run_single_iteration_handles_registration_timeout(mock_config, mock_user_data):
    """
    Test that run_single_iteration handles registration timeout correctly.
    
    Verifies that when registration fails (possibly due to verification timeout):
    - The failure is logged with appropriate message
    - Browser resources are cleaned up
    - Iteration is marked as failed
    - Method returns False
    
    Requirements: 4.3, 4.4, 4.5
    """
    runner = MainRunner(mock_config)
    
    # Mock dependencies
    with patch.object(runner.api_client, 'fetch_user_data', return_value=mock_user_data), \
         patch.object(runner.proxy_manager, 'get_valid_us_proxy', return_value='http://proxy:8080'), \
         patch('main.BrowserController') as MockBrowser, \
         patch('main.Registration') as MockRegistration, \
         patch('main.generate_random_day', return_value='15'):
        
        # Setup mock browser
        mock_browser_instance = Mock()
        MockBrowser.return_value = mock_browser_instance
        
        # Setup mock registration to fail (simulating timeout)
        mock_registration_instance = Mock()
        mock_registration_instance.register.return_value = False
        MockRegistration.return_value = mock_registration_instance
        
        # Run iteration
        result = runner.run_single_iteration(1)
        
        # Verify result is False
        assert result is False
        
        # Verify registration was attempted
        assert mock_registration_instance.register.called
        
        # Verify browser was cleaned up (Requirements 4.4, 4.5)
        assert mock_browser_instance.stop.called


def test_run_single_iteration_handles_profile_update_timeout(mock_config, mock_user_data):
    """
    Test that run_single_iteration handles profile update timeout correctly.
    
    Verifies that when profile update fails (possibly due to verification timeout):
    - The failure is logged with appropriate message
    - Account is still saved (registration was successful)
    - Browser resources are cleaned up
    - Method returns True (registration succeeded)
    
    Requirements: 4.3, 4.4, 4.5
    """
    runner = MainRunner(mock_config)
    
    # Mock dependencies
    with patch.object(runner.api_client, 'fetch_user_data', return_value=mock_user_data), \
         patch.object(runner.proxy_manager, 'get_valid_us_proxy', return_value='http://proxy:8080'), \
         patch.object(runner.storage, 'save_success') as mock_save, \
         patch('main.BrowserController') as MockBrowser, \
         patch('main.Registration') as MockRegistration, \
         patch('main.ProfileUpdate') as MockProfileUpdate, \
         patch('main.generate_random_day', return_value='15'):
        
        # Setup mock browser
        mock_browser_instance = Mock()
        MockBrowser.return_value = mock_browser_instance
        
        # Setup mock registration to succeed
        mock_registration_instance = Mock()
        mock_registration_instance.register.return_value = True
        MockRegistration.return_value = mock_registration_instance
        
        # Setup mock profile update to fail (simulating timeout)
        mock_profile_instance = Mock()
        mock_profile_instance.update_profile.return_value = False
        MockProfileUpdate.return_value = mock_profile_instance
        
        # Run iteration
        result = runner.run_single_iteration(1)
        
        # Verify result is True (registration succeeded even though profile update failed)
        assert result is True
        
        # Verify account was saved despite profile update failure
        assert mock_save.called
        
        # Verify browser was cleaned up (Requirements 4.4, 4.5)
        assert mock_browser_instance.stop.called


def test_run_continues_after_timeout(mock_config, mock_user_data):
    """
    Test that run() continues to next iteration after timeout.
    
    Verifies that when an iteration fails (possibly due to verification timeout):
    - The failure is counted
    - The next iteration is attempted
    - All iterations complete
    
    Requirements: 4.4
    """
    runner = MainRunner(mock_config)
    
    # Mock run_single_iteration to fail first, then succeed
    with patch.object(runner, 'run_single_iteration', side_effect=[False, True, True]):
        results = runner.run()
    
    # Verify all iterations were attempted
    assert results['total'] == 3
    assert results['successful'] == 2
    assert results['failed'] == 1


def test_run_logs_timeout_events(mock_config, mock_user_data, caplog):
    """
    Test that run() logs timeout events appropriately.
    
    Verifies that when iterations fail:
    - Failure is logged with appropriate message mentioning possible timeout
    - Message indicates proceeding to next iteration
    
    Requirements: 4.3, 4.5
    """
    import logging
    caplog.set_level(logging.INFO)
    
    runner = MainRunner(mock_config)
    
    # Mock run_single_iteration to fail
    with patch.object(runner, 'run_single_iteration', return_value=False):
        runner.run()
    
    # Check that timeout-related messages were logged
    log_messages = [record.message for record in caplog.records]
    
    # Verify failure logging mentions possible timeout
    assert any('verification timeout' in msg.lower() for msg in log_messages)
    
    # Verify proceeding to next iteration is logged
    assert any('proceeding to next iteration' in msg.lower() for msg in log_messages)


def test_run_single_iteration_cleans_up_browser_on_exception(mock_config, mock_user_data):
    """
    Test that browser resources are cleaned up even when exception occurs.
    
    Verifies that:
    - Browser.stop() is called in finally block
    - Resources are cleaned up regardless of exception
    
    Requirements: 4.4, 4.5
    """
    runner = MainRunner(mock_config)
    
    # Mock dependencies
    with patch.object(runner.api_client, 'fetch_user_data', return_value=mock_user_data), \
         patch.object(runner.proxy_manager, 'get_valid_us_proxy', return_value='http://proxy:8080'), \
         patch('main.BrowserController') as MockBrowser, \
         patch('main.Registration') as MockRegistration, \
         patch('main.generate_random_day', return_value='15'):
        
        # Setup mock browser
        mock_browser_instance = Mock()
        MockBrowser.return_value = mock_browser_instance
        
        # Setup mock registration to raise exception
        mock_registration_instance = Mock()
        mock_registration_instance.register.side_effect = Exception("Test exception")
        MockRegistration.return_value = mock_registration_instance
        
        # Run iteration (should not raise exception)
        result = runner.run_single_iteration(1)
        
        # Verify result is False
        assert result is False
        
        # Verify browser was cleaned up despite exception (Requirements 4.4, 4.5)
        assert mock_browser_instance.stop.called


def test_run_handles_multiple_timeout_iterations(mock_config):
    """
    Test that run() handles multiple consecutive timeout iterations.
    
    Verifies that:
    - Multiple timeouts are handled gracefully
    - Each timeout is logged
    - System continues through all iterations
    
    Requirements: 4.3, 4.4, 4.5
    """
    runner = MainRunner(mock_config)
    
    # Mock all iterations to fail (simulating timeouts)
    with patch.object(runner, 'run_single_iteration', return_value=False):
        results = runner.run()
    
    # Verify all iterations were attempted
    assert results['total'] == 3
    assert results['successful'] == 0
    assert results['failed'] == 3


def test_run_single_iteration_logs_timeout_in_registration(mock_config, mock_user_data, caplog):
    """
    Test that registration timeout is logged with clear message.
    
    Verifies that:
    - Registration failure logs mention possible verification timeout
    - Message indicates iteration will be marked as failed
    
    Requirements: 4.3, 4.5
    """
    import logging
    caplog.set_level(logging.INFO)
    
    runner = MainRunner(mock_config)
    
    # Mock dependencies
    with patch.object(runner.api_client, 'fetch_user_data', return_value=mock_user_data), \
         patch.object(runner.proxy_manager, 'get_valid_us_proxy', return_value='http://proxy:8080'), \
         patch('main.BrowserController') as MockBrowser, \
         patch('main.Registration') as MockRegistration, \
         patch('main.generate_random_day', return_value='15'):
        
        # Setup mocks
        mock_browser_instance = Mock()
        MockBrowser.return_value = mock_browser_instance
        
        mock_registration_instance = Mock()
        mock_registration_instance.register.return_value = False
        MockRegistration.return_value = mock_registration_instance
        
        # Run iteration
        runner.run_single_iteration(1)
    
    # Check log messages
    log_messages = [record.message for record in caplog.records]
    
    # Verify timeout-related logging
    assert any('manual verification timeout' in msg.lower() for msg in log_messages)
    assert any('marking iteration as failed' in msg.lower() for msg in log_messages)


def test_run_single_iteration_logs_timeout_in_profile_update(mock_config, mock_user_data, caplog):
    """
    Test that profile update timeout is logged with clear message.
    
    Verifies that:
    - Profile update failure logs mention possible verification timeout
    - Message indicates registration was successful
    
    Requirements: 4.3, 4.5
    """
    import logging
    caplog.set_level(logging.INFO)
    
    runner = MainRunner(mock_config)
    
    # Mock dependencies
    with patch.object(runner.api_client, 'fetch_user_data', return_value=mock_user_data), \
         patch.object(runner.proxy_manager, 'get_valid_us_proxy', return_value='http://proxy:8080'), \
         patch.object(runner.storage, 'save_success'), \
         patch('main.BrowserController') as MockBrowser, \
         patch('main.Registration') as MockRegistration, \
         patch('main.ProfileUpdate') as MockProfileUpdate, \
         patch('main.generate_random_day', return_value='15'):
        
        # Setup mocks
        mock_browser_instance = Mock()
        MockBrowser.return_value = mock_browser_instance
        
        mock_registration_instance = Mock()
        mock_registration_instance.register.return_value = True
        MockRegistration.return_value = mock_registration_instance
        
        mock_profile_instance = Mock()
        mock_profile_instance.update_profile.return_value = False
        MockProfileUpdate.return_value = mock_profile_instance
        
        # Run iteration
        runner.run_single_iteration(1)
    
    # Check log messages
    log_messages = [record.message for record in caplog.records]
    
    # Verify timeout-related logging
    assert any('manual verification timeout' in msg.lower() for msg in log_messages)
    assert any('registration was successful' in msg.lower() for msg in log_messages)


def test_browser_cleanup_logs_success(mock_config, mock_user_data, caplog):
    """
    Test that successful browser cleanup is logged.
    
    Verifies that:
    - Browser cleanup success is logged
    - Message mentions resources cleaned up
    
    Requirements: 4.5
    """
    import logging
    caplog.set_level(logging.INFO)
    
    runner = MainRunner(mock_config)
    
    # Mock dependencies
    with patch.object(runner.api_client, 'fetch_user_data', return_value=mock_user_data), \
         patch.object(runner.proxy_manager, 'get_valid_us_proxy', return_value='http://proxy:8080'), \
         patch('main.BrowserController') as MockBrowser, \
         patch('main.Registration') as MockRegistration, \
         patch('main.generate_random_day', return_value='15'):
        
        # Setup mocks
        mock_browser_instance = Mock()
        MockBrowser.return_value = mock_browser_instance
        
        mock_registration_instance = Mock()
        mock_registration_instance.register.return_value = False
        MockRegistration.return_value = mock_registration_instance
        
        # Run iteration
        runner.run_single_iteration(1)
    
    # Check log messages
    log_messages = [record.message for record in caplog.records]
    
    # Verify cleanup logging
    assert any('browser stopped' in msg.lower() and 'resources cleaned up' in msg.lower() for msg in log_messages)
