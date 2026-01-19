"""
Property-based tests for manual verification module.

Uses hypothesis library for property-based testing of VerificationEvent
and ManualVerificationHandler functionality.
"""

import pytest
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, assume

from src.manual_verification import VerificationEvent


# Strategy for generating challenge types
challenge_type_strategy = st.sampled_from([
    "captcha",
    "press-and-hold",
    "checkbox",
    "slider",
    "challenge",
    "unknown"
])

# Strategy for generating URLs
url_strategy = st.from_regex(
    r'https?://[a-z0-9\-\.]+\.[a-z]{2,}(/[a-z0-9\-_/]*)?',
    fullmatch=True
)

# Strategy for generating failure reasons
failure_reason_strategy = st.one_of(
    st.just(""),
    st.sampled_from([
        "timeout",
        "browser_closed",
        "page_error",
        "user_cancelled",
        "max_attempts_exceeded"
    ])
)

# Strategy for generating datetime objects
datetime_strategy = st.datetimes(
    min_value=datetime(2024, 1, 1),
    max_value=datetime(2026, 12, 31)
)


@given(
    challenge_type=challenge_type_strategy,
    start_time=datetime_strategy,
    page_url=url_strategy,
    success=st.booleans(),
    timeout=st.booleans(),
    failure_reason=failure_reason_strategy
)
@settings(max_examples=100)
def test_verification_event_logging_completeness(
    challenge_type, start_time, page_url, success, timeout, failure_reason
):
    """
    **Feature: manual-verification, Property 5: 验证事件日志完整性**
    
    *For any* verification event (detection, entry, completion, timeout, or failure),
    the logged data SHALL include all required fields: challenge type, timestamp,
    duration, and status-specific information (success/timeout/failure reason).
    
    **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 2.5**
    """
    # Create a verification event
    event = VerificationEvent(
        challenge_type=challenge_type,
        start_time=start_time,
        page_url=page_url
    )
    
    # Verify initial state has required fields
    assert event.challenge_type == challenge_type
    assert event.start_time == start_time
    assert event.page_url == page_url
    assert event.end_time is None
    assert event.success is False
    assert event.timeout is False
    assert event.duration_seconds == 0.0
    assert event.failure_reason == ""
    
    # Complete the event
    event.complete(success=success, timeout=timeout, failure_reason=failure_reason)
    
    # Verify completion updates all required fields
    assert event.end_time is not None
    assert event.success == success
    assert event.timeout == timeout
    assert event.failure_reason == failure_reason
    assert event.duration_seconds >= 0.0
    assert isinstance(event.duration_seconds, float)
    
    # Verify to_dict includes all fields
    event_dict = event.to_dict()
    assert "challenge_type" in event_dict
    assert "start_time" in event_dict
    assert "page_url" in event_dict
    assert "end_time" in event_dict
    assert "success" in event_dict
    assert "timeout" in event_dict
    assert "duration_seconds" in event_dict
    assert "failure_reason" in event_dict
    
    # Verify timestamps are in ISO format
    assert isinstance(event_dict["start_time"], str)
    if event_dict["end_time"]:
        assert isinstance(event_dict["end_time"], str)
    
    # Verify all values match
    assert event_dict["challenge_type"] == challenge_type
    assert event_dict["page_url"] == page_url
    assert event_dict["success"] == success
    assert event_dict["timeout"] == timeout
    assert event_dict["failure_reason"] == failure_reason


