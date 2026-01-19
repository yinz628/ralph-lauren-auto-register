"""
Browser Controller module for Ralph Lauren Auto Register System.

Handles Playwright browser automation with proxy configuration and
PerimeterX bypass settings.
"""

import re
import random
import time
from typing import Optional, Callable, Any, List
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Response


# Valid English month names for profile update
VALID_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def is_valid_month(month: str) -> bool:
    """Check if a month name is valid.
    
    Args:
        month: Month name to validate
        
    Returns:
        True if the month is a valid English month name
    """
    return month in VALID_MONTHS


def build_dynamic_id_selector(base_pattern: str, suffix_length: int = 12) -> str:
    """Build a CSS selector for elements with dynamic ID suffixes.
    
    Args:
        base_pattern: The base ID pattern (e.g., "dwfrm_profile_login_password_")
        suffix_length: Expected length of the random suffix (default 12)
        
    Returns:
        CSS selector that matches the pattern with any alphanumeric suffix
    """
    return f'[id^="{base_pattern}"]'


def matches_dynamic_id_pattern(element_id: str, base_pattern: str) -> bool:
    """Check if an element ID matches a dynamic ID pattern.
    
    Args:
        element_id: The actual element ID to check
        base_pattern: The base pattern (e.g., "dwfrm_profile_login_password_")
        
    Returns:
        True if the element ID matches the pattern with a 12-digit suffix
    """
    if not element_id.startswith(base_pattern):
        return False
    
    suffix = element_id[len(base_pattern):]
    # Check if suffix is exactly 12 alphanumeric characters
    return len(suffix) == 12 and suffix.isalnum()


