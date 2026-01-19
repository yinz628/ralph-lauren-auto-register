"""
Unit tests for configuration module.

Tests default configuration values and custom configuration loading.
"""

import pytest
from src.config import Config


class TestConfigDefaults:
    """Test default configuration values."""
    
    def test_manual_verification_timeout_default(self):
        """Test MANUAL_VERIFICATION_TIMEOUT has correct default value.
        
        Requirements: 6.1
        """
        config = Config()
        assert config.MANUAL_VERIFICATION_TIMEOUT == 120
        
    def test_enable_verification_notifications_default(self):
        """Test ENABLE_VERIFICATION_NOTIFICATIONS has correct default value.
        
        Requirements: 6.2
        """
        config = Config()
        assert config.ENABLE_VERIFICATION_NOTIFICATIONS is True
        
    def test_max_verification_attempts_default(self):
        """Test MAX_VERIFICATION_ATTEMPTS has correct default value.
        
        Requirements: 6.1
        """
        config = Config()
        assert config.MAX_VERIFICATION_ATTEMPTS == 3


class TestCustomConfiguration:
    """Test custom configuration values."""
    
    def test_custom_manual_verification_timeout(self):
        """Test custom MANUAL_VERIFICATION_TIMEOUT value.
        
        Requirements: 6.1
        """
        config = Config(MANUAL_VERIFICATION_TIMEOUT=180)
        assert config.MANUAL_VERIFICATION_TIMEOUT == 180
        
    def test_custom_enable_verification_notifications(self):
        """Test custom ENABLE_VERIFICATION_NOTIFICATIONS value.
        
        Requirements: 6.2
        """
        config = Config(ENABLE_VERIFICATION_NOTIFICATIONS=False)
        assert config.ENABLE_VERIFICATION_NOTIFICATIONS is False
        
    def test_custom_max_verification_attempts(self):
        """Test custom MAX_VERIFICATION_ATTEMPTS value.
        
        Requirements: 6.1
        """
        config = Config(MAX_VERIFICATION_ATTEMPTS=5)
        assert config.MAX_VERIFICATION_ATTEMPTS == 5
        
    def test_multiple_custom_values(self):
        """Test multiple custom configuration values together.
        
        Requirements: 6.1, 6.2
        """
        config = Config(
            MANUAL_VERIFICATION_TIMEOUT=90,
            ENABLE_VERIFICATION_NOTIFICATIONS=False,
            MAX_VERIFICATION_ATTEMPTS=2
        )
        assert config.MANUAL_VERIFICATION_TIMEOUT == 90
        assert config.ENABLE_VERIFICATION_NOTIFICATIONS is False
        assert config.MAX_VERIFICATION_ATTEMPTS == 2
        
    def test_partial_custom_values(self):
        """Test that unspecified values use defaults when some are customized.
        
        Requirements: 6.1, 6.2
        """
        config = Config(MANUAL_VERIFICATION_TIMEOUT=60)
        assert config.MANUAL_VERIFICATION_TIMEOUT == 60
        assert config.ENABLE_VERIFICATION_NOTIFICATIONS is True  # default
        assert config.MAX_VERIFICATION_ATTEMPTS == 3  # default