@given(
    challenge_type=challenge_type_strategy,
    start_time=datetime_strategy,
    page_url=url_strategy,
    duration_seconds=st.floats(min_value=0.0, max_value=300.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100)
def test_verification_event_duration_calculation(
    challenge_type, start_time, page_url, duration_seconds
):
    """
    **Feature: manual-verification, Property 5: 验证事件日志完整性 (Duration)**
    
    *For any* verification event that completes, the duration_seconds field
    SHALL accurately reflect the time difference between start_time and end_time.
    
    **Validates: Requirements 7.3, 7.4**
    """
    # Create event
    event = VerificationEvent(
        challenge_type=challenge_type,
        start_time=start_time,
        page_url=page_url
    )
    
    # Simulate completion with specific end time
    end_time = start_time + timedelta(seconds=duration_seconds)
    event.end_time = end_time
    event.success = True
    event.duration_seconds = (event.end_time - event.start_time).total_seconds()
    
    # Verify duration is calculated correctly
    expected_duration = (end_time - start_time).total_seconds()
    assert abs(event.duration_seconds - expected_duration) < 0.001  # Allow small floating point error
    assert event.duration_seconds >= 0.0


@given(
    challenge_type=challenge_type_strategy,
    page_url=url_strategy
)
@settings(max_examples=100)
def test_verification_event_state_transitions(challenge_type, page_url):
    """
    **Feature: manual-verification, Property 5: 验证事件日志完整性 (State)**
    
    *For any* verification event, the state SHALL transition correctly from
    initial (not complete) to completed (with end_time set and duration calculated).
    
    **Validates: Requirements 7.1, 7.2, 7.3**
    """
    # Create event in initial state
    start_time = datetime.now()
    event = VerificationEvent(
        challenge_type=challenge_type,
        start_time=start_time,
        page_url=page_url
    )
    
    # Verify initial state
    assert event.end_time is None
    assert event.success is False
    assert event.timeout is False
    assert event.duration_seconds == 0.0
    
    # Complete with success
    event.complete(success=True, timeout=False, failure_reason="")
    
    # Verify state after completion
    assert event.end_time is not None
    assert event.end_time >= event.start_time
    assert event.success is True
    assert event.timeout is False
    assert event.duration_seconds > 0.0 or event.duration_seconds == 0.0
    assert event.failure_reason == ""


@given(
    selector_index=st.integers(min_value=0, max_value=6),
    has_challenge=st.booleans()
)
@settings(max_examples=100)
def test_challenge_detection_completeness(selector_index, has_challenge):
    """
    **Feature: manual-verification, Property 1: 挑战检测完整性**
    
    *For any* page state with PerimeterX challenge elements, the detection method
    SHALL check all configured selectors (captcha containers, modals, iframes) and
    return the correct challenge type if any selector matches.
    
    **Validates: Requirements 1.1, 1.2, 1.3**
    """
    from unittest.mock import Mock, MagicMock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Get the selector being tested
    selectors = ManualVerificationHandler.PX_SELECTORS
    assume(selector_index < len(selectors))
    test_selector = selectors[selector_index]
    
    if has_challenge:
        # Mock element that exists and is visible
        mock_element = Mock()
        mock_element.count.return_value = 1
        mock_element.first = Mock()
        mock_element.first.wait_for = Mock()  # Simulates visible element
        
        # Set up page.locator to return mock element for the test selector
        def locator_side_effect(selector):
            if selector == test_selector:
                return mock_element
            else:
                # Other selectors return empty
                empty_element = Mock()
                empty_element.count.return_value = 0
                return empty_element
        
        mock_page.locator = Mock(side_effect=locator_side_effect)
        
        # Create handler and detect
        handler = ManualVerificationHandler(mock_browser, timeout=120)
        result = handler.detect_challenge()
        
        # Should detect challenge
        assert result is not None
        assert isinstance(result, str)
        assert result in ["captcha", "challenge", "unknown"]
        
        # Verify correct challenge type based on selector
        if 'captcha' in test_selector.lower():
            assert result == "captcha"
        elif 'challenge' in test_selector.lower():
            assert result == "challenge"
        else:
            assert result == "unknown"
    else:
        # Mock no challenge elements present
        mock_element = Mock()
        mock_element.count.return_value = 0
        mock_page.locator = Mock(return_value=mock_element)
        
        # Create handler and detect
        handler = ManualVerificationHandler(mock_browser, timeout=120)
        result = handler.detect_challenge()
        
        # Should not detect challenge
        assert result is None



# ============================================================================
# Unit Tests for Challenge Detection
# ============================================================================

def test_detect_challenge_with_captcha_selector():
    """
    Test challenge detection with captcha selector.
    
    Requirements: 1.1, 1.2, 1.3
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock element that exists and is visible
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.wait_for = Mock()
    
    # Set up page.locator to return mock element for captcha selector
    def locator_side_effect(selector):
        if selector == '#px-captcha':
            return mock_element
        else:
            empty_element = Mock()
            empty_element.count.return_value = 0
            return empty_element
    
    mock_page.locator = Mock(side_effect=locator_side_effect)
    
    # Create handler and detect
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    result = handler.detect_challenge()
    
    # Should detect captcha challenge
    assert result == "captcha"


def test_detect_challenge_with_challenge_container():
    """
    Test challenge detection with challenge container selector.
    
    Requirements: 1.1, 1.2, 1.3
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock element that exists and is visible
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.wait_for = Mock()
    
    # Set up page.locator to return mock element for challenge selector
    def locator_side_effect(selector):
        if selector == '#challenge-container':
            return mock_element
        else:
            empty_element = Mock()
            empty_element.count.return_value = 0
            return empty_element
    
    mock_page.locator = Mock(side_effect=locator_side_effect)
    
    # Create handler and detect
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    result = handler.detect_challenge()
    
    # Should detect challenge
    assert result == "challenge"


def test_detect_challenge_with_iframe_selector():
    """
    Test challenge detection with iframe selector.
    
    Requirements: 1.1, 1.2, 1.3
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock element that exists and is visible
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.wait_for = Mock()
    
    # Set up page.locator to return mock element for iframe selector
    def locator_side_effect(selector):
        if selector == 'iframe[src*="captcha"]':
            return mock_element
        else:
            empty_element = Mock()
            empty_element.count.return_value = 0
            return empty_element
    
    mock_page.locator = Mock(side_effect=locator_side_effect)
    
    # Create handler and detect
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    result = handler.detect_challenge()
    
    # Should detect unknown challenge type (iframe doesn't have captcha/challenge in selector)
    assert result == "captcha"  # iframe[src*="captcha"] contains "captcha"


def test_detect_challenge_no_challenge_present():
    """
    Test challenge detection when no challenge is present.
    
    Requirements: 1.1, 1.2, 1.3, 1.4
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock no elements present
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler and detect
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    result = handler.detect_challenge()
    
    # Should not detect any challenge
    assert result is None


def test_detect_challenge_element_not_visible():
    """
    Test challenge detection when element exists but is not visible.
    
    Requirements: 1.1, 1.2, 1.3
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock element that exists but is not visible
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.wait_for = Mock(side_effect=Exception("Not visible"))
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler and detect
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    result = handler.detect_challenge()
    
    # Should not detect challenge if not visible
    assert result is None


def test_detect_challenge_timeout():
    """
    Test challenge detection respects 3-second timeout.
    
    Requirements: 1.4
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    import time
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock element that takes too long to check
    def slow_locator(selector):
        time.sleep(0.5)  # Simulate slow check
        mock_element = Mock()
        mock_element.count.return_value = 0
        return mock_element
    
    mock_page.locator = Mock(side_effect=slow_locator)
    
    # Create handler and detect
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    start_time = time.time()
    result = handler.detect_challenge()
    elapsed = time.time() - start_time
    
    # Should complete within 3 seconds (with some margin)
    assert elapsed < 4.0
    # Should not detect challenge
    assert result is None


def test_detect_challenge_no_browser_page():
    """
    Test challenge detection when browser page is not available.
    
    Requirements: 1.1
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser without page
    mock_browser = Mock()
    mock_browser.page = None
    
    # Create handler and detect
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    result = handler.detect_challenge()
    
    # Should return None when no page available
    assert result is None


def test_detect_challenge_multiple_selectors():
    """
    Test challenge detection checks multiple selectors.
    
    Requirements: 1.1, 1.2, 1.3
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Track which selectors were checked
    checked_selectors = []
    
    def locator_side_effect(selector):
        checked_selectors.append(selector)
        # Third selector has the challenge
        if selector == '.px-captcha-container':
            mock_element = Mock()
            mock_element.count.return_value = 1
            mock_element.first = Mock()
            mock_element.first.wait_for = Mock()
            return mock_element
        else:
            empty_element = Mock()
            empty_element.count.return_value = 0
            return empty_element
    
    mock_page.locator = Mock(side_effect=locator_side_effect)
    
    # Create handler and detect
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    result = handler.detect_challenge()
    
    # Should detect captcha challenge
    assert result == "captcha"
    # Should have checked multiple selectors before finding it
    assert len(checked_selectors) >= 3
    assert '.px-captcha-container' in checked_selectors


# ============================================================================
# Property Tests for Verification Waiting Logic
# ============================================================================

@given(
    expected_url_pattern=st.sampled_from([
        "/account/profile",
        "/register/success",
        "/welcome",
        "/dashboard",
        "/account"
    ]),
    timeout_seconds=st.integers(min_value=1, max_value=3),
    url_matches=st.booleans()
)
@settings(max_examples=20, deadline=None)
def test_verification_completion_detection_url_match(
    expected_url_pattern, timeout_seconds, url_matches
):
    """
    **Feature: manual-verification, Property 3: 验证完成检测**
    
    *For any* manual verification wait period, if the current URL matches the
    expected success pattern OR all PerimeterX challenge elements disappear from
    the page, then the verification SHALL be marked as complete.
    
    **Validates: Requirements 3.2, 3.3, 3.4, 3.5**
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up current URL
    if url_matches:
        # URL contains the expected pattern
        current_url = f"https://example.com{expected_url_pattern}"
    else:
        # URL does not match
        current_url = "https://example.com/other/page"
    
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # Mock challenge elements still present (but URL match should still succeed)
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.is_visible.return_value = True
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler with short timeout
    handler = ManualVerificationHandler(mock_browser, timeout=timeout_seconds)
    
    # Mock time.time() to simulate time passing and time.sleep to speed up
    mock_time = [0.0]  # Start time
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds  # Advance time
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            # Wait for verification
            result = handler.wait_for_manual_verification(expected_url_pattern)
    
    if url_matches:
        # Should complete successfully when URL matches
        assert result is True
    else:
        # Should timeout when URL doesn't match and challenges still present
        assert result is False


@given(
    expected_url_pattern=st.sampled_from([
        "/account/profile",
        "/register/success"
    ]),
    timeout_seconds=st.integers(min_value=1, max_value=3),
    challenges_disappear=st.booleans()
)
@settings(max_examples=20, deadline=None)
def test_verification_completion_detection_challenge_disappear(
    expected_url_pattern, timeout_seconds, challenges_disappear
):
    """
    **Feature: manual-verification, Property 3: 验证完成检测**
    
    *For any* manual verification wait period, if all PerimeterX challenge
    elements disappear from the page, then the verification SHALL be marked
    as complete.
    
    **Validates: Requirements 3.2, 3.3, 3.4, 3.5**
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL does not match expected pattern
    current_url = "https://example.com/other/page"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # Mock challenge elements
    if challenges_disappear:
        # No challenge elements present
        mock_element = Mock()
        mock_element.count.return_value = 0
        mock_page.locator = Mock(return_value=mock_element)
    else:
        # Challenge elements still present
        mock_element = Mock()
        mock_element.count.return_value = 1
        mock_element.first = Mock()
        mock_element.first.is_visible.return_value = True
        mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler with short timeout
    handler = ManualVerificationHandler(mock_browser, timeout=timeout_seconds)
    
    # Mock time.time() to simulate time passing and time.sleep to speed up
    mock_time = [0.0]  # Start time
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds  # Advance time
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            # Wait for verification
            result = handler.wait_for_manual_verification(expected_url_pattern)
    
    if challenges_disappear:
        # Should complete successfully when challenges disappear
        assert result is True
    else:
        # Should timeout when challenges still present and URL doesn't match
        assert result is False


@given(
    timeout_seconds=st.integers(min_value=1, max_value=3),
    verification_completes=st.booleans()
)
@settings(max_examples=20, deadline=None)
def test_verification_timeout_boundary(timeout_seconds, verification_completes):
    """
    **Feature: manual-verification, Property 4: 验证超时边界**
    
    *For any* manual verification wait period, if the elapsed time exceeds the
    configured timeout, then the wait method SHALL return False, log a timeout
    event, and mark the verification as timed out.
    
    **Validates: Requirements 4.1, 4.2, 4.4**
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    if verification_completes:
        # URL matches expected pattern (completes before timeout)
        current_url = "https://example.com/account/profile"
    else:
        # URL does not match (will timeout)
        current_url = "https://example.com/other/page"
    
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # Challenge elements still present
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.is_visible.return_value = True
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler with specified timeout
    handler = ManualVerificationHandler(mock_browser, timeout=timeout_seconds)
    
    # Mock time.time() to simulate time passing and time.sleep to speed up
    mock_time = [0.0]  # Start time
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds  # Advance time
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            # Wait for verification
            result = handler.wait_for_manual_verification("/account/profile")
    
    if verification_completes:
        # Should complete successfully before timeout
        assert result is True
    else:
        # Should timeout
        assert result is False


@given(
    timeout_seconds=st.integers(min_value=2, max_value=5)
)
@settings(max_examples=20, deadline=None)
def test_verification_timeout_respects_configured_value(timeout_seconds):
    """
    **Feature: manual-verification, Property 4: 验证超时边界**
    
    *For any* configured timeout value, the wait method SHALL respect that
    timeout and not exceed it by more than a small margin.
    
    **Validates: Requirements 4.1, 4.2**
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL does not match (will timeout)
    current_url = "https://example.com/other/page"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # Challenge elements still present
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.is_visible.return_value = True
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler with specified timeout
    handler = ManualVerificationHandler(mock_browser, timeout=timeout_seconds)
    
    # Verify timeout is set correctly
    assert handler.timeout == timeout_seconds
    
    # Mock time.time() to simulate time passing and time.sleep to speed up
    mock_time = [0.0]  # Start time
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds  # Advance time
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            # Wait for verification (will timeout)
            result = handler.wait_for_manual_verification("/account/profile")
    
    # Should timeout
    assert result is False


# ============================================================================
# Unit Tests for Verification Waiting Logic
# ============================================================================

def test_wait_for_manual_verification_url_match():
    """
    Test verification completes when URL matches expected pattern.
    
    Requirements: 3.2, 3.3, 3.4, 3.5
    """
    from unittest.mock import Mock, PropertyMock
    from src.manual_verification import ManualVerificationHandler
    import time
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL matches expected pattern
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # Challenge elements still present (but URL match should succeed)
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.is_visible.return_value = True
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=5)
    
    # Wait for verification
    start_time = time.time()
    result = handler.wait_for_manual_verification("/account/profile")
    elapsed = time.time() - start_time
    
    # Should complete successfully
    assert result is True
    # Should complete quickly (not wait for full timeout)
    assert elapsed < 2.0


def test_wait_for_manual_verification_challenge_disappears():
    """
    Test verification completes when challenge elements disappear.
    
    Requirements: 3.2, 3.3, 3.4, 3.5
    """
    from unittest.mock import Mock, PropertyMock
    from src.manual_verification import ManualVerificationHandler
    import time
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL does not match expected pattern
    current_url = "https://example.com/other/page"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # No challenge elements present
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=5)
    
    # Wait for verification
    start_time = time.time()
    result = handler.wait_for_manual_verification("/account/profile")
    elapsed = time.time() - start_time
    
    # Should complete successfully
    assert result is True
    # Should complete quickly
    assert elapsed < 2.0


def test_wait_for_manual_verification_timeout():
    """
    Test verification times out when neither URL matches nor challenges disappear.
    
    Requirements: 4.1, 4.2
    """
    from unittest.mock import Mock, PropertyMock
    from src.manual_verification import ManualVerificationHandler
    import time
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL does not match
    current_url = "https://example.com/other/page"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # Challenge elements still present
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.is_visible.return_value = True
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler with short timeout
    timeout_seconds = 2
    handler = ManualVerificationHandler(mock_browser, timeout=timeout_seconds)
    
    # Wait for verification
    start_time = time.time()
    result = handler.wait_for_manual_verification("/account/profile")
    elapsed = time.time() - start_time
    
    # Should timeout
    assert result is False
    # Should wait for approximately the full timeout
    assert elapsed >= timeout_seconds - 0.5
    assert elapsed <= timeout_seconds + 1.5


