"""
Profile Update module for Ralph Lauren Auto Register System.

Handles the profile update flow including filling birthday and phone
information, submission, and success verification.
"""

from typing import Optional
import logging
import time
from datetime import datetime

from src.browser_controller import BrowserController, is_valid_month
from src.manual_verification import ManualVerificationHandler, VerificationEvent
from src.config import config


# URLs
PROFILE_URL = "https://www.ralphlauren.com/profile"
PROFILE_SUBMIT_URL_PATTERN = "on/demandware.store/Sites-RalphLauren_US-Site/en_US/Account-EditForm"

# Element selectors
MONTH_SELECTOR = "#dwfrm_profile_customer_month"
DAY_SELECTOR = "#dwfrm_profile_customer_day"
PHONE_SELECTOR = "#dwfrm_profile_customer_phone"
PHONE_MOBILE_SELECTOR = "#dwfrm_profile_customer_phoneMobile"
SUBMIT_BUTTON_SELECTOR = '[name="dwfrm_profile_confirm"]'

# Timeouts
NAVIGATION_TIMEOUT = 30000  # 30 seconds

logger = logging.getLogger(__name__)


class ProfileUpdateError(Exception):
    """Exception raised when profile update fails."""
    pass


class ProfileUpdate:
    """Handles Ralph Lauren profile update flow.
    
    Provides methods to fill the profile form with birthday and phone
    information, and submit with verification.
    """
    
    def __init__(self, browser: BrowserController):
        """Initialize ProfileUpdate module.
        
        Args:
            browser: BrowserController instance for browser automation
        """
        self.browser = browser

    def fill_profile_form(self, month: str, day: int, phone_number: str) -> None:
        """Fill the profile form with birthday and phone information.
        
        Args:
            month: English month name (e.g., "January")
            day: Day of the month (1-28)
            phone_number: Phone number to fill in both phone fields
            
        Raises:
            ProfileUpdateError: If required form elements cannot be found
            ValueError: If month is not a valid English month name
            
        Requirements: 5.1, 5.2, 5.3, 5.4
        """
        logger.info(f"Filling profile form: month={month}, day={day}")
        
        # Validate month (Requirements 5.1)
        if not is_valid_month(month):
            raise ValueError(f"Invalid month name: {month}. Must be a valid English month name.")
        
        # Select month dropdown (Requirements 5.1)
        if not self.browser.wait_for_element(MONTH_SELECTOR):
            raise ProfileUpdateError("Month dropdown not found")
        self.browser.select_dropdown(MONTH_SELECTOR, month)
        logger.debug(f"Month selected: {month}")
        
        # Select day dropdown (Requirements 5.2)
        if not self.browser.wait_for_element(DAY_SELECTOR):
            raise ProfileUpdateError("Day dropdown not found")
        self.browser.select_dropdown(DAY_SELECTOR, str(day))
        logger.debug(f"Day selected: {day}")
        
        # Fill phone field (Requirements 5.3)
        if not self.browser.wait_for_element(PHONE_SELECTOR):
            raise ProfileUpdateError("Phone field not found")
        self.browser.fill_input(PHONE_SELECTOR, phone_number)
        logger.debug("Phone field filled")
        
        # Fill mobile phone field (Requirements 5.4)
        if not self.browser.wait_for_element(PHONE_MOBILE_SELECTOR):
            raise ProfileUpdateError("Mobile phone field not found")
        self.browser.fill_input(PHONE_MOBILE_SELECTOR, phone_number)
        logger.debug("Mobile phone field filled")
        
        logger.info("Profile form filled successfully")

    def submit_and_verify(self, timeout: Optional[int] = None) -> bool:
        """Submit the profile form and verify success.
        
        Clicks the submit button, detects PerimeterX challenges, enters manual
        verification mode if needed, and monitors for HTTP 302 response
        from the Account-EditForm URL to determine if update was successful.
        
        Args:
            timeout: Maximum time to wait for success in milliseconds.
                    Defaults to NAVIGATION_TIMEOUT.
                    
        Returns:
            True if profile update was successful, False otherwise
            
        Requirements: 5.5, 5.6, 8.1
        """
        timeout = timeout or NAVIGATION_TIMEOUT
        
        logger.info("Submitting profile form")
        
        # Click submit button (Requirements 5.5)
        if not self.browser.wait_for_element(SUBMIT_BUTTON_SELECTOR):
            logger.error("Submit button not found")
            return False
        
        self.browser.click_button(SUBMIT_BUTTON_SELECTOR)
        logger.debug("Submit button clicked")
        
        # Wait a moment for potential PerimeterX challenge to appear
        time.sleep(2)
        
        # Initialize manual verification handler (Requirements 8.1)
        verification_handler = ManualVerificationHandler(
            self.browser, 
            timeout=config.MANUAL_VERIFICATION_TIMEOUT
        )
        
        # Detect PerimeterX challenge (Requirements 8.1)
        challenge_type = verification_handler.detect_challenge()
        
        if challenge_type:
            # Challenge detected - enter manual verification mode (Requirements 8.1)
            logger.info(f"PerimeterX challenge detected during profile update: {challenge_type}")
            
            # Create verification event
            event = VerificationEvent(
                challenge_type=challenge_type,
                start_time=datetime.now(),
                page_url=self.browser.current_url
            )
            
            # Display notification to user
            if config.ENABLE_VERIFICATION_NOTIFICATIONS:
                verification_handler.display_notification(challenge_type)
            
            # Log event start
            verification_handler.log_event(event)
            
            # Wait for manual verification (Requirements 8.1)
            # Expected URL pattern after profile update is the profile page itself
            verification_success = verification_handler.wait_for_manual_verification(
                expected_url_pattern=PROFILE_URL
            )
            
            if verification_success:
                # Verification completed successfully
                event.complete(success=True)
                verification_handler.log_event(event)
                logger.info("Manual verification completed successfully during profile update")
            else:
                # Verification timed out
                event.complete(success=False, timeout=True, failure_reason="Verification timeout")
                verification_handler.log_event(event)
                logger.warning("Manual verification timed out during profile update")
                return False
        else:
            logger.debug("No PerimeterX challenge detected, continuing normal flow")
        
        # Monitor for 302 response (Requirements 5.6)
        logger.info(f"Waiting for 302 response from: {PROFILE_SUBMIT_URL_PATTERN}")
        success = self.browser.wait_for_response(
            PROFILE_SUBMIT_URL_PATTERN, 
            status_code=302, 
            timeout=timeout
        )
        
        if success:
            logger.info("Profile update successful - 302 response detected")
        else:
            logger.warning("Profile update may have failed - 302 response not detected")
        
        return success

    def update_profile(self, month: str, day: int, phone_number: str) -> bool:
        """Execute the complete profile update flow.
        
        This is a convenience method that combines all profile update steps:
        1. Fill the profile form
        2. Submit and verify success
        
        Args:
            month: English month name (e.g., "January")
            day: Day of the month (1-28)
            phone_number: Phone number to fill in both phone fields
            
        Returns:
            True if profile update was successful, False otherwise
            
        Requirements: 5.1-5.6
        """
        try:
            # Step 1: Fill the form (Requirements 5.1-5.4)
            self.fill_profile_form(month, day, phone_number)
            
            # Step 2: Submit and verify (Requirements 5.5, 5.6)
            return self.submit_and_verify()
            
        except ProfileUpdateError as e:
            logger.error(f"Profile update failed: {e}")
            return False
        except ValueError as e:
            logger.error(f"Invalid input: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during profile update: {e}")
            return False


def fill_profile_form(browser: BrowserController, month: str, day: int, phone_number: str) -> None:
    """Convenience function to fill profile form.
    
    Args:
        browser: BrowserController instance
        month: English month name (e.g., "January")
        day: Day of the month (1-28)
        phone_number: Phone number to fill in both phone fields
    """
    profile_update = ProfileUpdate(browser)
    profile_update.fill_profile_form(month, day, phone_number)


def submit_and_verify(browser: BrowserController, timeout: Optional[int] = None) -> bool:
    """Convenience function to submit form and verify success.
    
    Args:
        browser: BrowserController instance
        timeout: Maximum time to wait for success in milliseconds
        
    Returns:
        True if profile update was successful, False otherwise
    """
    profile_update = ProfileUpdate(browser)
    return profile_update.submit_and_verify(timeout)
