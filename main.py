#!/usr/bin/env python3

import os
import sys
import time
import argparse
import winsound
import requests
from datetime import datetime, timezone
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ─── Config ───────────────────────────────────────────────────────────────────

ENV_PATH = os.path.join(os.path.dirname(__file__), '..', '.env')
config = dotenv_values(ENV_PATH)

EMAIL         = config.get('EMAIL')
PASSWORD      = config.get('PASSWORD')
COUNTRY_CODE  = config.get('COUNTRY_CODE')
SCHEDULE_ID   = config.get('SCHEDULE_ID')
FACILITY_ID   = config.get('FACILITY_ID')
REFRESH_DELAY = int(config.get('REFRESH_DELAY', 30))
MAX_RETRIES   = int(config.get('MAX_RETRIES', 10))
MIN_DATE      = config.get('MIN_DATE')
TARGET_DATE   = config.get('TARGET_DATE')
TELEGRAM_TOKEN    = config.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_IDS = [c.strip() for c in config.get('TELEGRAM_CHAT_IDS', '').split(',') if c.strip()]

BASE_URL  = f"https://ais.usvisa-info.com/en-{COUNTRY_CODE}/niv"
SIGN_IN   = f"{BASE_URL}/users/sign_in"
APPT_URL  = f"{BASE_URL}/schedule/{SCHEDULE_ID}/appointment"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}Z] {msg}", flush=True)

def alarm(level='found'):
    # Plays a looping beep alarm for 2 minutes
    # level: 'found' = urgent, 'booked' = victory, 'error' = warning
    try:
        end_time = time.time() + 120  # 2 minutes
        if level == 'booked':
            while time.time() < end_time:
                for freq in [600, 800, 1000, 1200, 1000, 800]:
                    winsound.Beep(freq, 250)
        elif level == 'found':
            while time.time() < end_time:
                # Alternating high-low urgent pattern
                winsound.Beep(1200, 300)
                winsound.Beep(800, 300)
        elif level == 'error':
            while time.time() < end_time:
                winsound.Beep(400, 500)
                winsound.Beep(600, 500)
    except Exception:
        pass  # Non-Windows or audio unavailable — fail silently

def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_IDS:
        return
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
                timeout=10
            )
        except Exception as e:
            log(f"Telegram error: {e}")

def parse_args():
    parser = argparse.ArgumentParser(description='US Visa Appointment Bot')
    parser.add_argument('-c', '--current', required=True, help='Current booked date (YYYY-MM-DD)')
    parser.add_argument('-t', '--target',  default=TARGET_DATE, help='Target date upper bound')
    parser.add_argument('-m', '--min',     default=MIN_DATE,    help='Minimum acceptable date')
    parser.add_argument('--dry-run', action='store_true', help='Do not actually book')
    parser.add_argument('--headless', action='store_true', default=False, help='Run browser in headless mode')
    return parser.parse_args()

def validate_config():
    missing = [k for k, v in {
        'EMAIL': EMAIL, 'PASSWORD': PASSWORD, 'COUNTRY_CODE': COUNTRY_CODE,
        'SCHEDULE_ID': SCHEDULE_ID, 'FACILITY_ID': FACILITY_ID
    }.items() if not v]
    if missing:
        log(f"Missing required config: {', '.join(missing)}")
        sys.exit(1)

# ─── Playwright login — returns (cookie, csrf_token) ─────────────────────────

