"""Output formatting and normalization for Trip.com hotel data."""

from __future__ import annotations

import re
from typing import Any


def _to_usd(price_text: str | None, currency: str = "HKD") -> float | None:
    """Very rough conversion stub. For real use, integrate rates or use Trip's currency selection."""
    if not price_text:
        return None
    val = None
    m = re.search(r"[\d,]+(\.\d+)?", price_text.replace(",", ""))
    if m:
        try:
            val = float(m.group(0))
        except ValueError:
            val = None

    if val is None:
        return None

    # Naive: assume displayed is already in selected curr or USD. For CLI we just label it.
    return round(val, 2)


def normalize_hotel(raw: dict[str, Any]) -> dict[str, Any]:
    """Turn a raw scraped dict into a clean, agent-friendly hotel record."""
    price_text = raw.get("price_text") or raw.get("price")
    price_usd = _to_usd(price_text)

    rating = raw.get("rating_text") or raw.get("rating")
    if isinstance(rating, str):
        m = re.search(r"(\d+(\.\d+)?)", rating)
        rating = float(m.group(1)) if m else None
    try:
        rating = float(rating) if rating else None
    except (TypeError, ValueError):
        rating = None

    stars = raw.get("stars")
    name = raw.get("name") or raw.get("hotel_name") or "Unknown Hotel"
    name_str = name if isinstance(name, str) else str(name)

    # Parse stars from name if present (★ or count)
    if not stars or stars is None:
        star_match = re.search(r"(\d)\s*★|★{1,5}", name_str)
        if star_match:
            stars = int(star_match.group(1)) if star_match.group(1) else len(star_match.group(0))
        else:
            stars = None

    # Clean name: remove some emoji noise if wanted but keep useful
    clean_name = re.sub(r"\s*\u2605+\s*", " ", name_str).strip()

    return {
        "rank": None,
        "name": clean_name,
        "price_text": price_text,
        "price_usd": price_usd,
        "currency": raw.get("currency", "HKD"),
        "rating": rating,
        "stars": stars,
        "location": raw.get("location") or raw.get("area"),
        "hotel_id": raw.get("hotel_id"),
        "url": raw.get("url"),
    }


def render_hotel_table(data: dict[str, Any]) -> str:
    """Pretty human readable table."""
    lines = []
    q = data.get("query", {})
    summary = data.get("summary", {})
    hotels = data.get("hotels", [])

    lines.append("Trip.com Hotel Search")
    lines.append(f"  City: {q.get('city')}  |  {q.get('checkin')} → {q.get('checkout')}")
    lines.append(f"  Guests: {q.get('adults')} adults, {q.get('children')} children | Rooms: 1+")
    if summary.get("cheapest_usd"):
        lines.append(f"  Cheapest seen: ~${summary['cheapest_usd']}")
    lines.append(f"  Results: {summary.get('count', len(hotels))}")
    if summary.get("search_url"):
        lines.append(f"  View: {summary['search_url']}")
    lines.append("")

    if not hotels:
        lines.append("No hotels found. Try broadening dates or city name.")
        return "\n".join(lines)

    # Table header
    header = f"{'#':>2}  {'PRICE':>8}  {'RATING':>6}  {'STARS':>5}  {'NAME':<38}  LOCATION"
    lines.append(header)
    lines.append("-" * len(header))

    for i, h in enumerate(hotels, 1):
        price = f"${h.get('price_usd')}" if h.get("price_usd") else (h.get("price_text") or "—")
        rating = f"{h.get('rating'):.1f}" if h.get("rating") else "—"
        stars = "★" * (h.get("stars") or 0) if h.get("stars") else "—"
        name = (h.get("name") or "")[:38]
        loc = (h.get("location") or "")[:25]
        lines.append(f"{i:>2}  {price:>8}  {rating:>6}  {stars:>5}  {name:<38}  {loc}")

    lines.append("")
    lines.append("Tip: Use --json for machine-readable output.")
    return "\n".join(lines)
