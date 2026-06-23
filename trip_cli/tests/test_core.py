"""Unit tests for core search and formatting logic."""

import pytest

from trip_cli.core.format import _to_usd, normalize_hotel, render_hotel_table
from trip_cli.core.search import (
    DATE_RE,
    HotelSearchRequest,
    build_search_url,
    resolve_city,
)


class TestResolveCity:
    def test_known_cities(self):
        assert resolve_city("Singapore") == {"display": "Singapore", "slug": "singapore", "id": "73"}
        assert resolve_city("Hong Kong")["id"] == "58"
        assert resolve_city("hongkong")["slug"] == "hong-kong"

    def test_unknown_city(self):
        result = resolve_city("Some Random Place")
        assert result["display"] == "Some Random Place"
        assert result["slug"] == "some-random-place"
        assert "id" not in result


class TestBuildSearchUrl:
    def test_basic_url(self):
        url = build_search_url("Singapore", "2026-07-15", "2026-07-18")
        assert "sg.trip.com" in url
        assert "singapore-hotels-list-73" in url
        assert "checkin=2026%2F07%2F15" in url
        assert "curr=USD" in url

    def test_unknown_city_url(self):
        url = build_search_url("Bali", "2026-08-01", "2026-08-05", currency="SGD")
        assert "bali-hotels-list-1249" in url
        assert "curr=SGD" in url


class TestHotelSearchRequest:
    def test_valid_request(self):
        req = HotelSearchRequest(
            city="Tokyo",
            checkin="2026-09-10",
            checkout="2026-09-13",
        )
        req.validate()  # Should not raise

    def test_invalid_city(self):
        req = HotelSearchRequest(city="A", checkin="2026-07-01", checkout="2026-07-04")
        with pytest.raises(ValueError, match="City must be a valid"):
            req.validate()

    def test_invalid_dates(self):
        req = HotelSearchRequest(city="Paris", checkin="07-01-2026", checkout="2026-07-04")
        with pytest.raises(ValueError, match="checkin must be YYYY-MM-DD"):
            req.validate()

    def test_invalid_adults(self):
        req = HotelSearchRequest(city="London", checkin="2026-07-01", checkout="2026-07-04", adults=0)
        with pytest.raises(ValueError, match="At least 1 adult"):
            req.validate()

    def test_invalid_min_stars(self):
        req = HotelSearchRequest(city="Dubai", checkin="2026-07-01", checkout="2026-07-04", min_stars=6)
        with pytest.raises(ValueError, match="min_stars must be 1-5"):
            req.validate()

    def test_date_regex(self):
        assert DATE_RE.match("2026-12-25")
        assert not DATE_RE.match("2026/12/25")


class TestNormalizeHotel:
    def test_full_data(self, mock_raw_hotels):
        norm = normalize_hotel(mock_raw_hotels[0])
        # Name cleaning removes star symbols but keeps other info
        assert "Raffles Singapore" in norm["name"]
        assert "9.7" in norm["name"] or norm.get("rating") == 9.7
        assert norm["price_usd"] == 450.0
        assert norm["rating"] == 9.7
        assert norm["stars"] == 5
        assert norm["hotel_id"] == "687474"

    def test_price_parsing(self):
        assert _to_usd("S$ 120 /night") == 120.0
        assert _to_usd("USD 89.50") == 89.5
        assert _to_usd(None) is None

    def test_stars_from_name(self):
        raw = {"name": "Nice Hotel ★★★★", "price_text": "$100"}
        norm = normalize_hotel(raw)
        assert norm["stars"] == 4

    def test_missing_fields(self):
        norm = normalize_hotel({"name": "Bare Hotel"})
        assert norm["price_usd"] is None
        assert norm["rating"] is None
        assert norm["stars"] is None


class TestRenderHotelTable:
    def test_empty_results(self):
        data = {"query": {"city": "Mars"}, "summary": {"count": 0}, "hotels": []}
        output = render_hotel_table(data)
        assert "No hotels found" in output
        assert "Mars" in output

    def test_with_results(self, mock_search_result):
        # The render expects a certain shape; simulate what CLI passes
        payload = {
            "query": {"city": "Singapore", "checkin": "2026-07-15", "checkout": "2026-07-18", "adults": 2},
            "summary": {"count": 2, "cheapest_usd": 280, "search_url": "https://..."},
            "hotels": mock_search_result["hotels"],
        }
        output = render_hotel_table(payload)
        assert "Trip.com Hotel Search" in output
        assert "Singapore" in output
        assert "$450" in output or "450.0" in output
        assert "9.7" in output
        assert "Tip: Use --json" in output
