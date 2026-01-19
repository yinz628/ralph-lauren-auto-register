"""
Main runner for Ralph Lauren Auto Register System.

Coordinates all modules to execute batch registration with
iteration intervals and error handling.
"""

import logging
import time
from typing import Optional

from src.config import Config, config
from src.api_client import APIClient
from src.proxy_manager import ProxyManager
from src.browser_controller import BrowserController
from src.registration import Registration
from src.profile_update import ProfileUpdate
from src.storage import Storage
from src.date_utils import generate_random_day
from src.models import AccountRecord, UserData


# Configure logging
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('main.log', encoding='utf-8')  # File output
    ]
)
logger = logging.getLogger(__name__)


class MainRunner:
    """Main runner that coordinates batch registration.
    
    Orchestrates the complete registration flow including:
    - Fetching user data from API
    - Getting valid US proxy
    - Browser automation for registration
    - Profile update
    - Data storage
    """
    
    def __init__(self, cfg: Optional[Config] = None):
        """Initialize MainRunner with configuration.
        
        Args:
            cfg: Configuration object. Uses default if not provided.
        """
        self.config = cfg or config
        self.api_client = APIClient(self.config.API_URL)
        self.proxy_manager = ProxyManager(self.config)
        self.storage = Storage(self.config.OUTPUT_FILE)

    def run_single_iteration(self, iteration_num: int) -> bool:
        """Execute a single registration iteration.
        
        Performs the complete flow:
        1. Fetch user data from API
        2. Get valid US proxy
        3. Start browser with proxy
        4. Register account
        5. Update profile
        6. Save successful account
        
        Handles manual verification timeouts by:
        - Logging timeout events
        - Cleaning up browser resources
        - Marking iteration as failed
        - Continuing to next iteration
        
        Args:
            iteration_num: Current iteration number (for logging)
            
        Returns:
            True if registration was successful, False otherwise
            
        Requirements: 8.1, 4.3, 4.4, 4.5
        """
        logger.info(f"Starting iteration {iteration_num}")
        browser = None
        
        try:
            # Step 1: Fetch user data from API
            logger.info("Fetching user data from API...")
            user_data = self.api_client.fetch_user_data()
            logger.info(f"User data fetched: {user_data.email}")
            
            # Step 2: Get valid US proxy
            logger.info("Getting valid US proxy...")
            proxy_url = self.proxy_manager.get_valid_us_proxy()
            if not proxy_url:
                logger.error("Failed to get valid US proxy after max retries")
                return False
            logger.info(f"Valid US proxy obtained: {proxy_url}")
            
            # Step 3: Generate random day for birthday
            random_day = generate_random_day()
            birthday = f"{self.config.MONTH} {random_day}"
            logger.info(f"Generated birthday: {birthday}")
            
            # Step 4: Start browser with proxy
            logger.info("Starting browser...")
            browser = BrowserController(proxy_url)
            browser.start(headless=False)
            logger.info("Browser started successfully")
            
            # Step 5: Execute registration
            logger.info("Starting registration flow...")
            registration = Registration(browser)
            registration_success = registration.register(user_data)
            
            if not registration_success:
                # Registration failed - could be due to verification timeout (Requirements 4.3, 4.4)
                logger.error("Registration failed - this may be due to manual verification timeout")
                logger.info("Marking iteration as failed and will proceed to next iteration")
                return False
            logger.info("Registration completed successfully")
            
            # Step 6: Update profile
            logger.info("Starting profile update...")
            profile_update = ProfileUpdate(browser)
            profile_success = profile_update.update_profile(
                month=self.config.MONTH,
                day=random_day,
                phone_number=user_data.phone_number
            )
            
            if not profile_success:
                # Profile update failed - could be due to verification timeout (Requirements 4.3, 4.4)
                logger.warning("Profile update failed - this may be due to manual verification timeout")
                logger.warning("Registration was successful, but profile update failed")
                # Continue to save the account even if profile update fails
            else:
                logger.info("Profile update completed successfully")
            
            # Step 7: Save successful account
            record = AccountRecord(
                email=user_data.email,
                password=user_data.password,
                birthday=birthday
            )
            self.storage.save_success(record)
            logger.info(f"Account saved: {user_data.email}")
            
            return True
            
        except Exception as e:
            logger.error(f"Iteration {iteration_num} failed with error: {e}")
            return False
            
        finally:
            # Clean up browser resources (Requirements 4.4, 4.5)
            if browser:
                try:
                    browser.stop()
                    logger.info("Browser stopped and resources cleaned up")
                except Exception as e:
                    logger.warning(f"Error stopping browser: {e}")

    def run(self) -> dict:
        """Execute batch registration for configured iteration count.
        
        Runs multiple registration iterations with configured intervals
        between each iteration. Logs errors and continues to next
        iteration on failure.
        
        Handles manual verification timeouts by:
        - Logging timeout events when iterations fail
        - Continuing to next iteration after timeout
        - Tracking failed iterations in results
        
        Returns:
            Dictionary with results:
            - total: Total number of iterations
            - successful: Number of successful registrations
            - failed: Number of failed registrations
            
        Requirements: 8.1, 8.2, 8.3, 4.3, 4.4, 4.5
        """
        total = self.config.ITERATION_COUNT
        successful = 0
        failed = 0
        
        logger.info(f"Starting batch registration: {total} iterations")
        logger.info(f"Interval between iterations: {self.config.ITERATION_INTERVAL} seconds")
        
        for i in range(1, total + 1):
            logger.info(f"=== Iteration {i}/{total} ===")
            
            try:
                # Run single iteration (Requirements 8.1)
                success = self.run_single_iteration(i)
                
                if success:
                    successful += 1
                    logger.info(f"Iteration {i} completed successfully")
                else:
                    failed += 1
                    # Log failure - could be due to verification timeout (Requirements 4.3, 4.5)
                    logger.warning(f"Iteration {i} failed - possible causes: verification timeout, registration error, or profile update error")
                    logger.info(f"Proceeding to next iteration (Requirements 4.4)")
                    
            except Exception as e:
                # Log error and continue to next iteration (Requirements 8.3, 4.4)
                failed += 1
                logger.error(f"Iteration {i} failed with exception: {e}")
                logger.info(f"Proceeding to next iteration after exception")
            
            # Wait for configured interval before next iteration (Requirements 8.2)
            if i < total:
                logger.info(f"Waiting {self.config.ITERATION_INTERVAL} seconds before next iteration...")
                time.sleep(self.config.ITERATION_INTERVAL)
        
        # Log final results
        logger.info("=== Batch Registration Complete ===")
        logger.info(f"Total: {total}, Successful: {successful}, Failed: {failed}")
        
        return {
            "total": total,
            "successful": successful,
            "failed": failed
        }


def run() -> dict:
    """Main entry point for the registration system.
    
    Creates a MainRunner instance and executes batch registration.
    
    Returns:
        Dictionary with batch registration results
        
    Requirements: 8.1, 8.2, 8.3
    """
    runner = MainRunner()
    return runner.run()


if __name__ == "__main__":
    results = run()
    print(f"\nResults: {results}")
