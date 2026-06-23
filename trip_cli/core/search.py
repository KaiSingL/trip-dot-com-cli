"""Hotel search request models and runner for Trip.com."""

from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from trip_cli.core.fetch import fetch_hotels
from trip_cli.core.format import normalize_hotel

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass
class HotelSearchRequest:
    city: str
    checkin: str
    checkout: str
    adults: int = 2
    children: int = 0
    rooms: int = 1
    min_stars: int | None = None
    max_price: int | None = None
    sort: str = "price"
    max_results: int = 10
    currency: str = "USD"
    language: str = "en-us"

    def validate(self) -> None:
        if not self.city or len(self.city.strip()) < 2:
            raise ValueError("City must be a valid destination name (e.g. 'Singapore').")
        if not DATE_RE.match(self.checkin):
            raise ValueError("checkin must be YYYY-MM-DD")
        if not DATE_RE.match(self.checkout):
            raise ValueError("checkout must be YYYY-MM-DD")
        if self.adults < 1:
            raise ValueError("At least 1 adult required.")
        if self.rooms < 1:
            raise ValueError("At least 1 room required.")
        if self.max_results < 1:
            raise ValueError("max_results >= 1")
        if self.min_stars is not None and not (1 <= self.min_stars <= 5):
            raise ValueError("min_stars must be 1-5")


def build_search_url(city: str, checkin: str, checkout: str, **extra) -> str:
    """Build a working Trip.com hotel list search URL.
    Prefers regional domains and slug-hotels-list style that contain real hotel cards.
    """
    info = resolve_city(city)
    slug = info.get("slug", city.lower().replace(" ", "-"))
    cid = info.get("id")

    # sg. + slug-hotels-list or slug-hotels-list-{id}
    suffix = f"{slug}-hotels-list"
    if cid:
        suffix = f"{slug}-hotels-list-{cid}"

    base = f"https://sg.trip.com/hotels/{suffix}"

    params = {
        "checkin": checkin.replace("-", "/"),
        "checkout": checkout.replace("-", "/"),
        "curr": extra.get("currency", "USD"),
        "adult": str(extra.get("adults", 2)),
        "children": str(extra.get("children", 0)),
        "rooms": str(extra.get("rooms", 1)),
    }

    qs = urllib.parse.urlencode(params)
    return f"{base}/?{qs}"


def resolve_city(city: str) -> dict[str, Any]:
    """Lightweight city -> slug + optional trip city id map.
    The -{id} suffix on list pages often yields better/more complete SERPs.
    """
    c = city.strip().lower()
    known = {
        "singapore": {"display": "Singapore", "slug": "singapore", "id": "73"},
        "tokyo": {"display": "Tokyo", "slug": "tokyo", "id": "228"},
        "paris": {"display": "Paris", "slug": "paris", "id": "340"},
        "new york": {"display": "New York", "slug": "new-york", "id": "633"},
        "london": {"display": "London", "slug": "london", "id": "358"},
        "hong kong": {"display": "Hong Kong", "slug": "hong-kong", "id": "58"},
        "hongkong": {"display": "Hong Kong", "slug": "hong-kong", "id": "58"},
        "bangkok": {"display": "Bangkok", "slug": "bangkok", "id": "359"},
        "seoul": {"display": "Seoul", "slug": "seoul", "id": "237"},
        "dubai": {"display": "Dubai", "slug": "dubai", "id": "1174"},
        "bali": {"display": "Bali", "slug": "bali", "id": "1249"},
    }
    if c in known:
        return known[c]
    slug = c.replace(" ", "-").replace(",", "")
    return {"display": city.title(), "slug": slug}


def run_hotel_search(req: HotelSearchRequest) -> dict[str, Any]:
    """Execute the hotel search and return normalized structured data + search_url."""
    req.validate()

    city_info = resolve_city(req.city)
    url = build_search_url(
        req.city,   # build does its own resolve for id lookup etc.
        req.checkin,
        req.checkout,
        adults=req.adults,
        children=req.children,
        rooms=req.rooms,
        currency=req.currency,
    )

    raw_hotels = fetch_hotels(
        url,
        city=req.city,
        checkin=req.checkin,
        checkout=req.checkout,
        max_results=req.max_results,
        sort=req.sort,
    )

    hotels = []
    for h in raw_hotels:
        norm = normalize_hotel(h)
        hotels.append(norm)

    # Apply local post filters if needed (client side)
    if req.min_stars:
        hotels = [h for h in hotels if (h.get("stars") or 0) >= req.min_stars]
    if req.max_price:
        hotels = [h for h in hotels if (h.get("price_usd") or 999999) <= req.max_price]

    # Basic sort client side for cases where server sort not perfect
    if req.sort == "price":
        hotels.sort(key=lambda x: x.get("price_usd") or 999999)
    elif req.sort == "rating":
        hotels.sort(key=lambda x: -(x.get("rating") or 0))

    hotels = hotels[: req.max_results]

    cheapest = None
    if hotels:
        cheapest = min((h.get("price_usd") for h in hotels if h.get("price_usd")), default=None)

    return {
        "search_url": url,
        "query_city": req.city,
        "cheapest": cheapest,
        "hotels": hotels,
    }
