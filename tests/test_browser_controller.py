"""
Property-based tests for browser controller module.

Uses hypothesis library for property-based testing.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from hypothesis import given, strategies as st, settings

from src.browser_controller import (
    build_dynamic_id_selector,
    matches_dynamic_id_pattern,
    is_valid_month,
    VALID_MONTHS,
    BrowserController
)


# Strategy for generating 12-character alphanumeric suffixes
alphanumeric_suffix_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters=''),
    min_size=12,
    max_size=12
).filter(lambda x: x.isalnum() and len(x) == 12)


# Strategy for base patterns used in Ralph Lauren forms
base_pattern_strategy = st.sampled_from([
    "dwfrm_profile_login_password_",
    "dwfrm_profile_login_passwordconfirm_"
])


@given(
    base_pattern=base_pattern_strategy,
    suffix=alphanumeric_suffix_strategy
)
@settings(max_examples=100)
def test_dynamic_id_selector_matching(base_pattern, suffix):
    """
    **Feature: ralph-lauren-auto-register, Property 5: 动态ID选择器匹配**
    
    *For any* 12-character alphanumeric suffix, the password field selector 
    SHALL correctly match elements with id pattern "dwfrm_profile_login_password_{suffix}".
    
    **Validates: Requirements 4.3, 4.4**
    """
    # Construct the full element ID
    element_id = f"{base_pattern}{suffix}"
    
    # Build the CSS selector
    selector = build_dynamic_id_selector(base_pattern)
    
    # Verify the selector format is correct (starts with attribute selector)
    assert selector.startswith('[id^="'), f"Selector should use attribute prefix match"
    assert base_pattern in selector, f"Selector should contain base pattern"
    
    # Verify the matches_dynamic_id_pattern function correctly identifies the ID
    assert matches_dynamic_id_pattern(element_id, base_pattern) is True, \
        f"Element ID '{element_id}' should match pattern '{base_pattern}'"


@given(
    base_pattern=base_pattern_strategy,
    wrong_suffix=st.text(min_size=1, max_size=20).filter(
        lambda x: len(x) != 12 or not x.isalnum()
    )
)
@settings(max_examples=100)
def test_dynamic_id_selector_rejects_invalid_suffix(base_pattern, wrong_suffix):
    """
    **Feature: ralph-lauren-auto-register, Property 5: 动态ID选择器匹配 (negative case)**
    
    *For any* suffix that is NOT exactly 12 alphanumeric characters,
    the matches_dynamic_id_pattern function SHALL return False.
    
    **Validates: Requirements 4.3, 4.4**
    """
    # Construct an element ID with invalid suffix
    element_id = f"{base_pattern}{wrong_suffix}"
    
    # Verify the function rejects invalid suffixes
    assert matches_dynamic_id_pattern(element_id, base_pattern) is False, \
        f"Element ID '{element_id}' with invalid suffix should not match"


@given(month=st.sampled_from(VALID_MONTHS))
@settings(max_examples=100)
def test_valid_month_names_accepted(month):
    """
    **Feature: ralph-lauren-auto-register, Property 6: 月份名称有效性**
    
    *For any* month value from the valid set of English month names, 
    the profile update module SHALL accept it as valid input.
    
    **Validates: Requirements 5.1**
    """
    assert is_valid_month(month) is True, \
        f"Month '{month}' should be recognized as valid"


@given(invalid_month=st.text(min_size=1, max_size=20).filter(
    lambda x: x not in VALID_MONTHS
))
@settings(max_examples=100)
def test_invalid_month_names_rejected(invalid_month):
    """
    **Feature: ralph-lauren-auto-register, Property 6: 月份名称有效性 (negative case)**
    
    *For any* string that is NOT a valid English month name,
    the is_valid_month function SHALL return False.
    
    **Validates: Requirements 5.1**
    """
    assert is_valid_month(invalid_month) is False, \
        f"Invalid month '{invalid_month}' should be rejected"



# ============================================================================
# Unit Tests for New BrowserController Methods (Task 7.2)
# ============================================================================

class TestWaitForUrlChange:
    """Unit tests for wait_for_url_change method.
    
    Requirements: 3.1, 3.2, 3.3
    """
    
    def test_wait_for_url_change_detects_navigation(self):
        """Test that wait_for_url_change detects when URL changes."""
        # Create a mock browser controller
        controller = BrowserController()
        controller._page = Mock()
        
        # Simulate URL change: first call returns old URL, second returns new URL
        controller._page.url = "https://example.com/old"
        
        def url_side_effect():
            # After first check, change the URL
            if not hasattr(url_side_effect, 'called'):
                url_side_effect.called = True
                return "https://example.com/old"
            return "https://example.com/new"
        
        type(controller._page).url = property(lambda self: url_side_effect())
        
        # Wait for URL change with short timeout
        new_url = controller.wait_for_url_change(timeout=5000)
        
        # Verify new URL is returned
        assert new_url == "https://example.com/new"
    
    def test_wait_for_url_change_timeout(self):
        """Test that wait_for_url_change raises TimeoutError when URL doesn't change."""
        controller = BrowserController()
        controller._page = Mock()
        controller._page.url = "https://example.com/same"
        
        # Should raise TimeoutError after timeout
        with pytest.raises(TimeoutError) as exc_info:
            controller.wait_for_url_change(timeout=1000)  # 1 second timeout
        
        assert "URL did not change" in str(exc_info.value)
    
    def test_wait_for_url_change_browser_not_started(self):
        """Test that wait_for_url_change raises RuntimeError when browser not started."""
        controller = BrowserController()
        controller._page = None
        
        with pytest.raises(RuntimeError) as exc_info:
            controller.wait_for_url_change()
        
        assert "Browser not started" in str(exc_info.value)


