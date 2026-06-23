"""Optional end-to-end tests that hit real Trip.com.

Run with:
    $env:TRIP_RUN_LIVE='1'
    python -m pytest trip_cli/tests/test_e2e.py -v
"""

import os

import pytest

from trip_cli.core.search import HotelSearchRequest, run_hotel_search

pytestmark = pytest.mark.skipif(
    os.environ.get("TRIP_RUN_LIVE") != "1",
    reason="Set TRIP_RUN_LIVE=1 to run live scraping tests",
)


class TestLiveHotelSearch:
    def test_singapore_live(self):
        req = HotelSearchRequest(
            city="Singapore",
            checkin="2026-08-10",
            checkout="2026-08-13",
            adults=2,
            max_results=3,
        )
        result = run_hotel_search(req)

        assert result["search_url"]
        assert len(result["hotels"]) >= 1
        assert result["cheapest"] is not None

        first = result["hotels"][0]
        assert first["name"]
        assert "url" in first
        # Price may be high or low, just ensure it's a number or None (handled upstream)
        assert first.get("price_usd") is None or isinstance(first["price_usd"], (int, float))

    def test_tokyo_live(self):
        req = HotelSearchRequest(
            city="Tokyo",
            checkin="2026-09-05",
            checkout="2026-09-08",
            max_results=2,
        )
        result = run_hotel_search(req)
        assert len(result["hotels"]) > 0
        assert "tokyo" in result["search_url"].lower()
