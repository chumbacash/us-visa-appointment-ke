# 🇺🇸 US Visa Appointment — Kenya (Nairobi)

![US Visa Appointment Kenya](assets/us_ke.png)

An automated bot that monitors the [US Visa appointment portal](https://ais.usvisa-info.com) and books the first available slot within your target date range — automatically.

> ✅ **Proven working** — successfully booked a June 4 appointment within hours of running.

---

## How It Works

1. **Playwright** launches a real Chrome browser to log in — handles bot detection and the iCheck policy checkbox automatically
2. After login, the session cookie is handed to **requests** for fast, lightweight API polling
3. Every 30 seconds the bot checks available dates against your configured range
4. Every 30 minutes the session is silently refreshed via `requests` — no browser needed
5. When a matching slot is found, it books immediately, sends a **Telegram notification**, and exits

---

## Features

- 🔐 Real browser login — bypasses CAPTCHA and bot detection
- ⚡ Fast `requests` polling after login — no browser overhead during monitoring
- 🔄 Automatic session refresh every 30 minutes without re-opening a browser
- 📅 Configurable date range via `.env` or CLI flags
- 📱 Telegram notifications — start, slot found, booked, errors
- 🔔 Audio alarm — 2-minute beep loop when a slot is found or booked (Windows)
- 🛡️ Max retry circuit breaker — stops cleanly after N consecutive failures
- 🧪 Dry run mode — test without actually booking

---

## Requirements

- Python 3.10+
- Google Chrome installed
- A valid existing appointment on [ais.usvisa-info.com](https://ais.usvisa-info.com)

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/Chumbacash/us-visa-appointment-ke.git
cd us-visa-appointment-ke

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright's Chrome driver
playwright install chrome

# 5. Copy and fill in your config
copy .env.example .env
```

---

## Configuration

Edit the `.env` file with your details:

```env
EMAIL=your.email@example.com
PASSWORD=yourpassword
COUNTRY_CODE=ke
SCHEDULE_ID=12345678
FACILITY_ID=104
MIN_DATE=2026-05-23
TARGET_DATE=2026-06-12
REFRESH_DELAY=30
MAX_RETRIES=10
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_IDS=your_chat_id
```

### Finding Your Values

| Variable | Where to find it |
|---|---|
| `COUNTRY_CODE` | URL after `/en-` — e.g. `ke` for Kenya |
| `SCHEDULE_ID` | URL when rescheduling: `.../schedule/{SCHEDULE_ID}/...` |
| `FACILITY_ID` | DevTools → Network tab → look for `appointment/days/{FACILITY_ID}.json` on the reschedule page |
| `MIN_DATE` | Earliest date you'd accept (inclusive) |
| `TARGET_DATE` | Latest date you'd accept (inclusive) |
| `TELEGRAM_BOT_TOKEN` | Create a bot via [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_IDS` | Your chat ID from [@userinfobot](https://t.me/userinfobot) |

---

## Usage

```bash
# Recommended: dry run first to confirm everything works
python main.py -c 2026-09-15 --dry-run

# Live mode — will actually book when a slot is found
python main.py -c 2026-09-15

# Headless — no visible browser window (good for leaving overnight)
python main.py -c 2026-09-15 --headless
```

### The `-c` flag

Pass a date **after** your target range as `-c`. The bot only looks for dates earlier than this value. Using your actual far-future booked date (e.g. `2026-09-15`) works perfectly — it won't interfere with the `MIN_DATE`/`TARGET_DATE` range.

### All Arguments

| Flag | Required | Description |
|---|---|---|
| `-c`, `--current` | ✅ | Your currently booked date — bot looks for anything earlier |
| `-t`, `--target` | ❌ | Override `TARGET_DATE` from `.env` |
| `-m`, `--min` | ❌ | Override `MIN_DATE` from `.env` |
| `--dry-run` | ❌ | Find and log slots without booking |
| `--headless` | ❌ | Run Chrome without a visible window |

---

## Example Output

```
[...] Starting | current: 2026-09-15 | min: 2026-05-23 | target: 2026-06-12 | dry_run: False
[...] Launching browser for login...
[...] Checked policy checkbox via iCheck div
[...] Login successful — landed on: .../groups/...
[...] Session ready ✓
[...] No dates in range (checked 35 total, earliest available: 2026-09-29)
[...] Session refreshed via requests ✓ (no browser needed)
[...] No dates in range (checked 35 total, earliest available: 2026-09-29)
[...] 📅 Found 1 good date(s): ['2026-06-04'] — using 2026-06-04
[...] Booking 2026-06-04 at 09:00...
[...] CSRF refreshed for booking ✓
[...] Booking response: 200 — .../appointment/instructions
[...] ✅ Booked 2026-06-04 at 09:00
```

---

## Telegram Notifications

| Event | Message |
|---|---|
| Bot started | 🟢 Started with current config |
| Slot found | 📅 Earlier slot found with date |
| Booked | ✅ Appointment successfully booked |
| Error | ⚠️ Error message with retry count |
| Max retries | 🛑 Bot stopped |

---

## Important Notes

- **Reschedule limit** — ais.usvisa-info.com allows a maximum of 4 reschedules. The bot uses one attempt per successful booking. Use `--dry-run` to test without consuming an attempt.
- **Slots disappear fast** — other people run similar tools. A 30-second poll interval is the sweet spot between responsiveness and avoiding rate limiting.
- **Session lifetime** — one Playwright login typically lasts 45–60 minutes. The bot refreshes silently via `requests` every 30 minutes and only re-opens the browser if that fails.
- **Audio alarm** — when a slot is found, a 2-minute beep alarm plays on Windows so you wake up even if asleep. The booking happens immediately in the background — do not press Ctrl+C.

---

## Disclaimer

This tool is for personal use to monitor your own appointment. Use responsibly and in accordance with the terms of service of the visa appointment system.

---

## License

MIT License — Copyright (c) 2026 [Chumbacash](https://github.com/Chumbacash)

See [LICENSE](LICENSE) for full details.
