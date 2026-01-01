#!/usr/bin/env python3
"""
Automated Acquire.com scraper with Chrome startup and login
"""
import os
import sys
import json
import uuid
import time
import psycopg2
import subprocess
from urllib.parse import urlparse, urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests

# -----------------------
# CONFIG
# -----------------------

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "acquire_agents",
    "user": "acquire_user",
    "password": "acquire_pass",
}

MARKETPLACE = "acquire.com"

# Stable namespace UUID for business_id generation
BUSINESS_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")

# -----------------------
# HELPERS
# -----------------------

def is_chrome_running():
    """Check if Chrome is running on port 9222"""
    try:
        print("Checking if Chrome is running on port 9222...", file=sys.stderr)
        response = requests.get("http://127.0.0.1:9222/json/version", timeout=5)
        is_running = response.status_code == 200
        print(f"Chrome running check: {is_running}", file=sys.stderr)
        return is_running
    except Exception as e:
        print(f"Chrome check failed: {e}", file=sys.stderr)
        return False

def start_chrome():
    """Start Chrome with remote debugging"""
    user_data_dir = os.path.expanduser("~/chrome-debug")

    # Ensure user data directory exists
    os.makedirs(user_data_dir, exist_ok=True)

    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    cmd = [
        chrome_path,
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--disable-default-apps",
        "--disable-sync",
        "--disable-translate",
        "--hide-crash-restore-bubble",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding"
    ]

    print("Starting Chrome with remote debugging...", file=sys.stderr)
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    # Wait for Chrome to start
    for i in range(30):  # Wait up to 30 seconds
        if is_chrome_running():
            print("Chrome started successfully", file=sys.stderr)
            return True
        time.sleep(1)

    raise Exception("Failed to start Chrome within 30 seconds")

def navigate_to_all_listing(driver):
    """Navigate to the all-listing page where business listings are located"""
    print("Current URL before navigation:", driver.current_url, file=sys.stderr)

    # Always navigate to the all-listing page - this is where the business listings are
    print("Navigating to all-listing page...", file=sys.stderr)
    driver.get("https://app.acquire.com/all-listing")

    # Wait for the page to load
    try:
        WebDriverWait(driver, 15).until(
            lambda driver: "all-listing" in driver.current_url or "listing" in driver.current_url
        )
        print("Successfully navigated to all-listing page", file=sys.stderr)
        print("Final URL:", driver.current_url, file=sys.stderr)
    except Exception as e:
        print(f"Warning: Could not verify all-listing URL, continuing anyway", file=sys.stderr)
        print(f"Current URL: {driver.current_url}, Error: {e}", file=sys.stderr)

    # Scroll through the page to load all lazy content
    print("Scrolling through all-listing page to load all business listings...", file=sys.stderr)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 4);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(3)
    print("Finished scrolling - all business listings should be loaded", file=sys.stderr)