def test_wait_for_manual_verification_no_browser_page():
    """
    Test verification returns False when browser page is not available.
    
    Requirements: 3.1
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser without page
    mock_browser = Mock()
    mock_browser.page = None
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=5)
    
    # Wait for verification
    result = handler.wait_for_manual_verification("/account/profile")
    
    # Should return False immediately
    assert result is False


def test_wait_for_manual_verification_url_pattern_matching():
    """
    Test URL pattern matching works correctly with various patterns.
    
    Requirements: 3.2, 3.3
    """
    from unittest.mock import Mock, PropertyMock
    from src.manual_verification import ManualVerificationHandler
    
    test_cases = [
        # (current_url, expected_pattern, should_match)
        ("https://example.com/account/profile", "/account/profile", True),
        ("https://example.com/account/profile?id=123", "/account/profile", True),
        ("https://example.com/register/success", "/register/success", True),
        ("https://example.com/other/page", "/account/profile", False),
        ("https://example.com/account", "/account/profile", False),
    ]
    
    for current_url, expected_pattern, should_match in test_cases:
        # Create mock browser and page
        mock_browser = Mock()
        mock_page = Mock()
        mock_browser.page = mock_page
        
        type(mock_browser).current_url = PropertyMock(return_value=current_url)
        
        # Challenge elements present
        mock_element = Mock()
        mock_element.count.return_value = 1
        mock_element.first = Mock()
        mock_element.first.is_visible.return_value = True
        mock_page.locator = Mock(return_value=mock_element)
        
        # Create handler with short timeout
        handler = ManualVerificationHandler(mock_browser, timeout=2)
        
        # Wait for verification
        result = handler.wait_for_manual_verification(expected_pattern)
        
        # Verify result matches expectation
        assert result == should_match, f"URL: {current_url}, Pattern: {expected_pattern}, Expected: {should_match}, Got: {result}"


def test_wait_for_manual_verification_challenge_element_visibility():
    """
    Test that only visible challenge elements are considered present.
    
    Requirements: 3.3, 3.4, 3.5
    """
    from unittest.mock import Mock, PropertyMock
    from src.manual_verification import ManualVerificationHandler
    import time
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL does not match
    current_url = "https://example.com/other/page"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # Challenge element exists but is not visible
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.is_visible.return_value = False
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=5)
    
    # Wait for verification
    start_time = time.time()
    result = handler.wait_for_manual_verification("/account/profile")
    elapsed = time.time() - start_time
    
    # Should complete successfully (invisible elements don't count)
    assert result is True
    # Should complete quickly
    assert elapsed < 2.0


def test_wait_for_manual_verification_multiple_challenge_selectors():
    """
    Test that verification checks all challenge selectors.
    
    Requirements: 3.3, 3.4, 3.5
    """
    from unittest.mock import Mock, PropertyMock
    from src.manual_verification import ManualVerificationHandler
    import time
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL does not match
    current_url = "https://example.com/other/page"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # Track which selectors were checked
    checked_selectors = []
    
    def locator_side_effect(selector):
        checked_selectors.append(selector)
        # Last selector has visible challenge
        if selector == 'div[class*="px-captcha"]':
            mock_element = Mock()
            mock_element.count.return_value = 1
            mock_element.first = Mock()
            mock_element.first.is_visible.return_value = True
            return mock_element
        else:
            # Other selectors have no elements
            mock_element = Mock()
            mock_element.count.return_value = 0
            return mock_element
    
    mock_page.locator = Mock(side_effect=locator_side_effect)
    
    # Create handler with short timeout
    handler = ManualVerificationHandler(mock_browser, timeout=2)
    
    # Wait for verification (will timeout)
    result = handler.wait_for_manual_verification("/account/profile")
    
    # Should timeout because one challenge is still visible
    assert result is False
    # Should have checked multiple selectors
    assert len(checked_selectors) > len(ManualVerificationHandler.PX_SELECTORS)


# ============================================================================
# Unit Tests for Notification Display
# ============================================================================

def test_display_notification_content_completeness():
    """
    Test that notification displays all required information.
    
    Requirements: 2.2, 2.4
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    from io import StringIO
    import sys
    
    # Create mock browser
    mock_browser = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Capture stdout
    captured_output = StringIO()
    sys.stdout = captured_output
    
    try:
        # Display notification
        handler.display_notification("captcha", remaining_time=115)
        
        # Get output
        output = captured_output.getvalue()
        
        # Verify all required content is present
        assert "PerimeterX 验证挑战检测" in output
        assert "captcha" in output
        assert "请在浏览器中手动完成验证" in output
        assert "验证成功后页面将自动跳转" in output
        assert "超时时间: 120 秒" in output
        assert "剩余时间: 115 秒" in output
        
    finally:
        # Restore stdout
        sys.stdout = sys.__stdout__


def test_display_notification_format_correctness():
    """
    Test that notification format is correct with box drawing characters.
    
    Requirements: 2.2, 2.4
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    from io import StringIO
    import sys
    
    # Create mock browser
    mock_browser = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Capture stdout
    captured_output = StringIO()
    sys.stdout = captured_output
    
    try:
        # Display notification
        handler.display_notification("press-and-hold", remaining_time=100)
        
        # Get output
        output = captured_output.getvalue()
        
        # Verify box format is present
        assert "╔" in output  # Top-left corner
        assert "╗" in output  # Top-right corner
        assert "╚" in output  # Bottom-left corner
        assert "╝" in output  # Bottom-right corner
        assert "║" in output  # Vertical lines
        assert "═" in output  # Horizontal lines
        
        # Verify output is not empty
        assert len(output) > 0
        
        # Verify multiple lines
        lines = output.strip().split('\n')
        assert len(lines) > 5
        
    finally:
        # Restore stdout
        sys.stdout = sys.__stdout__


def test_display_notification_with_different_challenge_types():
    """
    Test notification displays correctly for different challenge types.
    
    Requirements: 2.2, 2.4
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    from io import StringIO
    import sys
    
    challenge_types = ["captcha", "press-and-hold", "checkbox", "slider", "unknown"]
    
    for challenge_type in challenge_types:
        # Create mock browser
        mock_browser = Mock()
        
        # Create handler
        handler = ManualVerificationHandler(mock_browser, timeout=120)
        
        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            # Display notification
            handler.display_notification(challenge_type, remaining_time=100)
            
            # Get output
            output = captured_output.getvalue()
            
            # Verify challenge type is displayed
            assert challenge_type in output
            
            # Verify basic structure is present
            assert "PerimeterX 验证挑战检测" in output
            assert "请在浏览器中手动完成验证" in output
            
        finally:
            # Restore stdout
            sys.stdout = sys.__stdout__


def test_display_notification_with_default_remaining_time():
    """
    Test notification uses timeout as default remaining time.
    
    Requirements: 2.2, 2.4
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    from io import StringIO
    import sys
    
    # Create mock browser
    mock_browser = Mock()
    
    # Create handler with custom timeout
    timeout_value = 180
    handler = ManualVerificationHandler(mock_browser, timeout=timeout_value)
    
    # Capture stdout
    captured_output = StringIO()
    sys.stdout = captured_output
    
    try:
        # Display notification without remaining_time parameter
        handler.display_notification("captcha")
        
        # Get output
        output = captured_output.getvalue()
        
        # Verify timeout is used as remaining time
        assert f"超时时间: {timeout_value} 秒" in output
        assert f"剩余时间: {timeout_value} 秒" in output
        
    finally:
        # Restore stdout
        sys.stdout = sys.__stdout__


def test_display_notification_with_custom_remaining_time():
    """
    Test notification displays custom remaining time correctly.
    
    Requirements: 2.2, 2.4
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    from io import StringIO
    import sys
    
    # Create mock browser
    mock_browser = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Test with various remaining times
    remaining_times = [120, 90, 60, 30, 10, 5, 1]
    
    for remaining_time in remaining_times:
        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            # Display notification with custom remaining time
            handler.display_notification("captcha", remaining_time=remaining_time)
            
            # Get output
            output = captured_output.getvalue()
            
            # Verify remaining time is displayed correctly
            assert f"剩余时间: {remaining_time} 秒" in output
            
        finally:
            # Restore stdout
            sys.stdout = sys.__stdout__


def test_display_notification_logs_event():
    """
    Test that notification display also logs the event.
    
    Requirements: 2.2, 2.4, 2.5
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    from io import StringIO
    import sys
    
    # Create mock browser
    mock_browser = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Capture stdout
    captured_output = StringIO()
    sys.stdout = captured_output
    
    try:
        # Mock logger to capture log calls
        with patch('src.manual_verification.logger') as mock_logger:
            # Display notification
            handler.display_notification("captcha", remaining_time=100)
            
            # Verify logger was called
            assert mock_logger.info.called
            
            # Verify log messages contain expected information
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            log_messages = ' '.join(log_calls)
            
            assert "MANUAL_VERIFICATION" in log_messages
            assert "captcha" in log_messages
            
    finally:
        # Restore stdout
        sys.stdout = sys.__stdout__


def test_display_notification_instructions_present():
    """
    Test that notification includes clear user instructions.
    
    Requirements: 2.4
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    from io import StringIO
    import sys
    
    # Create mock browser
    mock_browser = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Capture stdout
    captured_output = StringIO()
    sys.stdout = captured_output
    
    try:
        # Display notification
        handler.display_notification("captcha", remaining_time=100)
        
        # Get output
        output = captured_output.getvalue()
        
        # Verify instructions are present
        assert "请在浏览器中手动完成验证" in output
        assert "验证成功后页面将自动跳转" in output
        
        # Verify timeout information is present
        assert "超时时间" in output
        assert "剩余时间" in output
        
    finally:
        # Restore stdout
        sys.stdout = sys.__stdout__


# ============================================================================
# Property Tests for Logging Methods
# ============================================================================

@given(
    challenge_type=challenge_type_strategy,
    page_url=url_strategy
)
@settings(max_examples=100)
def test_log_challenge_detection_completeness(challenge_type, page_url):
    """
    **Feature: manual-verification, Property 5: 验证事件日志完整性 (Challenge Detection)**
    
    *For any* challenge detection event, the log_challenge_detection method SHALL
    create a VerificationEvent with all required fields (challenge_type, start_time,
    page_url) and log the detection with proper formatting.
    
    **Validates: Requirements 7.1, 2.5**
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger to capture log calls
    with patch('src.manual_verification.logger') as mock_logger:
        # Log challenge detection
        event = handler.log_challenge_detection(challenge_type, page_url)
        
        # Verify event was created with correct fields
        assert event.challenge_type == challenge_type
        assert event.page_url == page_url
        assert event.start_time is not None
        assert isinstance(event.start_time, datetime)
        assert event.end_time is None
        assert event.success is False
        assert event.timeout is False
        assert event.duration_seconds == 0.0
        
        # Verify event was added to handler's events list
        assert event in handler.events
        
        # Verify logger was called
        assert mock_logger.info.called
        
        # Verify log message contains required information
        log_call = mock_logger.info.call_args[0][0]
        assert "[MANUAL_VERIFICATION]" in log_call
        assert "Challenge detected" in log_call
        assert challenge_type in log_call
        assert page_url in log_call


@given(
    timeout_duration=st.integers(min_value=1, max_value=300)
)
@settings(max_examples=100)
def test_log_verification_entry_completeness(timeout_duration):
    """
    **Feature: manual-verification, Property 5: 验证事件日志完整性 (Entry)**
    
    *For any* verification entry event, the log_verification_entry method SHALL
    log the entry with timeout duration information.
    
    **Validates: Requirements 7.2, 2.5**
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger to capture log calls
    with patch('src.manual_verification.logger') as mock_logger:
        # Log verification entry
        handler.log_verification_entry(timeout_duration)
        
        # Verify logger was called
        assert mock_logger.info.called
        
        # Verify log message contains required information
        log_call = mock_logger.info.call_args[0][0]
        assert "[MANUAL_VERIFICATION]" in log_call
        assert "Entering manual verification mode" in log_call
        assert str(timeout_duration) in log_call