class TestIsChallengePresent:
    """Unit tests for is_challenge_present method.
    
    Requirements: 3.1, 3.2, 3.3
    """
    
    def test_is_challenge_present_detects_visible_element(self):
        """Test that is_challenge_present returns True when challenge element is visible."""
        controller = BrowserController()
        controller._page = Mock()
        
        # Mock locator that finds a visible element
        mock_locator = Mock()
        mock_locator.count.return_value = 1
        mock_locator.first.is_visible.return_value = True
        
        controller._page.locator.return_value = mock_locator
        
        selectors = ['#px-captcha', '.challenge-container']
        result = controller.is_challenge_present(selectors)
        
        assert result is True
        controller._page.locator.assert_called()
    
    def test_is_challenge_present_returns_false_when_no_elements(self):
        """Test that is_challenge_present returns False when no challenge elements found."""
        controller = BrowserController()
        controller._page = Mock()
        
        # Mock locator that finds no elements
        mock_locator = Mock()
        mock_locator.count.return_value = 0
        
        controller._page.locator.return_value = mock_locator
        
        selectors = ['#px-captcha', '.challenge-container']
        result = controller.is_challenge_present(selectors)
        
        assert result is False
    
    def test_is_challenge_present_returns_false_when_element_not_visible(self):
        """Test that is_challenge_present returns False when element exists but not visible."""
        controller = BrowserController()
        controller._page = Mock()
        
        # Mock locator that finds element but it's not visible
        mock_locator = Mock()
        mock_locator.count.return_value = 1
        mock_locator.first.is_visible.return_value = False
        
        controller._page.locator.return_value = mock_locator
        
        selectors = ['#px-captcha']
        result = controller.is_challenge_present(selectors)
        
        assert result is False
    
    def test_is_challenge_present_handles_exceptions_gracefully(self):
        """Test that is_challenge_present handles exceptions and continues checking."""
        controller = BrowserController()
        controller._page = Mock()
        
        # First selector raises exception, second selector finds visible element
        def locator_side_effect(selector):
            if selector == '#invalid-selector':
                raise Exception("Invalid selector")
            else:
                mock_locator = Mock()
                mock_locator.count.return_value = 1
                mock_locator.first.is_visible.return_value = True
                return mock_locator
        
        controller._page.locator.side_effect = locator_side_effect
        
        selectors = ['#invalid-selector', '#px-captcha']
        result = controller.is_challenge_present(selectors)
        
        # Should still find the second selector
        assert result is True
    
    def test_is_challenge_present_browser_not_started(self):
        """Test that is_challenge_present raises RuntimeError when browser not started."""
        controller = BrowserController()
        controller._page = None
        
        with pytest.raises(RuntimeError) as exc_info:
            controller.is_challenge_present(['#px-captcha'])
        
        assert "Browser not started" in str(exc_info.value)
    
    def test_is_challenge_present_checks_multiple_selectors(self):
        """Test that is_challenge_present checks all selectors until one is found."""
        controller = BrowserController()
        controller._page = Mock()
        
        call_count = 0
        
        def locator_side_effect(selector):
            nonlocal call_count
            call_count += 1
            mock_locator = Mock()
            
            # First two selectors return no elements, third one returns visible element
            if call_count < 3:
                mock_locator.count.return_value = 0
            else:
                mock_locator.count.return_value = 1
                mock_locator.first.is_visible.return_value = True
            
            return mock_locator
        
        controller._page.locator.side_effect = locator_side_effect
        
        selectors = ['#selector1', '#selector2', '#selector3', '#selector4']
        result = controller.is_challenge_present(selectors)
        
        # Should find element on third selector and return True
        assert result is True
        assert call_count == 3  # Should stop after finding the first match
