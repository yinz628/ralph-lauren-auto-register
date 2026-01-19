"""
Registration module for Ralph Lauren Auto Register System.

Handles the complete registration flow including form filling,
submission, and success verification.
"""

from typing import Optional
import logging
import time

from src.browser_controller import BrowserController
from src.models import UserData
from src.manual_verification import ManualVerificationHandler, VerificationEvent
from src.config import config
from datetime import datetime


# URLs
REGISTRATION_URL = "https://www.ralphlauren.com/register"
SUCCESS_URL_PATTERN = "pplp/account?fromAccountLogin=true"
PROFILE_URL = "https://www.ralphlauren.com/profile"
REGISTRATION_API_URL = "Account-RegistrationForm"

# Element selectors
EMAIL_SELECTOR = "#dwfrm_profile_customer_email"
PASSWORD_BASE_PATTERN = "dwfrm_profile_login_password_"
PASSWORD_CONFIRM_BASE_PATTERN = "dwfrm_profile_login_passwordconfirm_"
FIRSTNAME_SELECTOR = "#dwfrm_profile_customer_firstname"
LASTNAME_SELECTOR = "#dwfrm_profile_customer_lastname"
SUBMIT_BUTTON_SELECTOR = '[name="dwfrm_profile_confirm"]'

# Timeouts
NAVIGATION_TIMEOUT = 30000  # 30 seconds

logger = logging.getLogger(__name__)


class RegistrationError(Exception):
    """Exception raised when registration fails."""
    pass