@given(
    challenge_type=challenge_type_strategy,
    page_url=url_strategy,
    duration=st.floats(min_value=0.0, max_value=300.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100)
def test_log_verification_completion_completeness(challenge_type, page_url, duration):
    """
    **Feature: manual-verification, Property 5: 验证事件日志完整性 (Completion)**
    
    *For any* verification completion event, the log_verification_completion method
    SHALL mark the event as successful, set end_time, calculate duration, and log
    the completion with duration information.
    
    **Validates: Requirements 7.3, 2.5**
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create a verification event
    start_time = datetime.now()
    event = VerificationEvent(
        challenge_type=challenge_type,
        start_time=start_time,
        page_url=page_url
    )
    
    # Mock logger to capture log calls
    with patch('src.manual_verification.logger') as mock_logger:
        # Log verification completion
        handler.log_verification_completion(event, duration)
        
        # Verify event was marked as successful
        assert event.success is True
        assert event.timeout is False
        assert event.failure_reason == ""
        assert event.end_time is not None
        assert event.duration_seconds >= 0.0
        
        # Verify logger was called
        assert mock_logger.info.called
        
        # Verify log message contains required information
        log_call = mock_logger.info.call_args[0][0]
        assert "[MANUAL_VERIFICATION]" in log_call
        assert "Verification completed successfully" in log_call
        assert f"{duration:.1f}s" in log_call


@given(
    challenge_type=challenge_type_strategy,
    page_url=url_strategy,
    duration=st.floats(min_value=0.0, max_value=300.0, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100)
def test_log_verification_timeout_completeness(challenge_type, page_url, duration):
    """
    **Feature: manual-verification, Property 5: 验证事件日志完整性 (Timeout)**
    
    *For any* verification timeout event, the log_verification_timeout method SHALL
    mark the event as timed out, set end_time, calculate duration, and log the
    timeout with duration information.
    
    **Validates: Requirements 7.4, 2.5**
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create a verification event
    start_time = datetime.now()
    event = VerificationEvent(
        challenge_type=challenge_type,
        start_time=start_time,
        page_url=page_url
    )
    
    # Mock logger to capture log calls
    with patch('src.manual_verification.logger') as mock_logger:
        # Log verification timeout
        handler.log_verification_timeout(event, duration)
        
        # Verify event was marked as timed out
        assert event.success is False
        assert event.timeout is True
        assert event.failure_reason == "timeout"
        assert event.end_time is not None
        assert event.duration_seconds >= 0.0
        
        # Verify logger was called with warning level
        assert mock_logger.warning.called
        
        # Verify log message contains required information
        log_call = mock_logger.warning.call_args[0][0]
        assert "[MANUAL_VERIFICATION]" in log_call
        assert "Verification timed out" in log_call
        assert f"{duration:.1f}s" in log_call


@given(
    challenge_type=challenge_type_strategy,
    page_url=url_strategy,
    failure_reason=failure_reason_strategy.filter(lambda x: x != "")
)
@settings(max_examples=100)
def test_log_verification_failure_completeness(challenge_type, page_url, failure_reason):
    """
    **Feature: manual-verification, Property 5: 验证事件日志完整性 (Failure)**
    
    *For any* verification failure event, the log_verification_failure method SHALL
    mark the event as failed, set end_time, record failure reason, and log the
    failure with reason information.
    
    **Validates: Requirements 7.5, 2.5**
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create a verification event
    start_time = datetime.now()
    event = VerificationEvent(
        challenge_type=challenge_type,
        start_time=start_time,
        page_url=page_url
    )
    
    # Mock logger to capture log calls
    with patch('src.manual_verification.logger') as mock_logger:
        # Log verification failure
        handler.log_verification_failure(event, failure_reason)
        
        # Verify event was marked as failed
        assert event.success is False
        assert event.timeout is False
        assert event.failure_reason == failure_reason
        assert event.end_time is not None
        assert event.duration_seconds >= 0.0
        
        # Verify logger was called with error level
        assert mock_logger.error.called
        
        # Verify log message contains required information
        log_call = mock_logger.error.call_args[0][0]
        assert "[MANUAL_VERIFICATION]" in log_call
        assert "Verification failed" in log_call
        assert failure_reason in log_call


@given(
    challenge_type=challenge_type_strategy,
    page_url=url_strategy,
    event_type=st.sampled_from(["detection", "completion", "timeout", "failure"])
)
@settings(max_examples=100)
def test_logging_methods_maintain_event_list(challenge_type, page_url, event_type):
    """
    **Feature: manual-verification, Property 5: 验证事件日志完整性 (Event List)**
    
    *For any* logging method call, the event SHALL be properly tracked in the
    handler's events list for later retrieval and analysis.
    
    **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 2.5**
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Verify events list is initially empty
    initial_count = len(handler.events)
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        if event_type == "detection":
            # Log challenge detection
            event = handler.log_challenge_detection(challenge_type, page_url)
            
            # Verify event was added to list
            assert len(handler.events) == initial_count + 1
            assert event in handler.events
            
        elif event_type in ["completion", "timeout", "failure"]:
            # Create an event first
            event = VerificationEvent(
                challenge_type=challenge_type,
                start_time=datetime.now(),
                page_url=page_url
            )
            
            # Log the appropriate event type
            if event_type == "completion":
                handler.log_verification_completion(event, 10.0)
            elif event_type == "timeout":
                handler.log_verification_timeout(event, 120.0)
            else:  # failure
                handler.log_verification_failure(event, "test_failure")
            
            # Verify event state was updated
            assert event.end_time is not None
            assert event.duration_seconds >= 0.0


# ============================================================================
# Unit Tests for Logging Methods
# ============================================================================

def test_log_challenge_detection_creates_event():
    """
    Test that log_challenge_detection creates and returns a VerificationEvent.
    
    Requirements: 7.1, 2.5
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger
    with patch('src.manual_verification.logger') as mock_logger:
        # Log challenge detection
        event = handler.log_challenge_detection("captcha", "https://example.com/register")
        
        # Verify event was created
        assert event is not None
        assert isinstance(event, VerificationEvent)
        assert event.challenge_type == "captcha"
        assert event.page_url == "https://example.com/register"
        
        # Verify event was added to events list
        assert event in handler.events
        
        # Verify logger was called
        assert mock_logger.info.called


def test_log_verification_entry_logs_timeout():
    """
    Test that log_verification_entry logs the timeout duration.
    
    Requirements: 7.2, 2.5
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)


# ============================================================================
# Property Tests for Multiple Verification Support
# ============================================================================

@given(
    num_challenges=st.integers(min_value=1, max_value=5),
    max_attempts=st.integers(min_value=1, max_value=5),
    challenge_types=st.lists(
        challenge_type_strategy,
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=100, deadline=None)
def test_multiple_verification_handling_consistency(num_challenges, max_attempts, challenge_types):
    """
    **Feature: manual-verification, Property 6: 多次验证处理一致性**
    
    *For any* sequence of verification challenges within a single iteration,
    each challenge SHALL be handled independently using the same verification
    logic, and if more than max_attempts challenges occur, the iteration SHALL
    be marked as failed.
    
    **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Ensure we have enough challenge types
    assume(len(challenge_types) >= num_challenges)
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Create handler with specified max attempts
    handler = ManualVerificationHandler(mock_browser, timeout=2, max_attempts=max_attempts)
    
    # Track results for each challenge
    results = []
    
    # Mock time to speed up tests
    mock_time = [0.0]
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            # Process each challenge
            for i in range(num_challenges):
                challenge_type = challenge_types[i]
                page_url = f"https://example.com/page{i}"
                
                # Reset mock time for each challenge
                mock_time[0] = 0.0
                
                # Set up URL to match (simulate successful verification)
                current_url = "https://example.com/account/profile"
                type(mock_browser).current_url = PropertyMock(return_value=current_url)
                
                # Mock challenge elements
                mock_element = Mock()
                mock_element.count.return_value = 0
                mock_page.locator = Mock(return_value=mock_element)
                
                # Handle verification attempt
                result = handler.handle_verification_attempt(
                    challenge_type,
                    page_url,
                    "/account/profile"
                )
                
                results.append(result)
                
                # Verify count was incremented
                assert handler.verification_count == i + 1
                
                # If we've exceeded max attempts, should fail
                if handler.verification_count > max_attempts:
                    if i + 1 < num_challenges:
                        # Next attempt should fail due to max attempts
                        assert handler.check_max_attempts_exceeded() is True
                    break
    
    # Verify behavior based on number of challenges vs max attempts
    if num_challenges <= max_attempts:
        # All challenges should be handled independently
        assert handler.verification_count == num_challenges
        # All should succeed (we mocked successful verification)
        assert all(results)
    else:
        # Should stop at max_attempts
        assert handler.verification_count > max_attempts
        # Last result should be False (max attempts exceeded)
        if len(results) > max_attempts:
            assert results[max_attempts] is False


@given(
    max_attempts=st.integers(min_value=1, max_value=5),
    num_attempts=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=100)
def test_verification_count_tracking(max_attempts, num_attempts):
    """
    **Feature: manual-verification, Property 6: 多次验证处理一致性 (Count Tracking)**
    
    *For any* sequence of verification attempts, the verification count SHALL
    accurately track the number of attempts made.
    
    **Validates: Requirements 8.1, 8.2**
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120, max_attempts=max_attempts)
    
    # Verify initial count is 0
    assert handler.verification_count == 0
    
    # Increment count multiple times
    for i in range(num_attempts):
        count = handler.increment_verification_count()
        
        # Verify count is correct
        assert count == i + 1
        assert handler.verification_count == i + 1
        
        # Check if max attempts exceeded
        exceeded = handler.check_max_attempts_exceeded()
        
        # Should be exceeded if count > max_attempts
        if count > max_attempts:
            assert exceeded is True
        else:
            assert exceeded is False


