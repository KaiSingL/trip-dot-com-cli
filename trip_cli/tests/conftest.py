"""Pytest fixtures for trip-cli tests."""

import pytest

MOCK_RAW_HOTELS = [
    {
        "name": "Raffles Singapore 📍 1 Beach Rd, Singapore ★★★★★ 9.7 (206 reviews)",
        "price_text": "S$ 450 /night",
        "rating_text": "9.7",
        "stars": None,
        "location": "Singapore",
        "hotel_id": "687474",
        "url": "https://sg.trip.com/hotels/singapore-hotel-detail-687474/raffles-singapore/",
    },
    {
        "name": "Grand Hyatt Singapore",
        "price_text": "USD 280",
        "rating_text": "8.8 (1,234 reviews)",
        "stars": 5,
        "location": "Singapore",
        "hotel_id": "12345",
        "url": "https://sg.trip.com/hotels/singapore-hotel-detail-12345/grand-hyatt/",
    },
    {
        "name": "Budget Inn",
        "price_text": "S$ 95",
        "rating_text": "7.2",
        "stars": None,
        "location": None,
        "hotel_id": "99999",
        "url": None,
    },
]

MOCK_SEARCH_RESULT = {
    "search_url": "https://sg.trip.com/hotels/singapore-hotels-list-73/?checkin=2026/07/15&checkout=2026/07/18&curr=USD",
    "query_city": "Singapore",
    "cheapest": 95.0,
    "hotels": [
        {
            "rank": None,
            "name": "Raffles Singapore",
            "price_text": "S$ 450 /night",
            "price_usd": 450.0,
            "currency": "USD",
            "rating": 9.7,
            "stars": 5,
            "location": "Singapore",
            "hotel_id": "687474",
            "url": "https://sg.trip.com/hotels/singapore-hotel-detail-687474/raffles-singapore/",
        },
        {
            "rank": None,
            "name": "Grand Hyatt Singapore",
            "price_text": "USD 280",
            "price_usd": 280.0,
            "currency": "USD",
            "rating": 8.8,
            "stars": 5,
            "location": "Singapore",
            "hotel_id": "12345",
            "url": "https://sg.trip.com/hotels/singapore-hotel-detail-12345/grand-hyatt/",
        },
    ],
}


@pytest.fixture
def mock_raw_hotels():
    return MOCK_RAW_HOTELS


@pytest.fixture
def mock_search_result():
    return MOCK_SEARCH_RESULT


@pytest.fixture
def mock_config(monkeypatch):
    """In-memory config for testing. Replaces the real config functions."""
    cfg = {"currency": "USD"}

    def fake_get(key, default=None):
        if key in cfg:
            return cfg[key]
        # Mimic real behavior: fall back to module DEFAULTS
        if key == "currency":
            return default or "USD"
        return default

    def fake_set(key, value):
        cfg[key] = value

    def fake_unset(key):
        cfg.pop(key, None)

    def fake_list():
        return cfg.copy()

    monkeypatch.setattr("trip_cli.cli.get_config_value", fake_get)
    monkeypatch.setattr("trip_cli.cli.set_config_value", fake_set)
    monkeypatch.setattr("trip_cli.cli.unset_config_value", fake_unset)
    monkeypatch.setattr("trip_cli.cli.list_config", fake_list)

    return cfg