def login_to_acquire(driver):
    """Login to acquire.com"""
    email = os.getenv("ACQUIRE_EMAIL")
    password = os.getenv("ACQUIRE_PASSWORD")

    if not email or not password:
        raise Exception("ACQUIRE_EMAIL and ACQUIRE_PASSWORD environment variables must be set")

    print("Starting fresh Chrome session - navigating to acquire.com login...", file=sys.stderr)

    # Navigate to login page
    driver.get("https://app.acquire.com/login")
    time.sleep(3)  # Give it time to load/redirect
    print(f"Current URL after navigation: {driver.current_url}", file=sys.stderr)

    # Check if we got redirected to browse (already logged in)
    current_url = driver.current_url
    if "browse" in current_url and "login" not in current_url:
        print("Already logged in - redirected to browse page", file=sys.stderr)
        return  # Skip login, go directly to navigation

    # If we're still on login page, proceed with login
    if "login" in current_url:
        print("On login page - proceeding with login", file=sys.stderr)

        # Wait for email input field
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[placeholder*='email' i]"))
            )
        except:
            print("No email input field found - might already be logged in", file=sys.stderr)
            return

    else:
        print("Unexpected page after login navigation - checking if logged in", file=sys.stderr)
        return

    # Find and fill email field
    email_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='email'], input[name='email']")
    if not email_inputs:
        # Try alternative selectors
        email_inputs = driver.find_elements(By.CSS_SELECTOR, "input[placeholder*='email' i], input[placeholder*='Email' i]")
        if not email_inputs:
            raise Exception("Could not find email input field")

    email_inputs[0].send_keys(email)

    # Find and fill password field
    password_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password'], input[name='password']")
    if not password_inputs:
        raise Exception("Could not find password input field")

    password_inputs[0].send_keys(password)

    # Find and click login button
    login_buttons = driver.find_elements(By.CSS_SELECTOR, "button[type='submit']")
    if not login_buttons:
        # Try finding buttons by text content
        login_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Sign') or contains(text(), 'Log') or contains(text(), 'Login')]")
        if not login_buttons:
            # Try pressing Enter on password field
            password_inputs[0].send_keys("\n")
        else:
            login_buttons[0].click()
    else:
        login_buttons[0].click()

    # Wait for login to complete
    try:
        print("Waiting for login to complete...", file=sys.stderr)
        WebDriverWait(driver, 15).until(EC.url_contains("app.acquire.com"))
        print("Login successful", file=sys.stderr)
    except Exception as e:
        # Check if we're still on login page
        current_url = driver.current_url
        print(f"Login wait failed. Current URL: {current_url}, Error: {e}", file=sys.stderr)
        if "login" in current_url:
            raise Exception("Login may have failed - still on login page")

    # Wait 10 seconds after login before navigating to allow session to stabilize
    print("Waiting 10 seconds for session to stabilize...", file=sys.stderr)
    time.sleep(10)
    print("Current URL before navigation:", driver.current_url, file=sys.stderr)

    # Navigate to all-listing page after login
    navigate_to_all_listing(driver)

def extract_hrefs(driver, url):
    """Extract business listing URLs with source=marketplace from current page"""
    # Note: url parameter is kept for compatibility but we're working with current page
    print("Extracting business URLs from current page...", file=sys.stderr)

    # Wait a bit for any dynamic content to load
    time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    hrefs = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]

        # Only process relative URLs (starting with /)
        if href and href.startswith('/'):
            # Parse the URL to check query parameters
            parsed = urlparse(href)
            query_params = dict(q.split('=', 1) for q in parsed.query.split('&') if '=' in q) if parsed.query else {}

            # Only include URLs with source=marketplace and startup path
            if (query_params.get('source') == 'marketplace' and
                parsed.path.startswith('/startup/')):
                full_url = urljoin("https://app.acquire.com", href)  # Use base URL since we're on browse
                hrefs.add(full_url)

    print(f"Found {len(hrefs)} business listing URLs", file=sys.stderr)
    return sorted(hrefs)

def extract_public_info_text(driver, url):
    """Extract public info text from a listing page"""
    driver.get(url)

    # Wait for the public-info-block to appear
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CLASS_NAME, "public-info-block"))
    )

    # Small delay for lazy content
    time.sleep(1)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    blocks = soup.find_all(class_="public-info-block")
    text_blocks = []

    for block in blocks:
        text = block.get_text(separator="\n", strip=True)
        if text:
            text_blocks.append(text)

    return "\n\n---\n\n".join(text_blocks)

def generate_business_id(listing_url: str) -> str:
    """Deterministically generate a stable UUID per unique listing URL"""
    return str(uuid.uuid5(BUSINESS_NAMESPACE, listing_url))