class BrowserController:
    """Controls Playwright browser with proxy and stealth configuration.
    
    Provides methods for browser automation including navigation,
    element interaction, and request monitoring.
    """
    
    PAGE_LOAD_TIMEOUT = 60000  # 60 seconds
    ELEMENT_TIMEOUT = 30000   # 30 seconds
    
    def __init__(self, proxy_url: Optional[str] = None):
        """Initialize BrowserController.
        
        Args:
            proxy_url: Optional proxy URL to use for browser connections
        """
        self.proxy_url = proxy_url
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._monitored_urls: List[str] = []
        self._captured_responses: List[Response] = []
    
    def _configure_stealth(self, context: BrowserContext) -> None:
        """Configure stealth settings to evade PerimeterX detection.
        
        Applies various techniques to make the browser appear more human-like
        and avoid bot detection.
        
        Args:
            context: The browser context to configure
            
        Requirements: 3.1
        """
        # Load external stealth script if available
        import os
        stealth_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'stealth.min.js')
        if os.path.exists(stealth_file):
            with open(stealth_file, 'r', encoding='utf-8') as f:
                stealth_script = f.read()
            context.add_init_script(stealth_script)
        
        # Add additional init script to bypass PerimeterX detection
        context.add_init_script("""
            // ========== Core WebDriver Detection Bypass (Based on PX init1.js analysis) ==========
            // Delete webdriver property completely
            try { delete Object.getPrototypeOf(navigator).webdriver; } catch(e) {}
            
            // Override webdriver with undefined
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });
            
            // ========== Remove All Automation Indicators (from PX Ba array) ==========
            const automationProps = [
                '__driver_evaluate', '__webdriver_evaluate', '__selenium_evaluate',
                '__fxdriver_evaluate', '__driver_unwrapped', '__webdriver_unwrapped',
                '__selenium_unwrapped', '__fxdriver_unwrapped', '_Selenium_IDE_Recorder',
                '_selenium', 'calledSelenium', '$cdc_asdjflasutopfhvcZLmcfl_',
                '$chrome_asyncScriptInfo', '__$webdriverAsyncExecutor', 'webdriver',
                '__webdriverFunc', 'domAutomation', 'domAutomationController',
                '__lastWatirAlert', '__lastWatirConfirm', '__lastWatirPrompt',
                '__webdriver_script_fn', '_WEBDRIVER_ELEM_CACHE'
            ];
            
            automationProps.forEach(prop => {
                try { delete window[prop]; } catch(e) {}
                try { delete document[prop]; } catch(e) {}
                try {
                    Object.defineProperty(window, prop, {
                        get: () => undefined,
                        configurable: true
                    });
                } catch(e) {}
            });
            
            // ========== Block Automation Event Listeners (from PX ka array) ==========
            const blockedEvents = [
                'driver-evaluate', 'webdriver-evaluate', 'selenium-evaluate',
                'webdriverCommand', 'webdriver-evaluate-response'
            ];
            
            const originalAddEventListener = document.addEventListener;
            document.addEventListener = function(type, listener, options) {
                if (blockedEvents.includes(type)) {
                    return; // Block these events
                }
                return originalAddEventListener.call(this, type, listener, options);
            };
            
            // ========== Clean iframe attributes (from PX Oa array) ==========
            const cleanIframeAttributes = () => {
                document.querySelectorAll('iframe, frame').forEach(frame => {
                    try {
                        frame.removeAttribute('webdriver');
                        frame.removeAttribute('cd_frame_id_');
                    } catch(e) {}
                });
            };
            
            // Run on DOM ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', cleanIframeAttributes);
            } else {
                cleanIframeAttributes();
            }
            
            // ========== Remove ChromeDriver cookie indicator ==========
            try {
                const cdCookie = 'ChromeDriverwjers908fljsdf37459fsdfgdfwru=';
                if (document.cookie.indexOf(cdCookie) > -1) {
                    document.cookie = cdCookie + '; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
                }
            } catch(e) {}
            
            // ========== Chrome Runtime Emulation ==========
            window.chrome = {
                runtime: {
                    PlatformOs: {
                        MAC: 'mac',
                        WIN: 'win',
                        ANDROID: 'android',
                        CROS: 'cros',
                        LINUX: 'linux',
                        OPENBSD: 'openbsd'
                    },
                    PlatformArch: {
                        ARM: 'arm',
                        X86_32: 'x86-32',
                        X86_64: 'x86-64'
                    },
                    PlatformNaclArch: {
                        ARM: 'arm',
                        X86_32: 'x86-32',
                        X86_64: 'x86-64'
                    },
                    RequestUpdateCheckStatus: {
                        THROTTLED: 'throttled',
                        NO_UPDATE: 'no_update',
                        UPDATE_AVAILABLE: 'update_available'
                    },
                    OnInstalledReason: {
                        INSTALL: 'install',
                        UPDATE: 'update',
                        CHROME_UPDATE: 'chrome_update',
                        SHARED_MODULE_UPDATE: 'shared_module_update'
                    },
                    OnRestartRequiredReason: {
                        APP_UPDATE: 'app_update',
                        OS_UPDATE: 'os_update',
                        PERIODIC: 'periodic'
                    },
                    connect: function() {},
                    sendMessage: function() {},
                    id: undefined
                },
                loadTimes: function() {
                    return {
                        requestTime: Date.now() * 0.001 - Math.random() * 100,
                        startLoadTime: Date.now() * 0.001 - Math.random() * 50,
                        commitLoadTime: Date.now() * 0.001 - Math.random() * 30,
                        finishDocumentLoadTime: Date.now() * 0.001 - Math.random() * 10,
                        finishLoadTime: Date.now() * 0.001,
                        firstPaintTime: Date.now() * 0.001 - Math.random() * 20,
                        firstPaintAfterLoadTime: 0,
                        navigationType: 'Other',
                        wasFetchedViaSpdy: false,
                        wasNpnNegotiated: true,
                        npnNegotiatedProtocol: 'h2',
                        wasAlternateProtocolAvailable: false,
                        connectionInfo: 'h2'
                    };
                },
                csi: function() {
                    return {
                        onloadT: Date.now(),
                        startE: Date.now() - Math.random() * 1000,
                        pageT: Math.random() * 1000
                    };
                },
                app: {
                    isInstalled: false,
                    InstallState: {
                        DISABLED: 'disabled',
                        INSTALLED: 'installed',
                        NOT_INSTALLED: 'not_installed'
                    },
                    RunningState: {
                        CANNOT_RUN: 'cannot_run',
                        READY_TO_RUN: 'ready_to_run',
                        RUNNING: 'running'
                    }
                }
            };
            
            // ========== Navigator Properties ==========
            // Realistic plugins array
            const makePlugin = (name, description, filename) => {
                const plugin = Object.create(Plugin.prototype);
                Object.defineProperties(plugin, {
                    name: { value: name, enumerable: true },
                    description: { value: description, enumerable: true },
                    filename: { value: filename, enumerable: true },
                    length: { value: 1, enumerable: true }
                });
                return plugin;
            };
            
            const plugins = [
                makePlugin('Chrome PDF Plugin', 'Portable Document Format', 'internal-pdf-viewer'),
                makePlugin('Chrome PDF Viewer', '', 'mhjfbmdgcfjbbpaeojofohoefgiehjai'),
                makePlugin('Native Client', '', 'internal-nacl-plugin')
            ];
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const pluginArray = Object.create(PluginArray.prototype);
                    plugins.forEach((p, i) => pluginArray[i] = p);
                    Object.defineProperty(pluginArray, 'length', { value: plugins.length });
                    pluginArray.item = (i) => plugins[i] || null;
                    pluginArray.namedItem = (name) => plugins.find(p => p.name === name) || null;
                    pluginArray.refresh = () => {};
                    return pluginArray;
                },
                configurable: true
            });
            
            // Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
                configurable: true
            });
            
            // Platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32',
                configurable: true
            });
            
            // Hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
                configurable: true
            });
            
            // Device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
                configurable: true
            });
            
            // Max touch points (desktop = 0)
            Object.defineProperty(navigator, 'maxTouchPoints', {
                get: () => 0,
                configurable: true
            });
            
            // Connection info
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 50,
                    downlink: 10,
                    saveData: false
                }),
                configurable: true
            });
            
            // ========== Permissions API ==========
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => {
                if (parameters.name === 'notifications') {
                    return Promise.resolve({ state: 'prompt', onchange: null });
                }
                return originalQuery.call(navigator.permissions, parameters);
            };
            
            // ========== WebGL Fingerprint (PX821, PX822, PX823) ==========
            const getParameterProxyHandler = {
                apply: function(target, thisArg, args) {
                    const param = args[0];
                    
                    // UNMASKED_VENDOR_WEBGL (37445)
                    if (param === 37445) {
                        return 'Google Inc. (NVIDIA)';
                    }
                    // UNMASKED_RENDERER_WEBGL (37446)
                    if (param === 37446) {
                        return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)';
                    }
                    // MAX_TEXTURE_SIZE
                    if (param === 3379) {
                        return 16384;
                    }
                    // MAX_VERTEX_ATTRIBS
                    if (param === 34921) {
                        return 16;
                    }
                    // MAX_VERTEX_UNIFORM_VECTORS
                    if (param === 36347) {
                        return 4096;
                    }
                    // MAX_VARYING_VECTORS
                    if (param === 36348) {
                        return 30;
                    }
                    // MAX_FRAGMENT_UNIFORM_VECTORS
                    if (param === 36349) {
                        return 1024;
                    }
                    return target.apply(thisArg, args);
                }
            };
            
            // Apply to WebGL
            const getWebGLContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type, ...args) {
                const context = getWebGLContext.call(this, type, ...args);
                if (context && (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl')) {
                    context.getParameter = new Proxy(context.getParameter, getParameterProxyHandler);
                }
                return context;
            };
            
            // ========== Screen Properties (PX91, PX92, PX93, PX269, PX270) ==========
            Object.defineProperty(screen, 'width', { get: () => 1920, configurable: true });
            Object.defineProperty(screen, 'height', { get: () => 1080, configurable: true });
            Object.defineProperty(screen, 'availWidth', { get: () => 1920, configurable: true });
            Object.defineProperty(screen, 'availHeight', { get: () => 1040, configurable: true });
            Object.defineProperty(screen, 'colorDepth', { get: () => 24, configurable: true });
            Object.defineProperty(screen, 'pixelDepth', { get: () => 24, configurable: true });
            
            // ========== Window Properties (PX185, PX186, PX187, PX188) ==========
            Object.defineProperty(window, 'outerWidth', { get: () => 1920, configurable: true });
            Object.defineProperty(window, 'outerHeight', { get: () => 1040, configurable: true });
            Object.defineProperty(window, 'innerWidth', { get: () => 1903, configurable: true });
            Object.defineProperty(window, 'innerHeight', { get: () => 969, configurable: true });
            Object.defineProperty(window, 'screenX', { get: () => 0, configurable: true });
            Object.defineProperty(window, 'screenY', { get: () => 0, configurable: true });
            
            // ========== Performance Timing (PX1055, PX1056) ==========
            if (window.performance && window.performance.timing) {
                const timing = window.performance.timing;
                // Ensure timing values look realistic
            }
            
            // ========== Navigator Additional Properties (PX59-PX69) ==========
            Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.', configurable: true });
            Object.defineProperty(navigator, 'product', { get: () => 'Gecko', configurable: true });
            Object.defineProperty(navigator, 'productSub', { get: () => '20030107', configurable: true });
            Object.defineProperty(navigator, 'appVersion', { 
                get: () => '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 
                configurable: true 
            });
            Object.defineProperty(navigator, 'appName', { get: () => 'Netscape', configurable: true });
            Object.defineProperty(navigator, 'appCodeName', { get: () => 'Mozilla', configurable: true });
            
            // ========== Date/Timezone (PX155, PX1008) ==========
            // Timezone offset for America/New_York
            const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
            Date.prototype.getTimezoneOffset = function() {
                return 300; // EST (UTC-5) in minutes
            };
            
            // ========== PDF Plugins (PX85) ==========
            Object.defineProperty(navigator, 'pdfViewerEnabled', { get: () => true, configurable: true });
            
            // ========== Cookie Enabled (PX86) ==========
            Object.defineProperty(navigator, 'cookieEnabled', { get: () => true, configurable: true });
            
            // ========== Java Enabled (PX88) ==========
            navigator.javaEnabled = () => false;
            
            // ========== Do Not Track (PX89) ==========
            Object.defineProperty(navigator, 'doNotTrack', { get: () => null, configurable: true });
            
            // ========== Online Status (PX60) ==========
            Object.defineProperty(navigator, 'onLine', { get: () => true, configurable: true });
            
            // ========== Document Properties ==========
            Object.defineProperty(document, 'hidden', {
                get: () => false,
                configurable: true
            });
            
            Object.defineProperty(document, 'visibilityState', {
                get: () => 'visible',
                configurable: true
            });
        """)
    
    def start(self, headless: bool = True) -> None:
        """Start the browser with configured settings.
        
        Args:
            headless: Whether to run browser in headless mode
            
        Requirements: 3.1, 3.2
        """
        self._playwright = sync_playwright().start()
        
        # Configure launch options with comprehensive anti-detection args
        launch_options = {
            "headless": headless,
            "args": [
                # Core anti-detection
                "--disable-blink-features=AutomationControlled",
                "--disable-automation",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                
                # Window and display
                "--window-size=1920,1080",
                "--start-maximized",
                
                # Disable automation flags
                "--disable-extensions",
                "--disable-default-apps",
                "--disable-component-extensions-with-background-pages",
                
                # WebGL and GPU
                "--enable-webgl",
                "--use-gl=swiftshader",
                "--enable-accelerated-2d-canvas",
                
                # Network
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
                
                # Privacy and fingerprinting
                "--disable-features=AudioServiceOutOfProcess",
                "--disable-features=TranslateUI",
                
                # Performance
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-breakpad",
                "--disable-client-side-phishing-detection",
                "--disable-component-update",
                "--disable-hang-monitor",
                "--disable-ipc-flooding-protection",
                "--disable-popup-blocking",
                "--disable-prompt-on-repost",
                "--disable-renderer-backgrounding",
                "--disable-sync",
                "--metrics-recording-only",
                "--no-first-run",
                "--password-store=basic",
                "--use-mock-keychain",
                
                # Exclude automation switches
                "--excludeSwitches=enable-automation",
            ]
        }
        
        self._browser = self._playwright.chromium.launch(**launch_options)
        
        # Configure context options with proxy if provided
        context_options = {
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "color_scheme": "light",
            "reduced_motion": "no-preference",
            "has_touch": False,
            "is_mobile": False,
            "device_scale_factor": 1,
            "java_script_enabled": True,
            "bypass_csp": False,
            "extra_http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "max-age=0",
                "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
            "permissions": ["geolocation"],
            "geolocation": {"latitude": 40.7128, "longitude": -74.0060},  # New York
        }
        
        if self.proxy_url:
            context_options["proxy"] = {"server": self.proxy_url}
        
        self._context = self._browser.new_context(**context_options)
        self._configure_stealth(self._context)
        self._page = self._context.new_page()
        
        # Set up response monitoring
        self._page.on("response", self._on_response)

    
    def _on_response(self, response: Response) -> None:
        """Handle response events for URL monitoring.
        
        Args:
            response: The response object from Playwright
        """
        for url_pattern in self._monitored_urls:
            if url_pattern in response.url:
                self._captured_responses.append(response)
    
    def stop(self) -> None:
        """Stop the browser and clean up resources."""
        if self._page:
            self._page.close()
            self._page = None
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
    
    def navigate(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """Navigate to a URL and wait for page load.
        
        Args:
            url: The URL to navigate to
            wait_until: When to consider navigation complete
                       ("load", "domcontentloaded", "networkidle")
                       
        Requirements: 3.3
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        self._page.goto(url, wait_until=wait_until, timeout=self.PAGE_LOAD_TIMEOUT)
    
    def refresh(self) -> None:
        """Refresh the current page."""
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        self._page.reload(wait_until="domcontentloaded", timeout=self.PAGE_LOAD_TIMEOUT)
    
    def wait_for_element(self, selector: str, timeout: Optional[int] = None) -> bool:
        """Wait for an element to be visible on the page.
        
        Args:
            selector: CSS selector for the element
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            True if element found, False if timeout
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        try:
            self._page.wait_for_selector(
                selector, 
                state="visible", 
                timeout=timeout or self.ELEMENT_TIMEOUT
            )
            return True
        except Exception:
            return False
    
    def _human_delay(self, min_ms: int = 50, max_ms: int = 150) -> None:
        """Add a random human-like delay.
        
        Args:
            min_ms: Minimum delay in milliseconds
            max_ms: Maximum delay in milliseconds
        """
        delay = random.randint(min_ms, max_ms) / 1000.0
        time.sleep(delay)
    
    def _human_type(self, selector: str, value: str) -> None:
        """Type text with human-like delays between keystrokes.
        
        Args:
            selector: CSS selector for the input element
            value: Value to type
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        # Click on the element first
        self._page.click(selector)
        self._human_delay(100, 300)
        
        # Clear existing content
        self._page.fill(selector, "")
        self._human_delay(50, 100)
        
        # Type each character with random delay
        for char in value:
            self._page.type(selector, char, delay=random.randint(30, 120))
            # Occasionally add a longer pause (simulating thinking)
            if random.random() < 0.1:
                self._human_delay(200, 500)
        
        # Small delay after typing
        self._human_delay(100, 300)
    
    def _human_click(self, selector: str) -> None:
        """Click with human-like behavior (move to element, pause, click).
        
        Args:
            selector: CSS selector for the element to click
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        # Get element bounding box
        element = self._page.locator(selector)
        box = element.bounding_box()
        
        if box:
            # Calculate a random point within the element
            x = box['x'] + random.uniform(box['width'] * 0.2, box['width'] * 0.8)
            y = box['y'] + random.uniform(box['height'] * 0.2, box['height'] * 0.8)
            
            # Move mouse to element with some randomness
            self._page.mouse.move(x, y)
            self._human_delay(50, 150)
            
            # Click
            self._page.mouse.click(x, y)
        else:
            # Fallback to regular click
            self._page.click(selector)
        
        self._human_delay(100, 300)
    
    def fill_input(self, selector: str, value: str, human_like: bool = True) -> None:
        """Fill an input field with a value.
        
        Args:
            selector: CSS selector for the input element
            value: Value to fill in the input
            human_like: Whether to use human-like typing (default True)
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        if human_like:
            self._human_type(selector, value)
        else:
            self._page.fill(selector, value)
    
    def fill_input_by_dynamic_id(self, base_pattern: str, value: str, human_like: bool = True) -> bool:
        """Fill an input field that has a dynamic ID suffix.
        
        Args:
            base_pattern: The base ID pattern (e.g., "dwfrm_profile_login_password_")
            value: Value to fill in the input
            human_like: Whether to use human-like typing (default True)
            
        Returns:
            True if element found and filled, False otherwise
            
        Requirements: 4.3, 4.4
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        selector = build_dynamic_id_selector(base_pattern)
        if self.wait_for_element(selector):
            if human_like:
                self._human_type(selector, value)
            else:
                self._page.fill(selector, value)
            return True
        return False
    
    def click_button(self, selector: str, human_like: bool = True) -> None:
        """Click a button element.
        
        Args:
            selector: CSS selector for the button
            human_like: Whether to use human-like clicking (default True)
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        if human_like:
            self._human_click(selector)
        else:
            self._page.click(selector)
    
    def select_dropdown(self, selector: str, value: str, human_like: bool = True) -> None:
        """Select an option from a dropdown.
        
        Args:
            selector: CSS selector for the select element
            value: Value or label to select
            human_like: Whether to add human-like delays (default True)
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        if human_like:
            self._human_click(selector)
            self._human_delay(200, 400)
        
        self._page.select_option(selector, value)
        
        if human_like:
            self._human_delay(100, 300)
    
    def monitor_request(self, url_pattern: str) -> None:
        """Start monitoring for requests matching a URL pattern.
        
        Args:
            url_pattern: URL pattern to monitor for
        """
        if url_pattern not in self._monitored_urls:
            self._monitored_urls.append(url_pattern)
    
    def stop_monitoring(self, url_pattern: str) -> None:
        """Stop monitoring a URL pattern.
        
        Args:
            url_pattern: URL pattern to stop monitoring
        """
        if url_pattern in self._monitored_urls:
            self._monitored_urls.remove(url_pattern)
    
    def clear_captured_responses(self) -> None:
        """Clear all captured responses."""
        self._captured_responses.clear()
    
    def get_captured_responses(self, url_pattern: Optional[str] = None) -> List[Response]:
        """Get captured responses, optionally filtered by URL pattern.
        
        Args:
            url_pattern: Optional URL pattern to filter by
            
        Returns:
            List of captured Response objects
        """
        if url_pattern:
            return [r for r in self._captured_responses if url_pattern in r.url]
        return self._captured_responses.copy()
    
    def wait_for_navigation(self, url_pattern: str, timeout: Optional[int] = None) -> bool:
        """Wait for navigation to a URL matching the pattern.
        
        Args:
            url_pattern: URL pattern to wait for
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            True if navigation detected, False if timeout
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        try:
            self._page.wait_for_url(
                f"**{url_pattern}**",
                timeout=timeout or self.PAGE_LOAD_TIMEOUT
            )
            return True
        except Exception:
            return False
    
    def wait_for_response(self, url_pattern: str, status_code: Optional[int] = None, 
                          timeout: Optional[int] = None) -> bool:
        """Wait for a response matching the URL pattern and optional status code.
        
        Args:
            url_pattern: URL pattern to wait for
            status_code: Optional HTTP status code to match
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            True if matching response received, False if timeout
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        try:
            def predicate(response: Response) -> bool:
                if url_pattern not in response.url:
                    return False
                if status_code is not None and response.status != status_code:
                    return False
                return True
            
            self._page.wait_for_event(
                "response",
                predicate=predicate,
                timeout=timeout or self.PAGE_LOAD_TIMEOUT
            )
            return True
        except Exception:
            return False

    def wait_for_response_with_data(self, url_pattern: str, status_code: Optional[int] = None,
                                     timeout: Optional[int] = None) -> Optional[dict]:
        """Wait for a response and return status code and body data.
        
        Args:
            url_pattern: URL pattern to wait for
            status_code: Optional HTTP status code to match
            timeout: Maximum time to wait in milliseconds
            
        Returns:
            Dictionary with 'status', 'url', 'headers', and 'body' if found, None if timeout
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        try:
            def predicate(response: Response) -> bool:
                if url_pattern not in response.url:
                    return False
                if status_code is not None and response.status != status_code:
                    return False
                return True
            
            response = self._page.wait_for_event(
                "response",
                predicate=predicate,
                timeout=timeout or self.PAGE_LOAD_TIMEOUT
            )
            
            # Try to get response body
            try:
                body = response.text()
            except Exception:
                body = ""
            
            return {
                "status": response.status,
                "url": response.url,
                "headers": dict(response.headers),
                "body": body
            }
        except Exception:
            return None
    
    def wait_for_url_change(self, timeout: int = 120000) -> str:
        """Wait for URL to change from the current URL.
        
        This method monitors the page for URL changes and returns the new URL
        when a change is detected. Useful for detecting when manual verification
        completes and the page redirects.
        
        Args:
            timeout: Maximum time to wait in milliseconds (default 120 seconds)
            
        Returns:
            The new URL after the change
            
        Raises:
            RuntimeError: If browser not started
            TimeoutError: If URL doesn't change within timeout
            
        Requirements: 3.1, 3.2, 3.3
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        current_url = self._page.url
        start_time = time.time()
        timeout_seconds = timeout / 1000.0
        
        while time.time() - start_time < timeout_seconds:
            try:
                # Check if URL has changed
                new_url = self._page.url
                if new_url != current_url:
                    return new_url
                
                # Small delay to avoid busy waiting
                time.sleep(0.5)
            except Exception:
                # Page might be navigating, continue waiting
                time.sleep(0.5)
        
        raise TimeoutError(f"URL did not change within {timeout}ms")
    
    def is_challenge_present(self, selectors: List[str]) -> bool:
        """Check if any PerimeterX challenge elements are present on the page.
        
        This method checks for the presence of challenge elements using the
        provided list of CSS selectors. It's used to detect when a challenge
        appears or disappears.
        
        Args:
            selectors: List of CSS selectors to check for challenge elements
            
        Returns:
            True if any challenge element is present and visible, False otherwise
            
        Raises:
            RuntimeError: If browser not started
            
        Requirements: 3.1, 3.2, 3.3
        """
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        
        for selector in selectors:
            try:
                element = self._page.locator(selector)
                # Check if element exists and is visible
                if element.count() > 0:
                    # Try to check visibility with a short timeout
                    try:
                        if element.first.is_visible(timeout=1000):
                            return True
                    except Exception:
                        # If visibility check fails, assume not visible
                        continue
            except Exception:
                # Selector might be invalid or element not found, continue
                continue
        
        return False
    
    @property
    def page(self) -> Optional[Page]:
        """Get the current page object."""
        return self._page
    
    @property
    def current_url(self) -> str:
        """Get the current page URL."""
        if not self._page:
            return ""
        return self._page.url
