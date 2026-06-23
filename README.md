# trip-cli

Agent-native command-line interface for searching hotels on Trip.com.

Inspired by the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) methodology and similar tools like `gflight`.

## Features

- Search hotels by city with flexible dates and guest counts
- Structured JSON output (`--json`) designed for AI agents and automation
- Human-readable tables by default
- No official API required — uses public web data via Playwright
- Cross-platform (primarily tested on Windows + PowerShell)

## Installation

```powershell
# Clone or navigate to the project
cd C:\dev\trip-dot-com-cli

# Create a virtual environment (recommended)
python -m venv .venv

# Activate it
.\.venv\Scripts\Activate.ps1

# Install the package in editable mode
pip install -e .

# Install Playwright browser (one-time)
playwright install chromium
```

### Run the CLI

You can run it in several ways:

```powershell
# Using the convenient launcher
.\scripts\trip-cli.cmd --help

# Or directly via Python module (always works)
python -m trip_cli --help

# Convenience alias (add to your profile)
function trip-cli { python -m trip_cli @args }
trip-cli --help
```

## Quick Examples

### Basic hotel search

```powershell
trip-cli hotel search --city "Singapore" --checkin 2026-07-15 --checkout 2026-07-18
```

### Agent-friendly JSON output

```powershell
trip-cli --json hotel search `
  --city Tokyo `
  --checkin 2026-09-10 `
  --checkout 2026-09-13 `
  --adults 2 `
  --max-results 5 `
  --sort price
```

### Build a direct Trip.com URL

```powershell
trip-cli url --city "Bangkok" --checkin 2026-08-05 --checkout 2026-08-08
```

## Command Reference

### `hotel search`

Search for hotels.

### `hotel details <hotel-id>`

Get rich details for one hotel (supports `--currency`):

```powershell
trip-cli hotel details 687474
trip-cli --json hotel details 687474 --currency SGD
```

### `destination search <query>`

Find cities or areas (helps with better matching):

```powershell
trip-cli destination search "tokyo"
trip-cli --json destination search "bali"
```

**Required:**
- `--city` — City or destination name (e.g. "Singapore", "Tokyo", "New York")

**Options:**
| Flag              | Description                              | Default     |
|-------------------|------------------------------------------|-------------|
| `--checkin`       | Check-in date (YYYY-MM-DD)               | ~14 days    |
| `--checkout`      | Check-out date (YYYY-MM-DD)              | ~3 nights   |
| `--adults`        | Number of adults                         | 2           |
| `--children`      | Number of children                       | 0           |
| `--rooms`         | Number of rooms                          | 1           |
| `--stars`         | Minimum star rating (`3`, `4`, `5`, `any`) | any       |
| `--max-price`     | Maximum price per night                  | —           |
| `--sort`          | Sort order (`price`, `rating`, `popularity`) | price    |
| `--max-results`   | Maximum number of results                | 10          |
| `--currency`      | Display currency (falls back to config)  | USD         |
| `--json`          | Output machine-readable JSON             | —           |

### `url`

Generate a Trip.com hotel search URL (useful for verification or sharing).

### Global Config

You can set persistent defaults that are used when you don't pass the flag:

```powershell
trip-cli config set currency SGD
trip-cli config set default-city "Singapore"

trip-cli config list
trip-cli config get currency
trip-cli config unset currency
```

Supported keys:
- `currency` — default for `hotel search` and `hotel details`
- (more coming)

## Output Formats

### Human-readable (default)

```
Trip.com Hotel Search
  City: Singapore  |  2026-07-15 → 2026-07-18
  Guests: 2 adults, 0 children | Rooms: 1+
  Cheapest seen: ~$1517
  Results: 3
  View: https://hk.trip.com/...

 #     PRICE   RATING  STARS  NAME
 1    $1517    9.7      5★   Raffles Singapore
 ...
```

### JSON (for agents / scripts)

```json
{
  "query": {
    "city": "Singapore",
    "checkin": "2026-07-15",
    "checkout": "2026-07-18",
    ...
  },
  "summary": {
    "count": 3,
    "cheapest_usd": 1517,
    "search_url": "..."
  },
  "hotels": [
    {
      "name": "Raffles Singapore",
      "price_usd": 1517,
      "price_text": "S$ 1517 /night",
      "rating": 9.7,
      "stars": 5,
      "hotel_id": "687474",
      "url": "https://hk.trip.com/hotels/..."
    }
  ]
}
```

## How It Works

Trip.com does not provide a public consumer API for hotel search.

This tool:
1. Constructs direct list URLs using known city slugs/IDs
2. Uses Playwright (headless Chromium) to load the page
3. Extracts hotel name, price, rating, stars, and links
4. Normalizes the data and returns clean JSON or a table

## Limitations

- Web scraping is inherently fragile — Trip.com may change their frontend at any time.
- Prices are "from" rates and may vary by room type, taxes, and availability.
- No support for booking through the CLI (search + discovery only).
- Some destinations may return fewer results depending on date range and inventory.

For production-scale use, consider commercial solutions such as Oxylabs Trip Scraper or Apify actors.

## Development

```powershell
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run the CLI
python -m trip_cli --help
```

## Testing

```powershell
# Install dev extras
pip install -e ".[dev]"

# Run unit tests (fast, no network)
python -m pytest trip_cli/tests -v

# Run live E2E tests (hits real Trip.com — use sparingly)
$env:TRIP_RUN_LIVE='1'
python -m pytest trip_cli/tests/test_e2e.py -v -s
```

Test layout:
- `test_core.py` — validation, URL building, normalization, table rendering
- `test_cli.py` — Click commands with mocked backend (CliRunner)
- `test_e2e.py` — optional real scraping tests (gated by `TRIP_RUN_LIVE=1`)

All core logic is unit-testable because `run_hotel_search` and `fetch_hotels` can be monkey-patched.

## Project Structure

```
trip-dot-com-cli/
├── README.md
├── setup.py
├── scripts/
│   ├── trip-cli.cmd
│   └── Invoke-TripCli.ps1
├── trip_cli/                 # Python package
│   ├── cli.py
│   ├── __init__.py
│   ├── __main__.py
│   ├── core/
│   │   ├── search.py
│   │   ├── fetch.py
│   │   └── format.py
│   └── tests/
│       ├── test_core.py
│       ├── test_cli.py
│       └── test_e2e.py
├── skills/
│   └── trip-cli/
│       └── SKILL.md          # Agent skill definition
└── trip_cli.egg-info/
```

## Agent Skill

A SKILL.md definition is available at:

```
skills/trip-cli/SKILL.md
```

This allows agent platforms to discover and use the CLI programmatically.

## Related Projects

- [CLI-Anything](https://github.com/HKUDS/CLI-Anything) — Framework for turning software into agent-native CLIs
- [gflight](https://github.com/...) — Similar agent-native CLI for Google Flights (reference implementation)

## License

This project follows the same license as the CLI-Anything ecosystem (see root LICENSE if present).

---

**Note:** This is an unofficial tool and is not affiliated with Trip.com. Use responsibly and respect Trip.com's terms of service.