def get_existing_urls():
    """Get all existing URLs from database"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT listing_url FROM raw_listings")
    existing_urls = {row[0] for row in cursor.fetchall()}

    cursor.close()
    conn.close()

    return existing_urls

def insert_raw_listings(data):
    """Insert scraped data into database"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    insert_sql = """
        INSERT INTO raw_listings (
            business_id,
            marketplace,
            listing_url,
            scrape_timestamp,
            raw_html,
            raw_text
        )
        VALUES (%s, %s, %s, NOW(), %s, %s)
        ON CONFLICT (business_id, listing_url) DO NOTHING
    """

    inserted_count = 0
    for url, raw_text in data.items():
        if raw_text:  # Only insert if we have content
            business_id = generate_business_id(url)
            cursor.execute(
                insert_sql,
                (
                    business_id,
                    MARKETPLACE,
                    url,
                    None,  # raw_html
                    raw_text,
                )
            )
            inserted_count += 1

    conn.commit()
    cursor.close()
    conn.close()

    return inserted_count

def main():
    """Main scraping function"""
    try:
        # Start Chrome programmatically with remote debugging
        print("Starting Chrome programmatically...", file=sys.stderr)
        chrome_started = start_chrome()
        if not chrome_started:
            raise Exception("Failed to start Chrome")
        # Give Chrome a moment to fully initialize
        time.sleep(3)
        # Verify Chrome is running
        if not is_chrome_running():
            raise Exception("Chrome started but is not responding on port 9222")

        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

        # Create driver with timeout handling
        print("Attempting to connect to Chrome WebDriver...", file=sys.stderr)
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print("Successfully connected to Chrome remote debugging session", file=sys.stderr)

            # Set reasonable timeouts to prevent hanging
            driver.set_page_load_timeout(30)  # 30 seconds for page loads
            driver.implicitly_wait(10)  # 10 seconds for element finding

            # Check current tabs/pages
            try:
                tabs = driver.window_handles
                print(f"Chrome has {len(tabs)} tabs open", file=sys.stderr)
                current_url = driver.current_url
                print(f"Current tab URL: {current_url}", file=sys.stderr)
            except Exception as tab_e:
                print(f"Could not check tabs: {tab_e}", file=sys.stderr)

        except Exception as e:
            print(f"Failed to create WebDriver: {e}", file=sys.stderr)
            raise Exception(f"Chrome WebDriver connection failed: {e}")

        try:
                    # Since we start Chrome fresh, perform login (will auto-detect if already logged in)
            print("Fresh Chrome session started - checking login status...", file=sys.stderr)
            login_to_acquire(driver)

            # Now navigate to listings page regardless of login status
            navigate_to_all_listing(driver)

            # Get all listing URLs from current page (should be browse with listings)
            print("Extracting business URLs from current page", file=sys.stderr)
            all_urls = extract_hrefs(driver, "")  # Empty string since we're using current page
            print(f"Found {len(all_urls)} potential listing URLs", file=sys.stderr)

            # Get existing URLs from database
            existing_urls = get_existing_urls()
            print(f"Found {len(existing_urls)} URLs already in database", file=sys.stderr)

            # Filter out URLs we already have
            new_urls = [url for url in all_urls if url not in existing_urls]
            print(f"Need to scrape {len(new_urls)} new URLs", file=sys.stderr)

            # Scrape new URLs
            results = {}
            success_count = 0
            error_count = 0

            for i, url in enumerate(new_urls, 1):
                try:
                    print(f"[{i}/{len(new_urls)}] Scraping: {url}", file=sys.stderr)
                    text = extract_public_info_text(driver, url)
                    results[url] = text
                    success_count += 1
                except Exception as e:
                    print(f"❌ Failed on {url}: {e}", file=sys.stderr)
                    results[url] = None
                    error_count += 1

            # Insert into database
            inserted_count = insert_raw_listings(results)

            result = {
                "success": True,
                "message": "Scraping completed successfully",
                "stats": {
                    "total_urls_found": len(all_urls),
                    "already_exist": len(existing_urls),
                    "scraped": success_count,
                    "failed": error_count,
                    "inserted": inserted_count,
                }
            }

        finally:
            driver.quit()

    except Exception as e:
        result = {
            "success": False,
            "message": f"Scraping failed: {str(e)}",
            "stats": {
                "total_urls_found": 0,
                "already_exist": 0,
                "scraped": 0,
                "failed": 0,
                "inserted": 0,
            }
        }

    # Output JSON result
    print(json.dumps(result))

if __name__ == "__main__":
    main()