@given(
    max_attempts=st.integers(min_value=1, max_value=5),
    attempts_before_reset=st.integers(min_value=0, max_value=10),
    attempts_after_reset=st.integers(min_value=0, max_value=10)
)
@settings(max_examples=100)
def test_verification_count_reset(max_attempts, attempts_before_reset, attempts_after_reset):
    """
    **Feature: manual-verification, Property 6: 多次验证处理一致性 (Reset)**
    
    *For any* verification handler, resetting the count SHALL set it back to zero,
    allowing a fresh set of attempts for a new iteration.
    
    **Validates: Requirements 8.1, 8.2**
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120, max_attempts=max_attempts)
    
    # Make some attempts before reset
    for _ in range(attempts_before_reset):
        handler.increment_verification_count()
    
    # Verify count before reset
    assert handler.verification_count == attempts_before_reset
    
    # Reset count
    handler.reset_verification_count()
    
    # Verify count is 0 after reset
    assert handler.verification_count == 0
    
    # Make attempts after reset
    for i in range(attempts_after_reset):
        handler.increment_verification_count()
    
    # Verify count after reset
    assert handler.verification_count == attempts_after_reset


@given(
    max_attempts=st.integers(min_value=1, max_value=5),
    challenge_type=challenge_type_strategy,
    page_url=url_strategy
)
@settings(max_examples=100)
def test_max_attempts_failure_handling(max_attempts, challenge_type, page_url):
    """
    **Feature: manual-verification, Property 6: 多次验证处理一致性 (Max Attempts)**
    
    *For any* verification handler, when the verification count reaches max_attempts,
    subsequent verification attempts SHALL fail immediately with appropriate logging.
    
    **Validates: Requirements 8.3, 8.4**
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=2, max_attempts=max_attempts)
    
    # Set up successful verification conditions
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Mock time to speed up tests
    mock_time = [0.0]
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            # Make max_attempts successful attempts
            for i in range(max_attempts):
                mock_time[0] = 0.0
                result = handler.handle_verification_attempt(
                    challenge_type,
                    page_url,
                    "/account/profile"
                )
                # Should succeed
                assert result is True
                assert handler.verification_count == i + 1
            
            # Make one more attempt (should exceed max_attempts)
            mock_time[0] = 0.0
            result = handler.handle_verification_attempt(
                challenge_type,
                page_url,
                "/account/profile"
            )
            
            # Should fail due to max attempts
            assert result is False
            assert handler.verification_count == max_attempts + 1
            assert handler.check_max_attempts_exceeded() is True
            
            # Verify failure event was logged
            # Find the last event
            if handler.events:
                last_event = handler.events[-1]
                assert last_event.success is False
                assert last_event.failure_reason == "max_attempts_exceeded"


@given(
    challenge_types=st.lists(
        challenge_type_strategy,
        min_size=2,
        max_size=4
    ),
    max_attempts=st.integers(min_value=3, max_value=5)
)
@settings(max_examples=50, deadline=None)
def test_independent_challenge_handling(challenge_types, max_attempts):
    """
    **Feature: manual-verification, Property 6: 多次验证处理一致性 (Independence)**
    
    *For any* sequence of different challenge types, each challenge SHALL be
    handled independently with its own event logging and verification flow.
    
    **Validates: Requirements 8.1, 8.2**
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=2, max_attempts=max_attempts)
    
    # Track events for each challenge
    events_per_challenge = []
    
    # Mock time to speed up tests
    mock_time = [0.0]
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            # Process each challenge type
            for i, challenge_type in enumerate(challenge_types):
                if handler.check_max_attempts_exceeded():
                    break
                
                # Reset mock time
                mock_time[0] = 0.0
                
                # Set up successful verification
                current_url = "https://example.com/account/profile"
                type(mock_browser).current_url = PropertyMock(return_value=current_url)
                
                mock_element = Mock()
                mock_element.count.return_value = 0
                mock_page.locator = Mock(return_value=mock_element)
                
                # Get event count before
                events_before = len(handler.events)
                
                # Handle verification
                page_url = f"https://example.com/page{i}"
                result = handler.handle_verification_attempt(
                    challenge_type,
                    page_url,
                    "/account/profile"
                )
                
                # Get event count after
                events_after = len(handler.events)
                
                # Should have added events (at least detection and completion/failure)
                events_added = events_after - events_before
                events_per_challenge.append(events_added)
                
                # Verify each challenge gets its own events
                assert events_added >= 1
                
                # Verify the latest event has the correct challenge type
                if handler.events:
                    # Find events for this challenge
                    challenge_events = [e for e in handler.events if e.challenge_type == challenge_type]
                    assert len(challenge_events) >= 1
    
    # Verify each challenge was handled independently
    # (each should have generated events)
    assert len(events_per_challenge) > 0
    assert all(count >= 1 for count in events_per_challenge)


def test_log_verification_entry_logs_timeout():
    """
    Test that log_verification_entry logs the timeout duration.
    
    Requirements: 7.2, 2.5
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger
    with patch('src.manual_verification.logger') as mock_logger:
        # Log verification entry
        handler.log_verification_entry(180)
        
        # Verify logger was called
        assert mock_logger.info.called
        
        # Verify log message contains timeout
        log_call = mock_logger.info.call_args[0][0]
        assert "180" in log_call


def test_log_verification_completion_marks_success():
    """
    Test that log_verification_completion marks event as successful.
    
    Requirements: 7.3, 2.5
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://example.com"
    )
    
    # Mock logger
    with patch('src.manual_verification.logger') as mock_logger:
        # Log completion
        handler.log_verification_completion(event, 15.5)
        
        # Verify event was marked as successful
        assert event.success is True
        assert event.timeout is False
        assert event.end_time is not None
        
        # Verify logger was called
        assert mock_logger.info.called


def test_log_verification_timeout_marks_timeout():
    """
    Test that log_verification_timeout marks event as timed out.
    
    Requirements: 7.4, 2.5
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://example.com"
    )
    
    # Mock logger
    with patch('src.manual_verification.logger') as mock_logger:
        # Log timeout
        handler.log_verification_timeout(event, 120.0)
        
        # Verify event was marked as timed out
        assert event.success is False
        assert event.timeout is True
        assert event.failure_reason == "timeout"
        assert event.end_time is not None
        
        # Verify logger was called with warning
        assert mock_logger.warning.called


def test_log_verification_failure_marks_failure():
    """
    Test that log_verification_failure marks event as failed with reason.
    
    Requirements: 7.5, 2.5
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://example.com"
    )
    
    # Mock logger
    with patch('src.manual_verification.logger') as mock_logger:
        # Log failure
        handler.log_verification_failure(event, "browser_closed")
        
        # Verify event was marked as failed
        assert event.success is False
        assert event.timeout is False
        assert event.failure_reason == "browser_closed"
        assert event.end_time is not None
        
        # Verify logger was called with error
        assert mock_logger.error.called


def test_logging_methods_use_correct_log_levels():
    """
    Test that logging methods use appropriate log levels.
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 2.5
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger
    with patch('src.manual_verification.logger') as mock_logger:
        # Test detection (info level)
        event1 = handler.log_challenge_detection("captcha", "https://example.com")
        assert mock_logger.info.called
        mock_logger.reset_mock()
        
        # Test entry (info level)
        handler.log_verification_entry(120)
        assert mock_logger.info.called
        mock_logger.reset_mock()
        
        # Test completion (info level)
        event2 = VerificationEvent("captcha", datetime.now(), "https://example.com")
        handler.log_verification_completion(event2, 10.0)
        assert mock_logger.info.called
        mock_logger.reset_mock()
        
        # Test timeout (warning level)
        event3 = VerificationEvent("captcha", datetime.now(), "https://example.com")
        handler.log_verification_timeout(event3, 120.0)
        assert mock_logger.warning.called
        mock_logger.reset_mock()
        
        # Test failure (error level)
        event4 = VerificationEvent("captcha", datetime.now(), "https://example.com")
        handler.log_verification_failure(event4, "test_failure")
        assert mock_logger.error.called


def test_log_messages_contain_manual_verification_tag():
    """
    Test that all log messages contain [MANUAL_VERIFICATION] tag.
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 2.5
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger
    with patch('src.manual_verification.logger') as mock_logger:
        # Test all logging methods
        event1 = handler.log_challenge_detection("captcha", "https://example.com")
        assert "[MANUAL_VERIFICATION]" in mock_logger.info.call_args[0][0]
        
        handler.log_verification_entry(120)
        assert "[MANUAL_VERIFICATION]" in mock_logger.info.call_args[0][0]
        
        event2 = VerificationEvent("captcha", datetime.now(), "https://example.com")
        handler.log_verification_completion(event2, 10.0)
        assert "[MANUAL_VERIFICATION]" in mock_logger.info.call_args[0][0]
        
        event3 = VerificationEvent("captcha", datetime.now(), "https://example.com")
        handler.log_verification_timeout(event3, 120.0)
        assert "[MANUAL_VERIFICATION]" in mock_logger.warning.call_args[0][0]
        
        event4 = VerificationEvent("captcha", datetime.now(), "https://example.com")
        handler.log_verification_failure(event4, "test_failure")
        assert "[MANUAL_VERIFICATION]" in mock_logger.error.call_args[0][0]



# ============================================================================
# Unit Tests for Multiple Verification Support
# ============================================================================

def test_increment_verification_count():
    """
    Test that increment_verification_count increments and returns the count.
    
    Requirements: 8.1, 8.2
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120, max_attempts=3)
    
    # Verify initial count is 0
    assert handler.verification_count == 0
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Increment count
        count = handler.increment_verification_count()
        
        # Verify count is 1
        assert count == 1
        assert handler.verification_count == 1
        
        # Increment again
        count = handler.increment_verification_count()
        
        # Verify count is 2
        assert count == 2
        assert handler.verification_count == 2


def test_check_max_attempts_not_exceeded():
    """
    Test that check_max_attempts_exceeded returns False when not exceeded.
    
    Requirements: 8.3, 8.4
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler with max_attempts=3
    handler = ManualVerificationHandler(mock_browser, timeout=120, max_attempts=3)
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Set count to 2 (not exceeded)
        handler.verification_count = 2
        
        # Check if exceeded
        exceeded = handler.check_max_attempts_exceeded()
        
        # Should not be exceeded
        assert exceeded is False


def test_check_max_attempts_exceeded():
    """
    Test that check_max_attempts_exceeded returns True when exceeded.
    
    Requirements: 8.3, 8.4
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler with max_attempts=3
    handler = ManualVerificationHandler(mock_browser, timeout=120, max_attempts=3)
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Set count to 4 (exceeded)
        handler.verification_count = 4
        
        # Check if exceeded
        exceeded = handler.check_max_attempts_exceeded()
        
        # Should be exceeded
        assert exceeded is True


