"""
API Client for Ralph Lauren Auto Register System.

Fetches user data from the configured API endpoint without using proxy.
"""

import requests
from typing import Optional

from src.config import config
from src.models import UserData


class APIClient:
    """Client for fetching user data from the API."""
    
    def __init__(self, api_url: Optional[str] = None, timeout: int = 30):
        """Initialize API client.
        
        Args:
            api_url: API endpoint URL. Defaults to config.API_URL.
            timeout: Request timeout in seconds.
        """
        self.api_url = api_url or config.API_URL
        self.timeout = timeout
    
    def fetch_user_data(self) -> UserData:
        """Fetch user data from the API without using proxy.
        
        Returns:
            UserData object containing email, first_name, last_name, 
            password, and phone_number.
            
        Raises:
            requests.RequestException: If the API request fails.
            KeyError: If required fields are missing from the response.
            ValueError: If the response cannot be parsed as JSON.
        """
        # Make request without proxy (Requirements 1.4)
        response = requests.get(
            self.api_url,
            timeout=self.timeout,
            proxies={"http": None, "https": None}  # Explicitly bypass proxy
        )
        response.raise_for_status()
        
        # Parse JSON response (Requirements 1.2)
        data = response.json()
        
        # Extract required fields and create UserData (Requirements 1.1)
        return UserData.from_dict(data)


# Default client instance
api_client = APIClient()


def fetch_user_data() -> UserData:
    """Convenience function to fetch user data using default client.
    
    Returns:
        UserData object containing user registration data.
    """
    return api_client.fetch_user_data()