class Registration:
    """Handles Ralph Lauren account registration flow.
    
    Provides methods to fill the registration form and submit it,
    with verification of successful registration.
    """
    
    def __init__(self, browser: BrowserController):
        """Initialize Registration module.
        
        Args:
            browser: BrowserController instance for browser automation
        """
        self.browser = browser

    def navigate_to_registration(self) -> None:
        """Navigate to the registration page.
        
        Requirements: 4.1
        """
        logger.info(f"Navigating to registration page: {REGISTRATION_URL}")
        self.browser.navigate(REGISTRATION_URL)
        
        # Wait for page to fully load
        time.sleep(30)
    
    def fill_registration_form(self, user_data: UserData) -> None:
        """Fill the registration form with user data.
        
        Handles dynamic ID selectors for password fields that have
        12-character random suffixes.
        
        Args:
            user_data: UserData object containing registration information
            
        Raises:
            RegistrationError: If required form elements cannot be found
            
        Requirements: 4.2, 4.3, 4.4, 4.5, 4.6
        """
        logger.info(f"Filling registration form for: {user_data.email}")
        
        # Fill email field (Requirements 4.2)
        if not self.browser.wait_for_element(EMAIL_SELECTOR):
            raise RegistrationError("Email field not found")
        self.browser.fill_input(EMAIL_SELECTOR, user_data.email)
        logger.debug("Email field filled")
        
        # Fill password field with dynamic ID (Requirements 4.3)
        if not self.browser.fill_input_by_dynamic_id(PASSWORD_BASE_PATTERN, user_data.password):
            raise RegistrationError("Password field not found")
        logger.debug("Password field filled")
        
        # Fill password confirmation with dynamic ID (Requirements 4.4)
        if not self.browser.fill_input_by_dynamic_id(PASSWORD_CONFIRM_BASE_PATTERN, user_data.password):
            raise RegistrationError("Password confirmation field not found")
        logger.debug("Password confirmation field filled")
        
        # Fill first name (Requirements 4.5)
        if not self.browser.wait_for_element(FIRSTNAME_SELECTOR):
            raise RegistrationError("First name field not found")
        self.browser.fill_input(FIRSTNAME_SELECTOR, user_data.first_name)
        logger.debug("First name field filled")
        
        # Fill last name (Requirements 4.6)
        if not self.browser.wait_for_element(LASTNAME_SELECTOR):
            raise RegistrationError("Last name field not found")
        self.browser.fill_input(LASTNAME_SELECTOR, user_data.last_name)
        logger.debug("Last name field filled")
        
        logger.info("Registration form filled successfully")

    def submit_and_verify(self, timeout: Optional[int] = None) -> bool:
        """Submit the registration form and verify success.
        
        Clicks the submit button, detects PerimeterX challenges, enters manual
        verification mode if needed, and monitors for the registration API
        response with status code 302 to determine if registration was successful.
        
        Args:
            timeout: Maximum time to wait for success in milliseconds.
                    Defaults to NAVIGATION_TIMEOUT.
                    
        Returns:
            True if registration was successful, False otherwise
            
        Requirements: 2.1, 2.2, 2.3, 4.7, 4.8, 9.6
        """
        timeout = timeout or NAVIGATION_TIMEOUT
        
        logger.info("Submitting registration form")
        
        # Click submit button (Requirements 4.7)
        if not self.browser.wait_for_element(SUBMIT_BUTTON_SELECTOR):
            logger.error("Submit button not found")
            return False
        
        self.browser.click_button(SUBMIT_BUTTON_SELECTOR)
        logger.debug("Submit button clicked")
        
        # Wait a moment for potential PerimeterX challenge to appear
        time.sleep(2)
        
        # Initialize manual verification handler
        verification_handler = ManualVerificationHandler(
            self.browser, 
            timeout=config.MANUAL_VERIFICATION_TIMEOUT
        )
        
        # Detect PerimeterX challenge (Requirements 2.1, 9.6)
        challenge_type = verification_handler.detect_challenge()
        
        if challenge_type:
            # Challenge detected - enter manual verification mode (Requirements 2.1, 2.2, 2.3)
            logger.info(f"PerimeterX challenge detected: {challenge_type}")
            
            # Create verification event
            event = VerificationEvent(
                challenge_type=challenge_type,
                start_time=datetime.now(),
                page_url=self.browser.current_url
            )
            
            # Display notification to user (Requirements 2.2)
            if config.ENABLE_VERIFICATION_NOTIFICATIONS:
                verification_handler.display_notification(challenge_type)
            
            # Log event start
            verification_handler.log_event(event)
            
            # Wait for manual verification (Requirements 2.3, 4.7, 4.8)
            verification_success = verification_handler.wait_for_manual_verification(
                expected_url_pattern=SUCCESS_URL_PATTERN
            )
            
            if verification_success:
                # Verification completed successfully
                event.complete(success=True)
                verification_handler.log_event(event)
                logger.info("Manual verification completed successfully")
            else:
                # Verification timed out
                event.complete(success=False, timeout=True, failure_reason="Verification timeout")
                verification_handler.log_event(event)
                logger.warning("Manual verification timed out")
                return False
        else:
            logger.debug("No PerimeterX challenge detected, continuing normal flow")
        
        # Monitor for registration API response with 302 status (Requirements 4.8)
        logger.info(f"Waiting for registration API response: {REGISTRATION_API_URL}")
        response_data = self.browser.wait_for_response_with_data(
            REGISTRATION_API_URL, 
            status_code=302, 
            timeout=timeout
        )
        
        if response_data:
            logger.info(f"Registration API response received - Status: {response_data['status']}")
            logger.info(f"Response URL: {response_data['url']}")
            logger.debug(f"Response headers: {response_data['headers']}")
            logger.debug(f"Response body: {response_data['body']}")
            logger.info("Registration successful - 302 redirect detected")
            return True
        else:
            logger.warning("Registration may have failed - 302 response not detected")
            return False
    

    def navigate_to_profile(self) -> None:
        """Navigate to the profile page after successful registration.
        
        Requirements: 4.9
        """
        logger.info(f"Navigating to profile page: {PROFILE_URL}")
        self.browser.navigate(PROFILE_URL)
    
    def register(self, user_data: UserData) -> bool:
        """Execute the complete registration flow.
        
        This is a convenience method that combines all registration steps:
        1. Navigate to registration page
        2. Fill the registration form
        3. Submit and verify success
        4. Navigate to profile page on success
        
        Args:
            user_data: UserData object containing registration information
            
        Returns:
            True if registration was successful, False otherwise
            
        Requirements: 4.1-4.9
        """
        try:
            # Step 1: Navigate to registration page (Requirements 4.1)
            self.navigate_to_registration()
            
            # Step 2: Fill the form (Requirements 4.2-4.6)
            self.fill_registration_form(user_data)
            
            # Step 3: Submit and verify (Requirements 4.7, 4.8)
            success = self.submit_and_verify()
            
            # Step 4: Navigate to profile on success (Requirements 4.9)
            if success:
                self.navigate_to_profile()
            
            return success
            
        except RegistrationError as e:
            logger.error(f"Registration failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during registration: {e}")
            return False


def fill_registration_form(browser: BrowserController, user_data: UserData) -> None:
    """Convenience function to fill registration form.
    
    Args:
        browser: BrowserController instance
        user_data: UserData object containing registration information
    """
    registration = Registration(browser)
    registration.fill_registration_form(user_data)


def submit_and_verify(browser: BrowserController, timeout: Optional[int] = None) -> bool:
    """Convenience function to submit form and verify success.
    
    Args:
        browser: BrowserController instance
        timeout: Maximum time to wait for success in milliseconds
        
    Returns:
        True if registration was successful, False otherwise
    """
    registration = Registration(browser)
    return registration.submit_and_verify(timeout)