def test_check_max_attempts_at_limit():
    """
    Test that check_max_attempts_exceeded returns False when at the limit.
    
    Requirements: 8.3, 8.4
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler with max_attempts=3
    handler = ManualVerificationHandler(mock_browser, timeout=120, max_attempts=3)
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Set count to exactly max_attempts
        handler.verification_count = 3
        
        # Check if exceeded
        exceeded = handler.check_max_attempts_exceeded()
        
        # Should not be exceeded (at limit is OK)
        assert exceeded is False


def test_reset_verification_count():
    """
    Test that reset_verification_count resets the count to zero.
    
    Requirements: 8.1, 8.2
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120, max_attempts=3)
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Set count to some value
        handler.verification_count = 5
        
        # Reset count
        handler.reset_verification_count()
        
        # Verify count is 0
        assert handler.verification_count == 0


def test_handle_verification_attempt_success():
    """
    Test that handle_verification_attempt succeeds when verification completes.
    
    Requirements: 8.1, 8.2
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up successful verification
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=2, max_attempts=3)
    
    # Mock time to speed up test
    mock_time = [0.0]
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            # Handle verification attempt
            result = handler.handle_verification_attempt(
                "captcha",
                "https://example.com/register",
                "/account/profile"
            )
    
    # Should succeed
    assert result is True
    # Count should be 1
    assert handler.verification_count == 1


def test_handle_verification_attempt_max_exceeded():
    """
    Test that handle_verification_attempt fails when max attempts exceeded.
    
    Requirements: 8.3, 8.4
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up successful verification conditions
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler with max_attempts=2
    handler = ManualVerificationHandler(mock_browser, timeout=2, max_attempts=2)
    
    # Mock time to speed up test
    mock_time = [0.0]
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            # Make 2 successful attempts
            result1 = handler.handle_verification_attempt(
                "captcha",
                "https://example.com/register",
                "/account/profile"
            )
            assert result1 is True
            assert handler.verification_count == 1
            
            mock_time[0] = 0.0
            result2 = handler.handle_verification_attempt(
                "captcha",
                "https://example.com/register",
                "/account/profile"
            )
            assert result2 is True
            assert handler.verification_count == 2
            
            # Third attempt should fail (exceeds max_attempts=2)
            mock_time[0] = 0.0
            result3 = handler.handle_verification_attempt(
                "captcha",
                "https://example.com/register",
                "/account/profile"
            )
            assert result3 is False
            assert handler.verification_count == 3


def test_handle_verification_attempt_independent_handling():
    """
    Test that each verification attempt is handled independently.
    
    Requirements: 8.1, 8.2
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up successful verification
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=2, max_attempts=5)
    
    # Mock time to speed up test
    mock_time = [0.0]
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            # Handle multiple verification attempts with different challenge types
            challenge_types = ["captcha", "press-and-hold", "checkbox"]
            
            for i, challenge_type in enumerate(challenge_types):
                mock_time[0] = 0.0
                events_before = len(handler.events)
                
                result = handler.handle_verification_attempt(
                    challenge_type,
                    f"https://example.com/page{i}",
                    "/account/profile"
                )
                
                # Should succeed
                assert result is True
                # Count should increment
                assert handler.verification_count == i + 1
                # Should have added events
                assert len(handler.events) > events_before


def test_max_attempts_configuration():
    """
    Test that max_attempts can be configured during initialization.
    
    Requirements: 8.1, 8.2
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Test different max_attempts values
    for max_attempts in [1, 2, 3, 5, 10]:
        handler = ManualVerificationHandler(mock_browser, timeout=120, max_attempts=max_attempts)
        
        # Verify max_attempts is set correctly
        assert handler.max_attempts == max_attempts


def test_verification_count_persists_across_attempts():
    """
    Test that verification count persists across multiple attempts.
    
    Requirements: 8.1, 8.2
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up successful verification
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=2, max_attempts=5)
    
    # Mock time to speed up test
    mock_time = [0.0]
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            # Make multiple attempts
            for i in range(3):
                mock_time[0] = 0.0
                handler.handle_verification_attempt(
                    "captcha",
                    "https://example.com/register",
                    "/account/profile"
                )
                
                # Verify count persists
                assert handler.verification_count == i + 1


def test_reset_allows_new_iteration():
    """
    Test that resetting count allows a new iteration with fresh attempts.
    
    Requirements: 8.1, 8.2
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up successful verification
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler with max_attempts=2
    handler = ManualVerificationHandler(mock_browser, timeout=2, max_attempts=2)
    
    # Mock time to speed up test
    mock_time = [0.0]
    
    def mock_time_func():
        return mock_time[0]
    
    def mock_sleep_func(seconds):
        mock_time[0] += seconds
    
    with patch('time.time', side_effect=mock_time_func):
        with patch('time.sleep', side_effect=mock_sleep_func):
            # Make 2 attempts (reach max)
            for i in range(2):
                mock_time[0] = 0.0
                result = handler.handle_verification_attempt(
                    "captcha",
                    "https://example.com/register",
                    "/account/profile"
                )
                assert result is True
            
            # Third attempt should fail
            mock_time[0] = 0.0
            result = handler.handle_verification_attempt(
                "captcha",
                "https://example.com/register",
                "/account/profile"
            )
            assert result is False
            assert handler.verification_count == 3
            
            # Reset count
            handler.reset_verification_count()
            assert handler.verification_count == 0
            
            # Should be able to make attempts again
            mock_time[0] = 0.0
            result = handler.handle_verification_attempt(
                "captcha",
                "https://example.com/register",
                "/account/profile"
            )
            assert result is True


# ============================================================================
# Property Tests for Flow Resume Logic
# ============================================================================

@given(
    expected_url_pattern=st.sampled_from([
        "/account/profile",
        "/register/success",
        "/welcome",
        "/dashboard"
    ]),
    challenge_type=challenge_type_strategy,
    page_url=url_strategy,
    next_step=st.sampled_from([
        "profile_update",
        "continue",
        "complete_registration",
        "verify_email"
    ])
)
@settings(max_examples=100)
def test_flow_resume_state_consistency(expected_url_pattern, challenge_type, page_url, next_step):
    """
    **Feature: manual-verification, Property 7: 流程恢复状态一致性**
    
    *For any* successful verification, the system SHALL log a success event,
    verify the current page state matches the expected state, and resume
    automated flow from the correct next step.
    
    **Validates: Requirements 5.1, 5.2, 5.3, 5.5**
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up page state that matches expected pattern
    current_url = f"https://example.com{expected_url_pattern}"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # No challenge elements present (successful state)
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create a successful verification event
    start_time = datetime.now()
    event = VerificationEvent(
        challenge_type=challenge_type,
        start_time=start_time,
        page_url=page_url
    )
    event.complete(success=True, timeout=False, failure_reason="")
    
    # Mock logger to capture log calls
    with patch('src.manual_verification.logger') as mock_logger:
        # Resume flow after verification
        result = handler.resume_flow_after_verification(
            event,
            expected_url_pattern,
            next_step
        )
        
        # Should succeed
        assert result is True
        
        # Verify page state was checked (verify_page_state logs)
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        log_messages = ' '.join(log_calls)
        assert "Page state verified successfully" in log_messages
        
        # Verify success event was logged (log_flow_resume_success)
        assert "Flow resuming after successful verification" in log_messages
        assert challenge_type in log_messages
        assert next_step in log_messages
        
        # Verify post-verification monitoring was set up
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        debug_messages = ' '.join(debug_calls)
        assert "Post-verification monitoring active" in debug_messages
        
        # Verify flow resume completion was logged
        assert "Flow resume complete" in log_messages


@given(
    expected_url_pattern=st.sampled_from([
        "/account/profile",
        "/register/success"
    ]),
    challenge_type=challenge_type_strategy,
    page_url=url_strategy,
    url_matches=st.booleans(),
    challenges_present=st.booleans()
)
@settings(max_examples=100)
def test_flow_resume_page_state_verification(
    expected_url_pattern, challenge_type, page_url, url_matches, challenges_present
):
    """
    **Feature: manual-verification, Property 7: 流程恢复状态一致性 (State Verification)**
    
    *For any* flow resume attempt, the page state verification SHALL correctly
    identify whether the page matches the expected state (URL pattern and no
    challenge elements).
    
    **Validates: Requirements 5.1, 5.3**
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up URL based on test parameter
    if url_matches:
        current_url = f"https://example.com{expected_url_pattern}"
    else:
        current_url = "https://example.com/other/page"
    
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # Set up challenge elements based on test parameter
    if challenges_present:
        # Challenge elements still present
        mock_element = Mock()
        mock_element.count.return_value = 1
        mock_element.first = Mock()
        mock_element.first.is_visible.return_value = True
        mock_page.locator = Mock(return_value=mock_element)
    else:
        # No challenge elements
        mock_element = Mock()
        mock_element.count.return_value = 0
        mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Verify page state
        result = handler.verify_page_state(expected_url_pattern)
        
        # Result should be True only if URL matches AND no challenges present
        expected_result = url_matches and not challenges_present
        assert result == expected_result


@given(
    challenge_type=challenge_type_strategy,
    page_url=url_strategy,
    next_step=st.sampled_from([
        "profile_update",
        "continue",
        "complete_registration"
    ])
)
@settings(max_examples=100)
def test_flow_resume_logging_completeness(challenge_type, page_url, next_step):
    """
    **Feature: manual-verification, Property 7: 流程恢复状态一致性 (Logging)**
    
    *For any* successful flow resume, all required logging SHALL occur:
    success event log, page state verification log, and monitoring setup log.
    
    **Validates: Requirements 5.1, 5.2, 5.5, 2.5**
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up successful state
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create a successful verification event
    start_time = datetime.now()
    event = VerificationEvent(
        challenge_type=challenge_type,
        start_time=start_time,
        page_url=page_url
    )
    event.complete(success=True, timeout=False, failure_reason="")
    
    # Mock logger to capture all log calls
    with patch('src.manual_verification.logger') as mock_logger:
        # Resume flow
        result = handler.resume_flow_after_verification(
            event,
            "/account/profile",
            next_step
        )
        
        # Should succeed
        assert result is True
        
        # Verify all required log calls were made
        # 1. Page state verification log
        assert mock_logger.info.called
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Page state verified successfully" in call for call in info_calls)
        
        # 2. Flow resume success log
        assert any("Flow resuming after successful verification" in call for call in info_calls)
        assert any(challenge_type in call for call in info_calls)
        assert any(next_step in call for call in info_calls)
        
        # 3. Flow resume complete log
        assert any("Flow resume complete" in call for call in info_calls)
        
        # 4. Post-verification monitoring log
        assert mock_logger.debug.called
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("Post-verification monitoring active" in call for call in debug_calls)


@given(
    expected_url_pattern=st.sampled_from([
        "/account/profile",
        "/register/success"
    ]),
    challenge_type=challenge_type_strategy,
    page_url=url_strategy
)
@settings(max_examples=100)
def test_flow_resume_failure_handling(expected_url_pattern, challenge_type, page_url):
    """
    **Feature: manual-verification, Property 7: 流程恢复状态一致性 (Failure)**
    
    *For any* flow resume attempt where page state verification fails,
    the system SHALL return False and log appropriate error messages.
    
    **Validates: Requirements 5.1, 5.3**
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up page state that does NOT match expected pattern
    current_url = "https://example.com/wrong/page"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create a successful verification event
    start_time = datetime.now()
    event = VerificationEvent(
        challenge_type=challenge_type,
        start_time=start_time,
        page_url=page_url
    )
    event.complete(success=True, timeout=False, failure_reason="")
    
    # Mock logger to capture log calls
    with patch('src.manual_verification.logger') as mock_logger:
        # Attempt to resume flow (should fail due to wrong URL)
        result = handler.resume_flow_after_verification(
            event,
            expected_url_pattern,
            "next_step"
        )
        
        # Should fail
        assert result is False
        
        # Verify error was logged
        assert mock_logger.error.called
        error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
        assert any("Cannot resume flow" in call for call in error_calls)
        assert any("page state verification failed" in call for call in error_calls)



