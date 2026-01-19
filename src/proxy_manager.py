"""
Proxy Manager module for Ralph Lauren Auto Register System.

Handles proxy generation, validation, and US region filtering.
"""

import random
import time
from typing import Optional
import requests

from src.config import Config
from src.models import ProxyValidationResult


class ProxyManager:
    """Manages proxy generation, validation, and selection."""
    
    VALIDATION_URL = "http://ip-api.com/json/"
    VALIDATION_TIMEOUT = 10  # seconds
    MAX_RETRY_ATTEMPTS = 10
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize ProxyManager with configuration.
        
        Args:
            config: Configuration object. Uses default if not provided.
        """
        self.config = config or Config()
    
    def generate_proxy(self) -> str:
        """Generate a proxy URL with random port.
        
        Returns:
            Proxy URL in format http://{ip}:{port}
            
        Requirements: 2.1
        """
        port = random.randint(self.config.PROXY_PORT_MIN, self.config.PROXY_PORT_MAX)
        return f"http://{self.config.PROXY_IP}:{port}"
    
    def validate_proxy(self, proxy_url: str) -> ProxyValidationResult:
        """Validate a proxy by checking response from ip-api.com.
        
        Measures connection latency and verifies location.
        
        Args:
            proxy_url: The proxy URL to validate
            
        Returns:
            ProxyValidationResult with validation details
            
        Requirements: 2.2, 2.3, 2.4
        """
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        try:
            start_time = time.time()
            response = requests.get(
                self.VALIDATION_URL,
                proxies=proxies,
                timeout=self.VALIDATION_TIMEOUT
            )
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                return ProxyValidationResult(
                    is_valid=False,
                    latency_ms=latency_ms,
                    country="",
                    region=""
                )
            
            data = response.json()
            country = data.get("countryCode", "")
            region = data.get("regionName", "")
            
            # Proxy is valid only if it's in the US
            is_valid = country == "US"
            
            return ProxyValidationResult(
                is_valid=is_valid,
                latency_ms=latency_ms,
                country=country,
                region=region
            )
            
        except (requests.RequestException, ValueError) as e:
            return ProxyValidationResult(
                is_valid=False,
                latency_ms=0.0,
                country="",
                region=""
            )
    
    def get_valid_us_proxy(self) -> Optional[str]:
        """Get a valid US proxy, retrying with different ports if needed.
        
        Returns:
            Valid US proxy URL, or None if no valid proxy found after max retries
            
        Requirements: 2.5
        """
        for _ in range(self.MAX_RETRY_ATTEMPTS):
            proxy_url = self.generate_proxy()
            result = self.validate_proxy(proxy_url)
            
            if result.is_valid:
                return proxy_url
        
        return None


def generate_proxy_url(ip: str, port_min: int, port_max: int) -> str:
    """Generate a proxy URL with random port in the given range.
    
    This is a standalone function for testing purposes.
    
    Args:
        ip: Proxy IP address
        port_min: Minimum port number (inclusive)
        port_max: Maximum port number (inclusive)
        
    Returns:
        Proxy URL in format http://{ip}:{port}
    """
    port = random.randint(port_min, port_max)
    return f"http://{ip}:{port}"


def is_us_proxy(validation_result: ProxyValidationResult) -> bool:
    """Check if a proxy validation result indicates a US proxy.
    
    Args:
        validation_result: The validation result to check
        
    Returns:
        True if the proxy is in the US, False otherwise
    """
    return validation_result.country == "US"
