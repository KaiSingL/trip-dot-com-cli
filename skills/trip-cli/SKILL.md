---
name: "trip-cli"
description: "Search Trip.com hotels from the terminal with JSON output for agents."
---

# trip-cli

Agent-native CLI for Trip.com hotels.

## Install

```powershell
cd trip-dot-com-cli
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m playwright install chromium
```

## Usage

```powershell
# Via module (always works)
python -m trip_cli --help

# Via launcher
.\scripts\trip-cli.cmd hotel search --city Singapore --checkin 2026-07-20 --checkout 2026-07-23

# JSON for agents
trip-cli --json hotel search --city Tokyo --checkin 2026-09-10 --checkout 2026-09-13 --max-results 5
```

### `hotel search`

Primary command.

```powershell
trip-cli hotel search --city "Singapore" --checkin 2026-07-15 --checkout 2026-07-18
```

Key flags:
- `--city` (required)
- `--checkin` / `--checkout` (YYYY-MM-DD)
- `--adults`, `--children`, `--rooms`
- `--stars` 3|4|5|any
- `--max-price`
- `--sort` price|rating
- `--max-results`
- `--currency`
- `--json`

### `url`

Emit the exact search URL to open in a browser for verification.

## JSON output shape

```json
{
  "query": { "city": "...", "checkin": "...", ... },
  "summary": { "count": 5, "cheapest_usd": 120, "search_url": "..." },
  "hotels": [
    {
      "name": "Hotel Foo",
      "price_usd": 128,
      "price_text": "S$ 172 /night",
      "rating": 8.9,
      "stars": 4,
      "hotel_id": "123456",
      "url": "https://sg.trip.com/..."
    }
  ]
}
```

## Notes for agents

- Always use `--json` when calling from code / LLM.
- Dates must be in the future.
- Prices shown are from Trip.com (may include taxes/fees or be "from" rates).
- No booking is performed by this CLI (search + details only).
- Scraping is best-effort and may need occasional tuning when Trip.com updates their frontend.

## Related

Follows patterns from gflight and the CLI-Anything methodology for turning web services into reliable agent tools.