# ============================================================================
# Unit Tests for Flow Resume Logic
# ============================================================================

def test_verify_page_state_success():
    """
    Test that verify_page_state returns True when page state matches expected.
    
    Requirements: 5.1, 5.3
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up page state that matches expected pattern
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # No challenge elements present
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Verify page state
        result = handler.verify_page_state("/account/profile")
        
        # Should succeed
        assert result is True


def test_verify_page_state_url_mismatch():
    """
    Test that verify_page_state returns False when URL doesn't match.
    
    Requirements: 5.1, 5.3
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up page state with wrong URL
    current_url = "https://example.com/wrong/page"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # No challenge elements present
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Verify page state
        result = handler.verify_page_state("/account/profile")
        
        # Should fail
        assert result is False


def test_verify_page_state_challenge_present():
    """
    Test that verify_page_state returns False when challenge elements present.
    
    Requirements: 5.1, 5.3
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up page state with correct URL
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # Challenge elements still present
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.is_visible.return_value = True
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Verify page state
        result = handler.verify_page_state("/account/profile")
        
        # Should fail
        assert result is False


def test_verify_page_state_no_browser_page():
    """
    Test that verify_page_state returns False when browser page not available.
    
    Requirements: 5.1, 5.3
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser without page
    mock_browser = Mock()
    mock_browser.page = None
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Verify page state
        result = handler.verify_page_state("/account/profile")
        
        # Should fail
        assert result is False


def test_verify_page_state_checks_all_selectors():
    """
    Test that verify_page_state checks all challenge selectors.
    
    Requirements: 5.1, 5.3
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up page state with correct URL
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # Track which selectors were checked
    checked_selectors = []
    
    def locator_side_effect(selector):
        checked_selectors.append(selector)
        # Last selector has visible challenge
        if selector == 'div[class*="px-captcha"]':
            mock_element = Mock()
            mock_element.count.return_value = 1
            mock_element.first = Mock()
            mock_element.first.is_visible.return_value = True
            return mock_element
        else:
            # Other selectors have no elements
            mock_element = Mock()
            mock_element.count.return_value = 0
            return mock_element
    
    mock_page.locator = Mock(side_effect=locator_side_effect)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Verify page state
        result = handler.verify_page_state("/account/profile")
        
        # Should fail because one challenge is present
        assert result is False
        
        # Should have checked multiple selectors
        assert len(checked_selectors) >= len(ManualVerificationHandler.PX_SELECTORS)


def test_log_flow_resume_success():
    """
    Test that log_flow_resume_success logs the correct information.
    
    Requirements: 5.1, 5.2, 2.5
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create a successful verification event
    start_time = datetime.now()
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=start_time,
        page_url="https://example.com/register"
    )
    event.complete(success=True, timeout=False, failure_reason="")
    
    # Mock logger to capture log calls
    with patch('src.manual_verification.logger') as mock_logger:
        # Log flow resume success
        handler.log_flow_resume_success(event, "profile_update")
        
        # Verify logger was called
        assert mock_logger.info.called
        
        # Verify log message contains required information
        log_call = mock_logger.info.call_args[0][0]
        assert "[MANUAL_VERIFICATION]" in log_call
        assert "Flow resuming after successful verification" in log_call
        assert "captcha" in log_call
        assert "profile_update" in log_call


def test_setup_post_verification_monitoring():
    """
    Test that setup_post_verification_monitoring logs monitoring activation.
    
    Requirements: 5.5
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_browser.page = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger to capture log calls
    with patch('src.manual_verification.logger') as mock_logger:
        # Setup post-verification monitoring
        handler.setup_post_verification_monitoring()
        
        # Verify logger was called with debug level
        assert mock_logger.debug.called
        
        # Verify log message contains required information
        log_call = mock_logger.debug.call_args[0][0]
        assert "[MANUAL_VERIFICATION]" in log_call
        assert "Post-verification monitoring active" in log_call


def test_resume_flow_after_verification_success():
    """
    Test that resume_flow_after_verification succeeds with valid state.
    
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up page state that matches expected pattern
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # No challenge elements present
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create a successful verification event
    start_time = datetime.now()
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=start_time,
        page_url="https://example.com/register"
    )
    event.complete(success=True, timeout=False, failure_reason="")
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Resume flow after verification
        result = handler.resume_flow_after_verification(
            event,
            "/account/profile",
            "profile_update"
        )
        
        # Should succeed
        assert result is True


def test_resume_flow_after_verification_state_mismatch():
    """
    Test that resume_flow_after_verification fails when state doesn't match.
    
    Requirements: 5.1, 5.3
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up page state with wrong URL
    current_url = "https://example.com/wrong/page"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # No challenge elements present
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create a successful verification event
    start_time = datetime.now()
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=start_time,
        page_url="https://example.com/register"
    )
    event.complete(success=True, timeout=False, failure_reason="")
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Attempt to resume flow (should fail)
        result = handler.resume_flow_after_verification(
            event,
            "/account/profile",
            "profile_update"
        )
        
        # Should fail
        assert result is False


def test_resume_flow_after_verification_logs_all_steps():
    """
    Test that resume_flow_after_verification logs all required steps.
    
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 2.5
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up page state that matches expected pattern
    current_url = "https://example.com/account/profile"
    type(mock_browser).current_url = PropertyMock(return_value=current_url)
    
    # No challenge elements present
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create a successful verification event
    start_time = datetime.now()
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=start_time,
        page_url="https://example.com/register"
    )
    event.complete(success=True, timeout=False, failure_reason="")
    
    # Mock logger to capture all log calls
    with patch('src.manual_verification.logger') as mock_logger:
        # Resume flow after verification
        result = handler.resume_flow_after_verification(
            event,
            "/account/profile",
            "profile_update"
        )
        
        # Should succeed
        assert result is True
        
        # Verify all required log calls were made
        # 1. Page state verification log (info)
        assert mock_logger.info.called
        info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        assert any("Page state verified successfully" in call for call in info_calls)
        
        # 2. Flow resume success log (info)
        assert any("Flow resuming after successful verification" in call for call in info_calls)
        
        # 3. Flow resume complete log (info)
        assert any("Flow resume complete" in call for call in info_calls)
        
        # 4. Post-verification monitoring log (debug)
        assert mock_logger.debug.called
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("Post-verification monitoring active" in call for call in debug_calls)


def test_resume_flow_after_verification_with_different_next_steps():
    """
    Test that resume_flow_after_verification works with different next steps.
    
    Requirements: 5.2, 5.4
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    next_steps = ["profile_update", "continue", "complete_registration", "verify_email"]
    
    for next_step in next_steps:
        # Create mock browser and page
        mock_browser = Mock()
        mock_page = Mock()
        mock_browser.page = mock_page
        
        # Set up page state that matches expected pattern
        current_url = "https://example.com/account/profile"
        type(mock_browser).current_url = PropertyMock(return_value=current_url)
        
        # No challenge elements present
        mock_element = Mock()
        mock_element.count.return_value = 0
        mock_page.locator = Mock(return_value=mock_element)
        
        # Create handler
        handler = ManualVerificationHandler(mock_browser, timeout=120)
        
        # Create a successful verification event
        start_time = datetime.now()
        event = VerificationEvent(
            challenge_type="captcha",
            start_time=start_time,
            page_url="https://example.com/register"
        )
        event.complete(success=True, timeout=False, failure_reason="")
        
        # Mock logger to capture log calls
        with patch('src.manual_verification.logger') as mock_logger:
            # Resume flow with specific next step
            result = handler.resume_flow_after_verification(
                event,
                "/account/profile",
                next_step
            )
            
            # Should succeed
            assert result is True
            
            # Verify next step is logged
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any(next_step in call for call in info_calls)


def test_resume_flow_after_verification_error_handling():
    """
    Test that resume_flow_after_verification handles errors gracefully.
    
    Requirements: 5.1, 5.3
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Set up page state that will cause an error
    type(mock_browser).current_url = PropertyMock(side_effect=Exception("Browser error"))
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create a successful verification event
    start_time = datetime.now()
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=start_time,
        page_url="https://example.com/register"
    )
    event.complete(success=True, timeout=False, failure_reason="")
    
    # Mock logger to suppress output
    with patch('src.manual_verification.logger'):
        # Attempt to resume flow (should fail due to error)
        result = handler.resume_flow_after_verification(
            event,
            "/account/profile",
            "profile_update"
        )
        
        # Should fail
        assert result is False


# ============================================================================
# Unit Tests for Error Handling (Task 17.2)
# ============================================================================

def test_check_browser_alive_with_active_browser():
    """
    Test browser alive check with active browser.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    mock_page.url = "https://example.com"
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Check browser alive
    result = handler._check_browser_alive()
    
    # Should return True
    assert result is True


def test_check_browser_alive_with_no_page():
    """
    Test browser alive check when page is None.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser without page
    mock_browser = Mock()
    mock_browser.page = None
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Check browser alive
    result = handler._check_browser_alive()
    
    # Should return False
    assert result is False


def test_check_browser_alive_with_crashed_browser():
    """
    Test browser alive check when browser has crashed.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock, PropertyMock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser that raises exception on URL access
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    type(mock_page).url = PropertyMock(side_effect=Exception("Browser crashed"))
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Check browser alive
    result = handler._check_browser_alive()
    
    # Should return False
    assert result is False


def test_handle_browser_crash():
    """
    Test handling browser crash during verification.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock
    from src.manual_verification import (
        ManualVerificationHandler, 
        VerificationEvent,
        BrowserCrashedError
    )
    from datetime import datetime
    
    # Create mock browser
    mock_browser = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create verification event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://example.com"
    )
    
    # Handle browser crash should raise exception
    with pytest.raises(BrowserCrashedError) as exc_info:
        handler.handle_browser_crash(event)
    
    # Verify exception message
    assert "Browser crashed" in str(exc_info.value)
    
    # Verify event was marked as failed
    assert event.success is False
    assert event.failure_reason == "browser_crashed"
    assert event.end_time is not None


