# 🇺🇸 US Visa Appointment — Kenya (Nairobi)

![US Visa Appointment Kenya](assets/us_ke.png)

An automated bot that monitors the [US Visa appointment portal](https://ais.usvisa-info.com) and notifies you — or books automatically — when an earlier slot opens within your target date range.

## How It Works

1. **Playwright** launches a real Chrome browser to log in (bypasses bot detection and handles the iCheck policy checkbox automatically)
2. After login, the session cookie is handed off to **requests** for fast, lightweight API polling
3. Every few seconds, the bot checks available dates against your configured range
4. When a matching slot is found, it sends a **Telegram notification** and either books it or logs it (dry run)

## Features

- 🔐 Real browser login — no CAPTCHA or bot detection issues
- 📅 Configurable date range (min and target dates)
- 📱 Telegram notifications for start, found slot, booked, and errors
- 🔁 Auto re-login on session expiry
- 🛡️ Max retry circuit breaker to prevent infinite loops
- 🧪 Dry run mode — see what would be booked without actually booking
- 🪶 Lightweight polling via `requests` after initial login

## Requirements

- Python 3.10+
- Google Chrome installed
- A valid appointment on [ais.usvisa-info.com](https://ais.usvisa-info.com)

## Installation

```bash
# Clone the repo
git clone https://github.com/your-username/us-visa-appointment-ke.git
cd us-visa-appointment-ke

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Install Playwright's Chrome driver
playwright install chrome
```

## Configuration

Create a `.env` file in the project root (use `.env.example` as a template):

```env
# Your ais.usvisa-info.com credentials
EMAIL=your.email@example.com
PASSWORD=yourpassword

# Found in the URL: https://ais.usvisa-info.com/en-{COUNTRY_CODE}/
COUNTRY_CODE=ke

# Found in the URL when rescheduling:
# https://ais.usvisa-info.com/en-ke/niv/schedule/{SCHEDULE_ID}/continue_actions
SCHEDULE_ID=12345678

# Found in DevTools → Network tab when loading the reschedule page
# Look for: appointment/days/{FACILITY_ID}.json
FACILITY_ID=104

# Date range — bot only considers slots within this window (YYYY-MM-DD)
MIN_DATE=2026-05-23
TARGET_DATE=2026-06-05

# Polling interval in seconds (default: 10)
REFRESH_DELAY=10

# Max consecutive errors before the bot stops (default: 10)
MAX_RETRIES=10

# Telegram notifications (optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_IDS=your_chat_id
```

### Finding Your Config Values

| Variable | Where to find it |
|---|---|
| `COUNTRY_CODE` | URL after `/en-` — e.g. `ke` for Kenya, `fr` for France |
| `SCHEDULE_ID` | URL when rescheduling: `.../schedule/{SCHEDULE_ID}/...` |
| `FACILITY_ID` | DevTools → Network tab → look for `appointment/days/{FACILITY_ID}.json` on the reschedule page |
| `TELEGRAM_BOT_TOKEN` | Create a bot via [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_CHAT_IDS` | Your Telegram user ID — get it from [@userinfobot](https://t.me/userinfobot) |

## Usage

```bash
# Dry run — find slots but don't book (recommended first run)
python main.py -c 2026-09-15 --dry-run

# Live mode — actually book when a slot is found
python main.py -c 2026-09-15

# Headless mode — no browser window (good for servers)
python main.py -c 2026-09-15 --headless
```

### Arguments

| Flag | Required | Description |
|---|---|---|
| `-c`, `--current` | ✅ | Your currently booked appointment date (`YYYY-MM-DD`) |
| `-t`, `--target` | ❌ | Override `TARGET_DATE` from `.env` |
| `-m`, `--min` | ❌ | Override `MIN_DATE` from `.env` |
| `--dry-run` | ❌ | Log and notify without booking |
| `--headless` | ❌ | Run Chrome without a visible window |

## Example Output

```
[2026-05-23T10:00:00Z] Starting | current: 2026-09-15 | min: 2026-05-23 | target: 2026-06-05 | dry_run: False
[2026-05-23T10:00:01Z] Launching browser for login...
[2026-05-23T10:00:08Z] Checked policy checkbox via iCheck div
[2026-05-23T10:00:12Z] Login successful — landed on: .../groups/...
[2026-05-23T10:00:14Z] Session cookie extracted ✓
[2026-05-23T10:00:15Z] Dates API → 200
[2026-05-23T10:00:15Z] No dates in range (checked 39 total, earliest available: 2026-06-10)
[2026-05-23T10:00:25Z] Dates API → 200
[2026-05-23T10:00:25Z] 📅 Found 2 good date(s): ['2026-05-28', '2026-06-01'] — using 2026-05-28
[2026-05-23T10:00:26Z] Booking 2026-05-28 at 08:00...
[2026-05-23T10:00:27Z] ✅ Booked 2026-05-28 at 08:00
```

## Telegram Notifications

The bot sends messages for:
- 🟢 Bot started
- 📅 Earlier slot found within range
- ✅ Appointment successfully booked (or dry run result)
- ⚠️ Errors with retry count
- 🛑 Max retries hit — bot stopped

## Notes

- The bot re-logs in automatically when the session expires
- The `--current` date should be your existing booked appointment — the bot only looks for dates earlier than this and within your `MIN_DATE`/`TARGET_DATE` window
- Slots on this portal appear and disappear quickly — a 10-second polling interval is a good balance between responsiveness and avoiding rate limiting

## Disclaimer

This tool is for personal use to monitor your own appointment. Use responsibly and in accordance with the terms of service of the visa appointment system.

## License

MIT
