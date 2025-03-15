import json
import time
import os
import argparse
import logging
import getpass
import random
import re
import requests
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tweet_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define folder paths
TWEETS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tweets")
IMAGES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

# Create folders if they don't exist
os.makedirs(TWEETS_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)

class TweetScraper:
    def __init__(self, username, headless=True, max_tweets=None, email=None, password=None, use_profile=True, profile_dir=None, user_agent=None):
        """
        Initialize the TweetScraper.
        
        Args:
            username (str): The Twitter/X username to scrape tweets from
            headless (bool): Whether to run the browser in headless mode
            max_tweets (int): Maximum number of tweets to scrape
            email (str): Email for X.com login
            password (str): Password for X.com login
            use_profile (bool): Whether to use a persistent Chrome profile
            profile_dir (str): Directory for Chrome profile
            user_agent (str): Custom user agent string
        """
        self.username = username
        self.profile_url = f"https://x.com/{username}"
        self.nitter_url = f"https://nitter.net/{username}"
        self.headless = headless
        self.max_tweets = max_tweets
        self.email = email
        self.password = password
        self.use_profile = use_profile
        
        # Set up Chrome profile directory
        if profile_dir:
            self.profile_dir = profile_dir
        else:
            self.profile_dir = os.path.expanduser("~/.chrome_profiles/tweet_scraper")
        
        # Create profile directory if it doesn't exist
        if not os.path.exists(self.profile_dir) and self.use_profile:
            os.makedirs(self.profile_dir, exist_ok=True)
        
        # Set up user agent
        if user_agent:
            self.user_agent = user_agent
        else:
            # Default user agent
            self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        
        logger.info(f"Initializing TweetScraper for user: {username}")
        logger.info(f"Profile URL: {self.profile_url}")
        logger.info(f"Headless mode: {headless}")
        logger.info(f"Max tweets: {max_tweets}")
        logger.info(f"Login credentials provided: {bool(email and password)}")
        logger.info(f"Using Chrome profile: {use_profile}")
        logger.info(f"Using Chrome profile directory: {self.profile_dir}")
        logger.info(f"Using user agent: {self.user_agent}")
        
        # Initialize Chrome WebDriver
        self._init_driver()
    
    def _init_driver(self):
        # Configure Chrome options
        chrome_options = Options()
        
        # Add profile directory if using a profile
        if self.use_profile:
            chrome_options.add_argument(f"--user-data-dir={self.profile_dir}")
        
        # Configure headless mode
        if self.headless:
            # Use the new headless mode with JS enabled
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
        
        # Add arguments to make Chrome more stealthy
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Explicitly enable JavaScript
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.javascript": 1,
            "profile.managed_default_content_settings.javascript": 1,
            "profile.managed_default_content_settings.images": 1,
            "profile.default_content_setting_values.cookies": 1
        })
        
        # Add user agent to avoid detection - use a more recent and realistic user agent
        chrome_options.add_argument(f"--user-agent={self.user_agent}")
        logger.info(f"Using user agent: {self.user_agent}")
        
        # Add experimental options to avoid detection
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        logger.info("Starting Chrome WebDriver...")
        try:
            # Initialize the Chrome WebDriver
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Execute CDP commands to avoid detection
            self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": self.user_agent
            })
            
            # Execute script to avoid detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Additional anti-detection measures
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    // Overwrite the 'navigator.webdriver' property to undefined
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Overwrite the 'navigator.plugins' to make it look more realistic
                    const makePluginsLookNatural = () => {
                        if (navigator.plugins.length === 0) {
                            Object.defineProperty(navigator, 'plugins', {
                                get: () => [1, 2, 3, 4, 5]
                            });
                        }
                    };
                    makePluginsLookNatural();
                    
                    // Overwrite the 'navigator.languages' property
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    
                    // Overwrite the 'window.chrome' property
                    window.chrome = {
                        runtime: {}
                    };
                    
                    // Add missing chrome functions
                    if (window.chrome) {
                        window.chrome.app = {
                            InstallState: 'hehe',
                            RunningState: 'haha',
                            getDetails: function() { return {}; },
                            getIsInstalled: function() { return true; },
                            isInstalled: true
                        };
                        
                        window.chrome.csi = function() { return {}; };
                        window.chrome.loadTimes = function() { return {}; };
                        window.chrome.runtime = {
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
                            PlatformArch: {
                                ARM: 'arm',
                                ARM64: 'arm64',
                                MIPS: 'mips',
                                MIPS64: 'mips64',
                                X86_32: 'x86-32',
                                X86_64: 'x86-64'
                            },
                            PlatformNaclArch: {
                                ARM: 'arm',
                                MIPS: 'mips',
                                MIPS64: 'mips64',
                                X86_32: 'x86-32',
                                X86_64: 'x86-64'
                            },
                            PlatformOs: {
                                ANDROID: 'android',
                                CROS: 'cros',
                                LINUX: 'linux',
                                MAC: 'mac',
                                OPENBSD: 'openbsd',
                                WIN: 'win'
                            },
                            RequestUpdateCheckStatus: {
                                THROTTLED: 'throttled',
                                NO_UPDATE: 'no_update',
                                UPDATE_AVAILABLE: 'update_available'
                            }
                        };
                    }
                    
                    // Fix iframe contentWindow access
                    try {
                        if (HTMLIFrameElement.prototype.contentWindow) {
                            Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                                get: function() {
                                    return window;
                                }
                            });
                        }
                    } catch(e) {}
                    
                    // Fix canvas fingerprinting
                    const originalGetContext = HTMLCanvasElement.prototype.getContext;
                    HTMLCanvasElement.prototype.getContext = function(type, attributes) {
                        const context = originalGetContext.call(this, type, attributes);
                        if (context && type === '2d') {
                            const originalGetImageData = context.getImageData;
                            context.getImageData = function() {
                                const imageData = originalGetImageData.apply(this, arguments);
                                // Add some random noise to the image data
                                for (let i = 0; i < imageData.data.length; i += 4) {
                                    const noise = Math.floor(Math.random() * 3) - 1;
                                    imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + noise));
                                    imageData.data[i+1] = Math.max(0, Math.min(255, imageData.data[i+1] + noise));
                                    imageData.data[i+2] = Math.max(0, Math.min(255, imageData.data[i+2] + noise));
                                }
                                return imageData;
                            };
                        }
                        return context;
                    };
                    
                    // Fix WebGL fingerprinting
                    const getParameterProxyHandler = {
                        apply: function(target, ctx, args) {
                            const param = args[0];
                            // UNMASKED_VENDOR_WEBGL or UNMASKED_RENDERER_WEBGL
                            if (param === 37445 || param === 37446) {
                                return param === 37445 ? 'Google Inc.' : 'ANGLE (Apple, Apple M1, OpenGL 4.1)';
                            }
                            return target.apply(ctx, args);
                        }
                    };
                    
                    try {
                        const getParameter = WebGLRenderingContext.prototype.getParameter;
                        WebGLRenderingContext.prototype.getParameter = new Proxy(getParameter, getParameterProxyHandler);
                    } catch(e) {}
                """
            })
            
            logger.info("Chrome WebDriver started successfully")
            
            # Test if JavaScript is enabled
            self.driver.get("about:blank")
            js_enabled = self.driver.execute_script("return true;")
            logger.info(f"JavaScript is {'enabled' if js_enabled else 'disabled'}")
            
        except Exception as e:
            logger.error(f"Failed to start Chrome WebDriver: {e}")
            raise
    
    def login(self):
        """
        Log in to X.com using the provided credentials.
        
        Returns:
            bool: True if login was successful, False otherwise
        """
        if not self.email or not self.password:
            logger.warning("No login credentials provided. Cannot log in.")
            return False
        
        logger.info("Attempting to log in to X.com...")
        try:
            # Navigate to the login page
            self.driver.get("https://x.com/i/flow/login")
            logger.info("Navigated to login page")
            
            # Take a screenshot of the login page
            self.driver.save_screenshot("login_page.png")
            logger.info("Saved login page screenshot")
            
            # Wait for the login form to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "text"))
                )
                logger.info("Login form loaded successfully")
            except TimeoutException:
                logger.error("Login form did not load properly")
                # Try an alternative selector
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
                    )
                    logger.info("Found alternative login input")
                except TimeoutException:
                    logger.error("Could not find any login input field")
                    self.driver.save_screenshot("login_form_not_found.png")
                    with open("login_page_source.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info("Saved login page source for debugging")
                    return False
            
            # Enter email/username with human-like typing
            logger.info("Entering email/username")
            try:
                email_field = self.driver.find_element(By.NAME, "text")
            except NoSuchElementException:
                try:
                    email_field = self.driver.find_element(By.CSS_SELECTOR, "input[autocomplete='username']")
                except NoSuchElementException:
                    logger.error("Could not find email input field")
                    return False
            
            # Type like a human with random delays
            for char in self.email:
                email_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2))
            
            time.sleep(random.uniform(0.5, 1.5))
            
            # Click the Next button
            try:
                next_button = self.driver.find_element(By.XPATH, "//span[text()='Next']")
                next_button.click()
                logger.info("Clicked Next button")
            except NoSuchElementException:
                # Try pressing Enter instead
                email_field.send_keys(Keys.RETURN)
                logger.info("Pressed Enter to submit email")
            
            logger.info("Submitted email/username")
            
            # Save a screenshot after submitting email
            self.driver.save_screenshot("after_email_submit.png")
            logger.info("Saved screenshot after email submission")
            
            # Check for verification or unusual activity challenges
            try:
                # Check for "Unusual login activity" or verification screens
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Verify your identity')]"))
                )
                logger.warning("Identity verification required. X.com is asking for additional verification.")
                self.driver.save_screenshot("verification_required.png")
                logger.info("Saved verification screen screenshot")
                logger.info("Please log in manually once to verify your account, then try again.")
                return False
            except TimeoutException:
                # No verification needed, continue with login
                pass
                
            # Check for "We need to confirm your email" screen
            try:
                confirm_email = self.driver.find_element(By.XPATH, "//*[contains(text(), 'confirm your email')]")
                if confirm_email:
                    logger.warning("X.com is asking to confirm your email.")
                    self.driver.save_screenshot("confirm_email.png")
                    
                    # Try to find and click the "Use phone instead" option
                    try:
                        use_phone = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Use phone instead')]")
                        use_phone.click()
                        logger.info("Clicked 'Use phone instead'")
                        time.sleep(2)
                    except NoSuchElementException:
                        logger.warning("Could not find 'Use phone instead' option")
            except NoSuchElementException:
                # No email confirmation needed
                pass
                
            # Check for username verification (sometimes X asks for username after email)
            try:
                username_field = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.NAME, "text"))
                )
                logger.info("Username verification field found")
                
                # Enter username
                for char in self.email.split('@')[0]:  # Use part before @ as username
                    username_field.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.2))
                
                # Click Next or press Enter
                try:
                    next_button = self.driver.find_element(By.XPATH, "//span[text()='Next']")
                    next_button.click()
                except NoSuchElementException:
                    username_field.send_keys(Keys.RETURN)
                
                logger.info("Submitted username verification")
                time.sleep(2)
            except TimeoutException:
                # No username verification needed
                pass
            
            # Wait for password field with increased timeout
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.NAME, "password"))
                )
                logger.info("Password field loaded")
            except TimeoutException:
                logger.error("Password field did not load")
                
                # Try alternative selectors for password field
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                    logger.info("Found password field using alternative selector")
                except NoSuchElementException:
                    # Save the current page for debugging
                    self.driver.save_screenshot("password_field_not_found.png")
                    with open("password_page_source.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info("Saved page source when password field not found")
                    
                    # Check if we're on a challenge page
                    if "challenge" in self.driver.current_url:
                        logger.error("X.com is showing a challenge page. Manual verification may be required.")
                    
                    return False
            
            # Enter password with human-like typing
            logger.info("Entering password")
            try:
                password_field = self.driver.find_element(By.NAME, "password")
            except NoSuchElementException:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                except NoSuchElementException:
                    logger.error("Could not find password field after waiting")
                    return False
            
            for char in self.password:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.2))
            
            time.sleep(random.uniform(0.5, 1.5))
            
            # Click the Log in button
            try:
                login_button = self.driver.find_element(By.XPATH, "//span[text()='Log in']")
                login_button.click()
                logger.info("Clicked Log in button")
            except NoSuchElementException:
                # Try pressing Enter instead
                password_field.send_keys(Keys.RETURN)
                logger.info("Pressed Enter to submit password")
            
            logger.info("Submitted password")
            
            # Wait for login to complete
            logger.info("Waiting for login to complete...")
            time.sleep(5)  # Give some time for the login to process
            
            # Save screenshot after login attempt
            self.driver.save_screenshot("after_login_attempt.png")
            
            # Check if login was successful by looking for the home timeline
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='primaryColumn']"))
                )
                logger.info("Login successful")
                
                # Save cookies for future use
                cookies = self.driver.get_cookies()
                with open("x_cookies.json", "w") as f:
                    json.dump(cookies, f)
                logger.info("Saved cookies for future use")
                
                return True
            except TimeoutException:
                logger.error("Login failed - could not find home timeline")
                
                # Take a screenshot for debugging
                screenshot_path = "login_failed.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Saved login failure screenshot to {screenshot_path}")
                
                # Check for error messages
                try:
                    error_messages = self.driver.find_elements(By.CSS_SELECTOR, "div[role='alert']")
                    for error in error_messages:
                        logger.error(f"Login error message: {error.text}")
                except:
                    pass
                
                # Check for two-factor authentication
                if "Enter your verification code" in self.driver.page_source:
                    logger.error("Two-factor authentication is enabled. Manual login required.")
                    
                return False
                
        except Exception as e:
            logger.error(f"Error during login: {e}", exc_info=True)
            return False
    
    def load_cookies(self):
        """
        Load cookies from file if available
        
        Returns:
            bool: True if cookies were loaded successfully, False otherwise
        """
        cookie_file = "x_cookies.json"
        if not os.path.exists(cookie_file):
            logger.info("No cookie file found")
            return False
        
        try:
            with open(cookie_file, "r") as f:
                cookies = json.load(f)
            
            # Navigate to the domain first
            self.driver.get("https://x.com")
            
            # Add the cookies
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Could not add cookie: {e}")
            
            logger.info("Cookies loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False
        
    def scrape_tweets(self):
        """
        Scrape tweets from the user's profile and return them as a list of dictionaries.
        
        Returns:
            list: A list of dictionaries containing tweet data
        """
        logger.info(f"Scraping tweets from {self.username}'s profile...")
        
        # Try to load cookies first
        cookies_loaded = self.load_cookies()
        
        # First try using nitter.net as it's more reliable for scraping
        try:
            logger.info(f"Attempting to use nitter.net to scrape tweets...")
            self.driver.get(self.nitter_url)
            logger.info(f"Navigated to {self.nitter_url}")
            
            # Take a screenshot for debugging
            screenshot_path = f"{self.username}_nitter.png"
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Saved nitter screenshot to {screenshot_path}")
            
            # Log the current URL in case of redirects
            logger.info(f"Current URL: {self.driver.current_url}")
            
            # Check if nitter is working
            if "nitter.net" not in self.driver.current_url:
                logger.warning("Redirected away from nitter.net. The instance might be blocked or down.")
                logger.info("Will try X.com directly as fallback.")
            else:
                # Check for tweets on nitter
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".timeline-item"))
                    )
                    logger.info("Found tweets on nitter.net")
                    
                    # Extract tweets from nitter
                    tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, ".timeline-item")
                    logger.info(f"Found {len(tweet_elements)} tweets on nitter.net")
                    
                    tweets = []
                    for tweet_element in tweet_elements:
                        try:
                            # Extract tweet data from nitter
                            tweet_data = self._extract_nitter_tweet_data(tweet_element)
                            if tweet_data:
                                tweets.append(tweet_data)
                                logger.info(f"Scraped tweet {len(tweets)} from nitter: {tweet_data['text'][:50]}...")
                                
                                # Check if we've reached the maximum number of tweets
                                if self.max_tweets and len(tweets) >= self.max_tweets:
                                    logger.info(f"Reached maximum number of tweets ({self.max_tweets})")
                                    return tweets
                        except Exception as e:
                            logger.warning(f"Error extracting tweet data from nitter: {e}")
                    
                    if tweets:
                        logger.info(f"Successfully scraped {len(tweets)} tweets from nitter.net")
                        return tweets
                    else:
                        logger.warning("No tweets were scraped from nitter.net")
                        logger.info("Will try X.com directly as fallback.")
                except TimeoutException:
                    logger.error("Timeout waiting for tweets to load on nitter.net")
                    logger.info("Will try X.com directly as fallback.")
        except Exception as e:
            logger.error(f"Error using nitter.net: {e}")
            logger.info("Will try X.com directly as fallback.")
        
        # Fallback to X.com if nitter fails
        try:
            # Login if cookies weren't loaded and credentials are provided
            if not cookies_loaded and self.email and self.password:
                if not self.login():
                    logger.error("Failed to log in. Cannot scrape tweets.")
                    return []
            
            # Navigate to the user's profile
            self.driver.get(self.profile_url)
            logger.info(f"Navigated to {self.profile_url}")
            
            # Log the page title to verify we're on the right page
            logger.info(f"Page title: {self.driver.title}")
            
            # Take a screenshot for debugging
            screenshot_path = f"{self.username}_page_load.png"
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Saved screenshot to {screenshot_path}")
            
            # Log the current URL in case of redirects
            logger.info(f"Current URL: {self.driver.current_url}")
            
            # Check if we're on a login page
            if "login" in self.driver.current_url.lower() or "Log in to X" in self.driver.title:
                logger.error("Redirected to login page. X.com requires authentication to view tweets.")
                
                # Try to login if credentials are provided
                if self.email and self.password:
                    logger.info("Attempting to log in...")
                    if not self.login():
                        logger.error("Login failed. Cannot scrape tweets.")
                        return []
                    
                    # Navigate back to the profile after login
                    self.driver.get(self.profile_url)
                    logger.info(f"Navigated back to {self.profile_url} after login")
                else:
                    logger.info("Please provide login credentials using --email and --password options.")
                    return []
            
            # Check for JavaScript disabled message
            if "JavaScript is not available" in self.driver.page_source:
                logger.error("X.com is detecting that JavaScript is disabled. This is a critical issue.")
                with open(f"{self.username}_js_disabled.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                logger.info(f"Saved JavaScript disabled page source to {self.username}_js_disabled.html")
                
                # Try a different approach - use a mobile user agent
                logger.info("Attempting to bypass detection by using a mobile user agent...")
                
                # Close the current browser
                try:
                    self.driver.quit()
                except Exception:
                    pass
                
                # Configure new Chrome options with mobile user agent
                chrome_options = Options()
                if self.use_profile:
                    chrome_options.add_argument(f"--user-data-dir={self.profile_dir}")
                
                # Use a mobile user agent
                mobile_user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
                chrome_options.add_argument(f"--user-agent={mobile_user_agent}")
                logger.info(f"Using mobile user agent: {mobile_user_agent}")
                
                # Add other necessary options
                chrome_options.add_argument("--disable-notifications")
                chrome_options.add_argument("--disable-infobars")
                chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                chrome_options.add_argument("--window-size=375,812")  # iPhone X dimensions
                
                # Explicitly enable JavaScript
                chrome_options.add_experimental_option("prefs", {
                    "profile.default_content_setting_values.javascript": 1,
                    "profile.managed_default_content_settings.javascript": 1,
                    "profile.managed_default_content_settings.images": 1,
                    "profile.default_content_setting_values.cookies": 1
                })
                
                # Add experimental options to avoid detection
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option("useAutomationExtension", False)
                
                try:
                    # Initialize a new Chrome WebDriver with mobile settings
                    self.driver = webdriver.Chrome(options=chrome_options)
                    
                    # Execute CDP commands to avoid detection
                    self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                        "userAgent": mobile_user_agent
                    })
                    
                    # Execute script to avoid detection
                    self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    
                    # Navigate to the profile again
                    self.driver.get(self.profile_url)
                    logger.info(f"Navigated to {self.profile_url} with mobile user agent")
                    
                    # Take a screenshot for debugging
                    self.driver.save_screenshot(f"{self.username}_mobile_view.png")
                    logger.info(f"Saved mobile view screenshot")
                    
                    # Check if we still have JavaScript disabled message
                    if "JavaScript is not available" in self.driver.page_source:
                        logger.error("Still detecting JavaScript as disabled with mobile user agent.")
                        return []
                except Exception as e:
                    logger.error(f"Error restarting browser with mobile user agent: {e}")
                    return []
            
            # Wait for the page to load
            logger.info("Waiting for tweets to load...")
            try:
                WebDriverWait(self.driver, 30).until(  # Increased timeout to 30 seconds
                    EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
                )
                logger.info("Tweets loaded successfully")
            except TimeoutException:
                logger.error("Timeout waiting for tweets to load. Check if the profile exists or is private.")
                
                # Try alternative selectors for tweets
                try:
                    # Try to find any tweet-like elements
                    tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[data-testid='cellInnerDiv']")
                    if tweet_elements:
                        logger.info(f"Found {len(tweet_elements)} potential tweet elements using alternative selector")
                    else:
                        # Check if the profile doesn't exist or is private
                        if "This account doesn't exist" in self.driver.page_source:
                            logger.error("This X.com account doesn't exist")
                        elif "These posts are protected" in self.driver.page_source:
                            logger.error("This X.com account is private/protected")
                        elif "Something went wrong" in self.driver.page_source:
                            logger.error("X.com is showing 'Something went wrong' error")
                        
                        # Log the page source for debugging
                        with open(f"{self.username}_page_source.html", "w", encoding="utf-8") as f:
                            f.write(self.driver.page_source)
                        logger.info(f"Saved page source to {self.username}_page_source.html")
                        
                        return []
                except Exception as e:
                    logger.error(f"Error checking for alternative tweet elements: {e}")
                    return []
            
            tweets = []
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            logger.info(f"Initial page height: {last_height}")
            
            scroll_count = 0
            max_scrolls = 30  # Limit scrolling attempts
            
            while scroll_count < max_scrolls:
                scroll_count += 1
                logger.info(f"Scroll attempt {scroll_count}/{max_scrolls}")
                
                # Get all tweets currently in the DOM
                tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
                logger.info(f"Found {len(tweet_elements)} tweet elements in the DOM")
                
                # Process new tweets
                new_tweets_count = 0
                for tweet_element in tweet_elements[len(tweets):]:
                    tweet_data = self._extract_tweet_data(tweet_element)
                    if tweet_data:
                        tweets.append(tweet_data)
                        new_tweets_count += 1
                        logger.info(f"Scraped tweet {len(tweets)}: {tweet_data['text'][:50]}...")
                    
                    # Check if we've reached the maximum number of tweets
                    if self.max_tweets and len(tweets) >= self.max_tweets:
                        logger.info(f"Reached maximum number of tweets ({self.max_tweets})")
                        return tweets
                
                logger.info(f"Processed {new_tweets_count} new tweets in this scroll")
                
                # Scroll down to load more tweets - use a more human-like scrolling
                logger.info("Scrolling down to load more tweets...")
                
                # Random scroll amount to appear more human-like
                scroll_amount = random.randint(500, 1000)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(0.5, 1.0))
                
                # Continue scrolling to the bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for new content to load with a random delay
                logger.info("Waiting for new content to load...")
                time.sleep(random.uniform(1.5, 3.0))
                
                # Calculate new scroll height and compare with last scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                logger.info(f"New page height: {new_height}")
                
                if new_height == last_height:
                    # Try once more with a longer wait
                    logger.info("No new content loaded, waiting longer...")
                    time.sleep(random.uniform(3.0, 5.0))
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    logger.info(f"New page height after longer wait: {new_height}")
                    
                    if new_height == last_height:
                        # If still no new tweets, we've reached the end
                        logger.info("No new content after longer wait, ending scroll")
                        break
                
                last_height = new_height
            
            logger.info(f"Finished scraping. Total tweets scraped: {len(tweets)}")
            return tweets
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}", exc_info=True)
            return []
    
    def _extract_tweet_data(self, tweet_element):
        """
        Extract data from a tweet element.
        
        Args:
            tweet_element: Selenium WebElement representing a tweet
            
        Returns:
            dict: Tweet data or None if extraction failed
        """
        try:
            # Get tweet ID from URL
            try:
                link_element = tweet_element.find_element(By.CSS_SELECTOR, "a[href*='/status/']")
                tweet_url = link_element.get_attribute("href")
                tweet_id = tweet_url.split("/status/")[1].split("?")[0]
                logger.debug(f"Extracted tweet ID: {tweet_id}")
            except NoSuchElementException:
                logger.warning("Could not find tweet URL/ID")
                tweet_id = "unknown"
            
            # Get tweet text
            try:
                text_element = tweet_element.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']")
                text = text_element.text
                logger.debug(f"Extracted tweet text: {text[:30]}...")
            except NoSuchElementException:
                logger.warning("Could not find tweet text")
                text = ""
            
            # Get timestamp
            try:
                time_element = tweet_element.find_element(By.CSS_SELECTOR, "time")
                timestamp = time_element.get_attribute("datetime")
                logger.debug(f"Extracted timestamp: {timestamp}")
            except NoSuchElementException:
                logger.warning("Could not find tweet timestamp")
                timestamp = ""
            
            # Get engagement stats
            stats = {}
            try:
                # Try to find reply count
                reply_element = tweet_element.find_element(By.CSS_SELECTOR, "div[data-testid='reply']")
                reply_text = reply_element.text
                stats["replies"] = int(reply_text) if reply_text.isdigit() else 0
            except (NoSuchElementException, ValueError) as e:
                logger.warning(f"Could not extract reply count: {e}")
                stats["replies"] = 0
                
            try:
                # Try to find retweet count
                retweet_element = tweet_element.find_element(By.CSS_SELECTOR, "div[data-testid='retweet']")
                retweet_text = retweet_element.text
                stats["retweets"] = int(retweet_text) if retweet_text.isdigit() else 0
            except (NoSuchElementException, ValueError) as e:
                logger.warning(f"Could not extract retweet count: {e}")
                stats["retweets"] = 0
                
            try:
                # Try to find like count
                like_element = tweet_element.find_element(By.CSS_SELECTOR, "div[data-testid='like']")
                like_text = like_element.text
                stats["likes"] = int(like_text) if like_text.isdigit() else 0
            except (NoSuchElementException, ValueError) as e:
                logger.warning(f"Could not extract like count: {e}")
                stats["likes"] = 0
            
            logger.debug(f"Extracted stats: {stats}")
            
            # Get media links (images, videos)
            media_links = []
            has_video = False
            video_preview_url = None
            try:
                # Check for images
                media_elements = tweet_element.find_elements(By.CSS_SELECTOR, "img[src*='media']")
                for media in media_elements:
                    src = media.get_attribute("src")
                    if src and "profile" not in src and src not in media_links:
                        media_links.append(src)
                
                # Check for videos
                video_elements = tweet_element.find_elements(By.CSS_SELECTOR, "div[data-testid='videoPlayer']")
                if video_elements:
                    has_video = True
                    # Try to find video preview image
                    try:
                        # Look for the video thumbnail/preview image
                        video_preview = video_elements[0].find_element(By.CSS_SELECTOR, "img")
                        if video_preview:
                            video_preview_url = video_preview.get_attribute("src")
                            if video_preview_url:
                                # Convert relative URLs to absolute URLs if needed
                                if video_preview_url.startswith('/'):
                                    base_url = self.driver.current_url.split('/status')[0]
                                    video_preview_url = f"{base_url}{video_preview_url}"
                                
                                # First, remove any existing entry of this URL without the prefix
                                if video_preview_url in media_links:
                                    media_links.remove(video_preview_url)
                                # Add with the prefix
                                media_links.append(f"video_preview:{video_preview_url}")
                                logger.debug(f"Found video preview image: {video_preview_url}")
                    except NoSuchElementException:
                        logger.debug("Could not find video preview image")
                    
                logger.debug(f"Extracted {len(media_links)} media links")
            except Exception as e:
                logger.warning(f"Error extracting media links: {e}")
            
            return {
                "id": tweet_id,
                "url": tweet_url if 'tweet_url' in locals() else "",
                "text": text,
                "timestamp": timestamp,
                "stats": stats,
                "media": media_links,
                "has_video": has_video,
                "has_media": len(media_links) > 0 or has_video,
                "video_preview_url": video_preview_url,
                "source": "x.com"
            }
        except Exception as e:
            logger.error(f"Error extracting tweet data: {e}", exc_info=True)
            return None
    
    def _extract_nitter_tweet_data(self, tweet_element):
        """
        Extract data from a nitter tweet element.
        
        Args:
            tweet_element: Selenium WebElement representing a tweet on nitter.net
            
        Returns:
            dict: Tweet data or None if extraction failed
        """
        try:
            # Get tweet ID and URL
            try:
                link_element = tweet_element.find_element(By.CSS_SELECTOR, ".tweet-link")
                tweet_url = link_element.get_attribute("href")
                tweet_id = tweet_url.split("/")[-1]
                logger.debug(f"Extracted tweet ID from nitter: {tweet_id}")
            except NoSuchElementException:
                logger.warning("Could not find tweet URL/ID on nitter")
                tweet_id = "unknown"
                tweet_url = ""
            
            # Get tweet text
            try:
                text_element = tweet_element.find_element(By.CSS_SELECTOR, ".tweet-content")
                text = text_element.text
                logger.debug(f"Extracted tweet text from nitter: {text[:30]}...")
            except NoSuchElementException:
                logger.warning("Could not find tweet text on nitter")
                text = ""
            
            # Get timestamp
            try:
                time_element = tweet_element.find_element(By.CSS_SELECTOR, ".tweet-date a")
                timestamp = time_element.get_attribute("title")
                logger.debug(f"Extracted timestamp from nitter: {timestamp}")
            except NoSuchElementException:
                logger.warning("Could not find tweet timestamp on nitter")
                timestamp = ""
            
            # Get engagement stats
            stats = {}
            try:
                # Try to find stats
                stats_element = tweet_element.find_element(By.CSS_SELECTOR, ".tweet-stats")
                stats_text = stats_element.text
                
                # Parse stats
                for stat in stats_text.split('\n'):
                    if 'repl' in stat.lower():
                        stats["replies"] = int(stat.split()[0]) if stat.split()[0].isdigit() else 0
                    elif 'retweet' in stat.lower():
                        stats["retweets"] = int(stat.split()[0]) if stat.split()[0].isdigit() else 0
                    elif 'like' in stat.lower():
                        stats["likes"] = int(stat.split()[0]) if stat.split()[0].isdigit() else 0
                
                logger.debug(f"Extracted stats from nitter: {stats}")
            except (NoSuchElementException, ValueError, IndexError) as e:
                logger.warning(f"Could not extract stats from nitter: {e}")
                stats = {"replies": 0, "retweets": 0, "likes": 0}
            
            # Get media links
            media_links = []
            video_preview_url = None
            try:
                # Try multiple selectors to find images
                # First try the original selector
                media_elements = tweet_element.find_elements(By.CSS_SELECTOR, ".still-image")
                
                # If no images found, try alternative selectors
                if not media_elements:
                    media_elements = tweet_element.find_elements(By.CSS_SELECTOR, ".attachment img")
                
                if not media_elements:
                    media_elements = tweet_element.find_elements(By.CSS_SELECTOR, ".media-image img")
                
                if not media_elements:
                    media_elements = tweet_element.find_elements(By.CSS_SELECTOR, ".tweet-body img:not(.emoji):not(.profile-pic)")
                
                # Extract src attributes from found elements
                for media in media_elements:
                    src = media.get_attribute("src")
                    if src and "profile" not in src and src not in media_links:
                        # Convert relative URLs to absolute URLs if needed
                        if src.startswith('/'):
                            base_url = self.driver.current_url.split('/status')[0]
                            src = f"{base_url}{src}"
                        media_links.append(src)
                
                # Also check for video elements
                video_elements = tweet_element.find_elements(By.CSS_SELECTOR, ".video-container")
                if video_elements:
                    # Mark that this tweet has a video
                    has_video = True
                    
                    # Try to find video preview image
                    try:
                        # Look for the video thumbnail/preview image
                        video_preview = video_elements[0].find_element(By.CSS_SELECTOR, "img")
                        if video_preview:
                            video_preview_url = video_preview.get_attribute("src")
                            if video_preview_url:
                                # Convert relative URLs to absolute URLs if needed
                                if video_preview_url.startswith('/'):
                                    base_url = self.driver.current_url.split('/status')[0]
                                    video_preview_url = f"{base_url}{video_preview_url}"
                                
                                # First, remove any existing entry of this URL without the prefix
                                if video_preview_url in media_links:
                                    media_links.remove(video_preview_url)
                                # Add with the prefix
                                media_links.append(f"video_preview:{video_preview_url}")
                                logger.debug(f"Found video preview image: {video_preview_url}")
                    except NoSuchElementException:
                        # Try alternative selectors for video thumbnails
                        try:
                            video_preview = video_elements[0].find_element(By.CSS_SELECTOR, ".poster")
                            if video_preview:
                                video_preview_url = video_preview.get_attribute("src")
                                if video_preview_url:
                                    # Convert relative URLs to absolute URLs if needed
                                    if video_preview_url.startswith('/'):
                                        base_url = self.driver.current_url.split('/status')[0]
                                        video_preview_url = f"{base_url}{video_preview_url}"
                                    
                                    # First, remove any existing entry of this URL without the prefix
                                    if video_preview_url in media_links:
                                        media_links.remove(video_preview_url)
                                    # Add with the prefix
                                    media_links.append(f"video_preview:{video_preview_url}")
                                    logger.debug(f"Found video preview image: {video_preview_url}")
                        except NoSuchElementException:
                            logger.debug("Could not find video preview image")
                else:
                    has_video = False
                
                logger.debug(f"Extracted {len(media_links)} media links from nitter")
            except Exception as e:
                logger.warning(f"Error extracting media links from nitter: {e}")
                has_video = False
            
            return {
                "id": tweet_id,
                "url": tweet_url,
                "text": text,
                "timestamp": timestamp,
                "stats": stats,
                "media": media_links,
                "has_video": has_video,
                "has_media": len(media_links) > 0 or has_video,
                "video_preview_url": video_preview_url,
                "source": "nitter"
            }
        except Exception as e:
            logger.error(f"Error extracting tweet data from nitter: {e}", exc_info=True)
            return None
    
    def save_tweets(self, tweets, output_file=None):
        """
        Save tweets to a JSON file.
        
        Args:
            tweets (list): List of tweet dictionaries
            output_file (str, optional): Output file path
            
        Returns:
            str: Path to the saved file
        """
        if not tweets:
            logger.warning("No tweets to save")
            return None
        
        # Generate output filename if not provided
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{self.username}_tweets_{timestamp}.json"
        
        # Ensure the output file is in the tweets folder
        if not os.path.isabs(output_file):
            output_file = os.path.join(TWEETS_FOLDER, output_file)
        
        # Create the tweets folder if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Prepare data
        data = {
            "username": self.username,
            "scraped_at": datetime.now().isoformat(),
            "tweet_count": len(tweets),
            "tweets": tweets
        }
        
        # Save to file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Successfully saved tweets to {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Error saving tweets: {e}", exc_info=True)
            return None
    
    def close(self):
        """Close the WebDriver"""
        logger.info("Closing WebDriver")
        try:
            self.driver.quit()
            logger.info("WebDriver closed successfully")
        except Exception as e:
            logger.error(f"Error closing WebDriver: {e}")

def main():
    parser = argparse.ArgumentParser(description='Scrape tweets from an X.com profile')
    parser.add_argument('username', help='X.com username without the @ symbol')
    parser.add_argument('--max', type=int, help='Maximum number of tweets to scrape')
    parser.add_argument('--output', help='Output filename')
    parser.add_argument('--visible', action='store_true', help='Run in visible mode (not headless)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--email', help='X.com login email')
    parser.add_argument('--password', help='X.com login password')
    parser.add_argument('--no-profile', action='store_true', help='Do not use a persistent Chrome profile')
    
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")
    
    logger.info(f"Starting tweet scraper for user: {args.username}")
    
    # Get password if email is provided but password is not
    password = args.password
    if args.email and not args.password:
        password = getpass.getpass("Enter your X.com password: ")
    
    scraper = TweetScraper(
        args.username, 
        headless=not args.visible, 
        max_tweets=args.max,
        email=args.email,
        password=password,
        use_profile=not args.no_profile
    )
    
    try:
        tweets = scraper.scrape_tweets()
        if tweets:
            scraper.save_tweets(tweets, args.output)
        else:
            logger.warning("No tweets were scraped.")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        scraper.close()

if __name__ == "__main__":
    main()