def playwright_login(headless=False):
    log("Launching browser for login...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",   # use installed Chrome, not bundled Chromium
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="en-US",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        log(f"Navigating to {SIGN_IN}")
        page.goto(SIGN_IN, wait_until="networkidle", timeout=30000)
        # Wait for email field to be ready
        page.wait_for_selector('#user_email', state='visible', timeout=15000)

        # Fill login form
        page.fill('#user_email', EMAIL)
        page.fill('#user_password', PASSWORD)

        # Check policy/terms checkbox — uses iCheck jQuery plugin
        # The real input is hidden behind a div overlay, must click the div
        try:
            # Click the iCheck div wrapper that sits on top of the real input
            page.locator('div.icheckbox').first.click()
            log("Checked policy checkbox via iCheck div")
        except Exception as e:
            log(f"iCheck div click failed: {e}, trying JS fallback...")
            try:
                # JS fallback: directly set checked and trigger iCheck's update
                page.evaluate("""
                    var cb = document.getElementById('policy_confirmed');
                    cb.checked = true;
                    if (window.$) $(cb).iCheck('check');
                """)
                log("Checked policy checkbox via JS")
            except Exception as e2:
                log(f"JS fallback also failed: {e2}")

        # Small pause to let checkbox state register
        page.wait_for_timeout(800)

        # Submit
        page.click('[name="commit"]')
        log("Login form submitted, waiting for redirect...")

        # Wait for redirect away from sign_in
        try:
            page.wait_for_url(lambda url: 'sign_in' not in url, timeout=15000)
            log(f"Login successful — landed on: {page.url}")
        except PlaywrightTimeout:
            # Try to grab error message
            try:
                error = page.locator('.alert, #flash_messages').first.inner_text()
            except Exception:
                error = "Unknown — still on sign_in page"
            browser.close()
            raise Exception(f"Login failed: {error}")

        # Navigate to appointment page to get a valid session state
        page.goto(APPT_URL, wait_until="networkidle", timeout=30000)

        # Extract _yatri_session cookie
        cookies = context.cookies()
        yatri = next((c['value'] for c in cookies if c['name'] == '_yatri_session'), None)
        if not yatri:
            browser.close()
            raise Exception("Could not extract _yatri_session cookie after login")

        # Extract CSRF token from page meta tag
        csrf = page.evaluate("() => document.querySelector('meta[name=\"csrf-token\"]')?.content")
        log(f"Session ready ✓")

        browser.close()
        return f"_yatri_session={yatri}", csrf

# ─── requests session built from Playwright cookie ───────────────────────────

def build_session(cookie, csrf):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Cookie": cookie,
        "X-CSRF-Token": csrf,
        "Referer": APPT_URL,
        "X-Requested-With": "XMLHttpRequest",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return session

# ─── Appointment API ──────────────────────────────────────────────────────────

def get_available_dates(session):
    url = f"{BASE_URL}/schedule/{SCHEDULE_ID}/appointment/days/{FACILITY_ID}.json?appointments[expedite]=false"
    resp = session.get(url, headers={"Accept": "application/json"}, timeout=15)

    if resp.status_code == 401:
        raise Exception("Session expired (401) — need to re-login")
    if resp.status_code != 200:
        raise Exception(f"Dates API error {resp.status_code}: {resp.text[:200]}")

    # Update cookie from response if rotated
    sc = resp.headers.get('set-cookie', '')
    if '_yatri_session=' in sc:
        import re
        m = re.search(r'_yatri_session=([^;]+)', sc)
        if m:
            session.headers.update({"Cookie": f"_yatri_session={m.group(1)}"})

    data = resp.json()
    if isinstance(data, dict) and data.get('error'):
        raise Exception(f"API error: {data['error']}")

    return [item['date'] for item in data]

def get_available_time(session, date):
    url = f"{BASE_URL}/schedule/{SCHEDULE_ID}/appointment/times/{FACILITY_ID}.json?date={date}&appointments[expedite]=false"
    resp = session.get(url, headers={"Accept": "application/json"}, timeout=15)
    if resp.status_code != 200:
        raise Exception(f"Times API error {resp.status_code}")
    data = resp.json()
    times = data.get('business_times') or data.get('available_times') or []
    return times[0] if times else None

def book(session, date, time_slot):
    resp = session.post(
        APPT_URL,
        data={
            'utf8': '✓',
            'authenticity_token': session.headers.get('X-CSRF-Token', ''),
            'confirmed_limit_message': '1',
            'use_consulate_appointment_capacity': 'true',
            'appointments[consulate_appointment][facility_id]': FACILITY_ID,
            'appointments[consulate_appointment][date]': date,
            'appointments[consulate_appointment][time]': time_slot,
            'appointments[asc_appointment][facility_id]': '',
            'appointments[asc_appointment][date]': '',
            'appointments[asc_appointment][time]': ''
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        allow_redirects=True,
        timeout=15
    )
    if resp.status_code not in (200, 302):
        raise Exception(f"Booking failed: {resp.status_code}")
    return True

def filter_dates(dates, current, min_date, target_date):
    good = []
    for d in dates:
        if d >= current:
            continue
        if min_date and d < min_date:
            continue
        if target_date and d > target_date:
            continue
        good.append(d)
    return sorted(good)

# ─── Main loop ────────────────────────────────────────────────────────────────

def main():
    validate_config()
    args = parse_args()

    current_date = args.current
    target_date  = args.target
    min_date     = args.min
    dry_run      = args.dry_run
    headless     = args.headless

    log(f"Starting | current: {current_date} | min: {min_date} | target: {target_date} | dry_run: {dry_run}")
    send_telegram(
        f"🟢 <b>Bot started</b>\nCurrent: {current_date}\n"
        f"Min: {min_date or 'None'}\nTarget: {target_date or 'None'}\n"
        f"Mode: {'DRY RUN' if dry_run else 'LIVE'}"
    )

    session = None
    retries = 0

    while True:
        try:
            if session is None:
                cookie, csrf = playwright_login(headless=headless)
                session = build_session(cookie, csrf)
                retries = 0

            dates = get_available_dates(session)

            if not dates:
                log("No dates available")
            else:
                good = filter_dates(dates, current_date, min_date, target_date)
                if not good:
                    log(f"No dates in range (checked {len(dates)} total, earliest available: {dates[0]})")
                else:
                    earliest = good[0]
                    log(f"📅 Found {len(good)} good date(s): {good} — using {earliest}")
                    alarm('found')
                    send_telegram(f"📅 <b>Earlier slot found</b>\nDate: {earliest}")

                    time_slot = get_available_time(session, earliest)
                    if not time_slot:
                        log(f"No time slots for {earliest}")
                    elif dry_run:
                        log(f"[DRY RUN] Would book {earliest} at {time_slot}")
                        alarm('found')
                        send_telegram(f"✅ <b>[DRY RUN] Would book</b>\nDate: {earliest}\nTime: {time_slot}")
                        sys.exit(0)
                    else:
                        log(f"Booking {earliest} at {time_slot}...")
                        book(session, earliest, time_slot)
                        log(f"✅ Booked {earliest} at {time_slot}")
                        alarm('booked')
                        send_telegram(f"✅ <b>Appointment booked</b>\nDate: {earliest}\nTime: {time_slot}")
                        sys.exit(0)

            time.sleep(REFRESH_DELAY)

        except KeyboardInterrupt:
            log("Stopped by user")
            sys.exit(0)
        except Exception as e:
            retries += 1
            log(f"Error (attempt {retries}/{MAX_RETRIES}): {e}")
            send_telegram(f"⚠️ <b>Error</b>\n{e}\nRetry {retries}/{MAX_RETRIES}")
            session = None  # force re-login next iteration

            if retries >= MAX_RETRIES:
                log("Max retries reached. Exiting.")
                alarm('error')
                send_telegram("🛑 <b>Max retries hit — bot stopped</b>")
                sys.exit(1)

            wait = 60 if '401' in str(e) or 'expired' in str(e).lower() else REFRESH_DELAY
            log(f"Waiting {wait}s before retry...")
            time.sleep(wait)

if __name__ == '__main__':
    main()
