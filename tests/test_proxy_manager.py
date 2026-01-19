"""
Property-based tests for proxy manager module.

Uses hypothesis library for property-based testing.
"""

import re
import pytest
from hypothesis import given, strategies as st, settings

from src.proxy_manager import generate_proxy_url, is_us_proxy
from src.models import ProxyValidationResult


# Strategy for generating valid IP addresses
ip_strategy = st.from_regex(
    r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',
    fullmatch=True
)

# Strategy for generating valid port ranges within 50000-50020
port_min_strategy = st.integers(min_value=50000, max_value=50019)


@given(
    ip=ip_strategy,
    port_min=port_min_strategy
)
@settings(max_examples=100)
def test_proxy_url_format_correctness(ip, port_min):
    """
    **Feature: ralph-lauren-auto-register, Property 3: 代理URL格式正确性**
    
    *For any* generated proxy URL, it SHALL contain the configured IP address 
    and a port number within the range 50000 to 50020.
    
    **Validates: Requirements 2.1**
    """
    port_max = port_min + 1  # Ensure valid range
    
    # Generate proxy URL
    proxy_url = generate_proxy_url(ip, port_min, port_max)
    
    # Verify URL format: http://{ip}:{port}
    pattern = r'^http://(.+):(\d+)$'
    match = re.match(pattern, proxy_url)
    
    assert match is not None, f"Proxy URL '{proxy_url}' does not match expected format"
    
    extracted_ip = match.group(1)
    extracted_port = int(match.group(2))
    
    # Verify IP matches
    assert extracted_ip == ip, f"IP mismatch: expected {ip}, got {extracted_ip}"
    
    # Verify port is within range
    assert port_min <= extracted_port <= port_max, \
        f"Port {extracted_port} not in range [{port_min}, {port_max}]"


# Strategy for generating country codes
country_strategy = st.sampled_from(["US", "CA", "GB", "DE", "FR", "JP", "CN", "AU", "BR", ""])


@given(
    country=country_strategy,
    latency=st.floats(min_value=0, max_value=10000, allow_nan=False),
    region=st.text(max_size=50)
)
@settings(max_examples=100)
def test_us_proxy_filter_correctness(country, latency, region):
    """
    **Feature: ralph-lauren-auto-register, Property 4: US代理筛选正确性**
    
    *For any* proxy validation result, if the country code is "US" then 
    is_valid SHALL be true, otherwise is_valid SHALL be false.
    
    **Validates: Requirements 2.4**
    """
    # Create validation result with the given country
    # Note: is_valid in the result reflects whether it passed validation,
    # but is_us_proxy function checks if country is US
    validation_result = ProxyValidationResult(
        is_valid=True,  # Assume proxy connection succeeded
        latency_ms=latency,
        country=country,
        region=region
    )
    
    # Check if is_us_proxy correctly identifies US proxies
    result = is_us_proxy(validation_result)
    
    if country == "US":
        assert result is True, f"US proxy should be identified as valid US proxy"
    else:
        assert result is False, f"Non-US proxy (country={country}) should not be identified as US proxy"