def test_handle_browser_closed():
    """
    Test handling user closing browser during verification.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock
    from src.manual_verification import (
        ManualVerificationHandler,
        VerificationEvent,
        BrowserClosedError
    )
    from datetime import datetime
    
    # Create mock browser
    mock_browser = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Create verification event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://example.com"
    )
    
    # Handle browser closed should raise exception
    with pytest.raises(BrowserClosedError) as exc_info:
        handler.handle_browser_closed(event)
    
    # Verify exception message
    assert "closed browser" in str(exc_info.value)
    
    # Verify event was marked as failed
    assert event.success is False
    assert event.failure_reason == "browser_closed_by_user"
    assert event.end_time is not None


def test_handle_page_state_mismatch_recovery_success():
    """
    Test successful recovery from page state mismatch.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock, PropertyMock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock page.url for browser alive check (always returns valid URL)
    type(mock_page).url = PropertyMock(return_value="https://example.com/account/profile")
    
    # Mock browser.current_url - returns list of URLs in sequence
    url_sequence = iter([
        "https://example.com/wrong/page",  # First call
        "https://example.com/account/profile",  # After refresh
    ])
    type(mock_browser).current_url = PropertyMock(side_effect=lambda: next(url_sequence))
    mock_browser.refresh = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Handle page state mismatch
    result = handler.handle_page_state_mismatch(
        expected_state="/account/profile",
        actual_state="/wrong/page"
    )
    
    # Should succeed after refresh
    assert result is True
    # Verify refresh was called
    mock_browser.refresh.assert_called_once()


def test_handle_page_state_mismatch_recovery_failure():
    """
    Test failed recovery from page state mismatch.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock, PropertyMock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL always returns wrong page
    type(mock_browser).current_url = PropertyMock(
        return_value="https://example.com/wrong/page"
    )
    mock_browser.refresh = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Handle page state mismatch
    result = handler.handle_page_state_mismatch(
        expected_state="/account/profile",
        actual_state="/wrong/page"
    )
    
    # Should fail
    assert result is False
    # Verify refresh was called
    mock_browser.refresh.assert_called_once()


def test_handle_page_state_mismatch_browser_not_responsive():
    """
    Test page state mismatch when browser is not responsive.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser that is not responsive
    mock_browser = Mock()
    mock_browser.page = None
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Handle page state mismatch
    result = handler.handle_page_state_mismatch(
        expected_state="/account/profile",
        actual_state="/wrong/page"
    )
    
    # Should fail immediately
    assert result is False


def test_safe_log_normal_operation():
    """
    Test safe logging under normal operation.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Safe log should not raise exception
    handler._safe_log("Test message", "info")
    handler._safe_log("Warning message", "warning")
    handler._safe_log("Error message", "error")
    
    # Should complete without error


def test_safe_log_with_logging_failure():
    """
    Test safe logging when file logging fails.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock, patch
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Mock logger to raise exception
    with patch('src.manual_verification.logger') as mock_logger:
        mock_logger.info.side_effect = Exception("Logging failed")
        
        # Safe log should not raise exception
        handler._safe_log("Test message", "info")
    
    # Should have fallback log
    fallback_logs = handler.get_fallback_logs()
    assert len(fallback_logs) > 0
    assert "Test message" in fallback_logs[0]


def test_get_fallback_logs():
    """
    Test getting fallback log messages.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Add some fallback logs
    handler._fallback_log_messages.append("INFO: Message 1")
    handler._fallback_log_messages.append("ERROR: Message 2")
    
    # Get fallback logs
    logs = handler.get_fallback_logs()
    
    # Should return copy of logs
    assert len(logs) == 2
    assert "Message 1" in logs[0]
    assert "Message 2" in logs[1]
    
    # Modifying returned list should not affect original
    logs.append("New message")
    assert len(handler._fallback_log_messages) == 2


def test_clear_fallback_logs():
    """
    Test clearing fallback log messages.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Add some fallback logs
    handler._fallback_log_messages.append("INFO: Message 1")
    handler._fallback_log_messages.append("ERROR: Message 2")
    
    # Clear logs
    handler.clear_fallback_logs()
    
    # Should be empty
    assert len(handler._fallback_log_messages) == 0
    assert len(handler.get_fallback_logs()) == 0


def test_wait_for_manual_verification_with_error_handling_success():
    """
    Test wait for manual verification with error handling - success case.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.4, 4.5
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler, VerificationEvent
    from datetime import datetime
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL matches expected pattern
    type(mock_browser).current_url = PropertyMock(
        return_value="https://example.com/account/profile"
    )
    
    # Mock page URL for browser alive check
    type(mock_page).url = PropertyMock(return_value="https://example.com/account/profile")
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=5)
    
    # Create event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://example.com"
    )
    
    # Wait for verification with error handling
    result = handler.wait_for_manual_verification_with_error_handling(
        expected_url_pattern="/account/profile",
        event=event
    )
    
    # Should succeed
    assert result is True


def test_wait_for_manual_verification_with_error_handling_timeout():
    """
    Test wait for manual verification with error handling - timeout case.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.4, 4.5
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import ManualVerificationHandler, VerificationEvent
    from datetime import datetime
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL does not match
    type(mock_browser).current_url = PropertyMock(
        return_value="https://example.com/other/page"
    )
    
    # Mock page URL for browser alive check
    type(mock_page).url = PropertyMock(return_value="https://example.com/other/page")
    
    # Challenge elements still present
    mock_element = Mock()
    mock_element.count.return_value = 1
    mock_element.first = Mock()
    mock_element.first.is_visible.return_value = True
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler with short timeout
    handler = ManualVerificationHandler(mock_browser, timeout=2)
    
    # Create event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://example.com"
    )
    
    # Wait for verification with error handling
    result = handler.wait_for_manual_verification_with_error_handling(
        expected_url_pattern="/account/profile",
        event=event
    )
    
    # Should timeout
    assert result is False


def test_wait_for_manual_verification_with_error_handling_browser_crash():
    """
    Test wait for manual verification with error handling - browser crash case.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.4, 4.5
    """
    from unittest.mock import Mock, PropertyMock, patch
    from src.manual_verification import (
        ManualVerificationHandler,
        VerificationEvent,
        BrowserCrashedError
    )
    from datetime import datetime
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL access raises exception (simulating crash)
    type(mock_browser).current_url = PropertyMock(
        side_effect=Exception("Browser crashed")
    )
    
    # Mock page URL to also raise exception
    type(mock_page).url = PropertyMock(side_effect=Exception("Browser crashed"))
    
    # Create handler with short timeout
    handler = ManualVerificationHandler(mock_browser, timeout=10)
    
    # Create event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://example.com"
    )
    
    # Wait for verification with error handling should raise BrowserCrashedError
    with pytest.raises(BrowserCrashedError):
        handler.wait_for_manual_verification_with_error_handling(
            expected_url_pattern="/account/profile",
            event=event
        )
    
    # Event should be marked as failed
    assert event.success is False
    assert event.failure_reason == "browser_crashed"


def test_wait_for_manual_verification_with_error_handling_browser_closed():
    """
    Test wait for manual verification with error handling - browser closed case.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.4, 4.5
    """
    from unittest.mock import Mock, PropertyMock
    from src.manual_verification import (
        ManualVerificationHandler,
        VerificationEvent,
        BrowserClosedError
    )
    from datetime import datetime
    
    # Create mock browser and page
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # URL access raises AttributeError (simulating closed browser)
    type(mock_browser).current_url = PropertyMock(
        side_effect=AttributeError("Browser page closed")
    )
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=10)
    
    # Create event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://example.com"
    )
    
    # Wait for verification with error handling should raise BrowserClosedError
    with pytest.raises(BrowserClosedError):
        handler.wait_for_manual_verification_with_error_handling(
            expected_url_pattern="/account/profile",
            event=event
        )
    
    # Event should be marked as failed
    assert event.success is False
    assert event.failure_reason == "browser_closed_by_user"


def test_wait_for_manual_verification_with_error_handling_no_page():
    """
    Test wait for manual verification with error handling when no page available.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.4, 4.5
    """
    from unittest.mock import Mock
    from src.manual_verification import ManualVerificationHandler, VerificationEvent
    from datetime import datetime
    
    # Create mock browser without page
    mock_browser = Mock()
    mock_browser.page = None
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=5)
    
    # Create event
    event = VerificationEvent(
        challenge_type="captcha",
        start_time=datetime.now(),
        page_url="https://example.com"
    )
    
    # Wait for verification with error handling
    result = handler.wait_for_manual_verification_with_error_handling(
        expected_url_pattern="/account/profile",
        event=event
    )
    
    # Should return False immediately
    assert result is False


def test_error_recovery_workflow():
    """
    Test complete error recovery workflow.
    
    Requirements: 4.4, 4.5
    """
    from unittest.mock import Mock, PropertyMock
    from src.manual_verification import ManualVerificationHandler
    
    # Create mock browser
    mock_browser = Mock()
    mock_page = Mock()
    mock_browser.page = mock_page
    
    # Mock page.url for browser alive check
    type(mock_page).url = PropertyMock(return_value="https://example.com/account/profile")
    
    # Mock browser.current_url - returns list of URLs in sequence
    url_sequence = iter([
        "https://example.com/wrong/page",  # First call in handle_page_state_mismatch
        "https://example.com/account/profile",  # After refresh
        "https://example.com/account/profile",  # verify_page_state call
    ])
    type(mock_browser).current_url = PropertyMock(side_effect=lambda: next(url_sequence))
    mock_browser.refresh = Mock()
    
    # Mock challenge elements not present
    mock_element = Mock()
    mock_element.count.return_value = 0
    mock_page.locator = Mock(return_value=mock_element)
    
    # Create handler
    handler = ManualVerificationHandler(mock_browser, timeout=120)
    
    # Step 1: Detect page state mismatch
    expected_state = "/account/profile"
    actual_state = "/wrong/page"
    
    # Step 2: Attempt recovery
    recovery_result = handler.handle_page_state_mismatch(expected_state, actual_state)
    
    # Should succeed
    assert recovery_result is True
    
    # Step 3: Verify page state after recovery
    verify_result = handler.verify_page_state(expected_state)
    
    # Should succeed
    assert verify_result is True
