"""
Configuration module for Ralph Lauren Auto Register System.

Contains all system parameters including API endpoint, proxy settings,
iteration configuration, and output file settings.
"""

from dataclasses import dataclass


@dataclass
class Config:
    """Configuration class containing all system parameters."""
    
    # API Configuration
    API_URL: str = "http://127.0.0.1:8000/identity/"
    
    # Proxy Configuration
    PROXY_IP: str = "127.0.0.1"
    PROXY_PORT_MIN: int = 7897
    PROXY_PORT_MAX: int = 7897
    
    # Registration Configuration
    MONTH: str = "January"
    
    # Iteration Configuration
    ITERATION_COUNT: int = 10
    ITERATION_INTERVAL: int = 30  # seconds between iterations
    
    # Output Configuration
    OUTPUT_FILE: str = "accounts.txt"
    
    # PerimeterX Configuration
    PX_APP_ID: str = "pxjbdhncwl"
    PX_COLLECTOR_URL: str = "https://collector-pxjbdhncwl.px-cloud.net"
    
    # Manual Verification Configuration
    MANUAL_VERIFICATION_TIMEOUT: int = 120  # seconds
    ENABLE_VERIFICATION_NOTIFICATIONS: bool = True
    MAX_VERIFICATION_ATTEMPTS: int = 3


# Default configuration instance
config = Config()
