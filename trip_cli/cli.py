#!/usr/bin/env python3
"""Trip.com CLI — agent-native hotel search for Trip.com."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta

import click

from trip_cli.core.format import render_hotel_table
from trip_cli.config import (
    get_config_value,
    set_config_value,
    unset_config_value,
    list_config,
)
from trip_cli.core.search import (
    HotelSearchRequest,
    run_hotel_search,
    search_destinations,
    get_hotel_details,
)

_json_output = False


def emit(data: dict, human_renderer) -> None:
    if _json_output:
        click.echo(json.dumps(data, indent=2, default=str))
        return
    click.echo(human_renderer(data))


def handle_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (RuntimeError, ValueError) as exc:
            if _json_output:
                click.echo(json.dumps({"error": str(exc), "type": type(exc).__name__}))
            else:
                click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def _default_dates():
    today = datetime.now().date()
    checkin = (today + timedelta(days=14)).strftime("%Y-%m-%d")
    checkout = (today + timedelta(days=17)).strftime("%Y-%m-%d")
    return checkin, checkout


@click.group()
@click.option("--json", "use_json", is_flag=True, help="Output machine-readable JSON for agents.")
def cli(use_json: bool) -> None:
    """Trip.com hotel search CLI (agent-native).

Run via:
  python -m trip_cli --help
  .\\scripts\\trip-cli.cmd hotel search --city Singapore ...
"""
    global _json_output
    _json_output = use_json


@cli.group()
def hotel() -> None:
    """Hotel search and details commands."""


@hotel.command("search")
@click.option("--city", required=True, help="City name or destination (e.g. 'Singapore', 'Tokyo', 'Paris').")
@click.option("--checkin", default=None, help="Check-in date (YYYY-MM-DD). Defaults to ~14 days from now.")
@click.option("--checkout", default=None, help="Check-out date (YYYY-MM-DD). Defaults ~3 nights.")
@click.option("--adults", default=2, show_default=True, help="Number of adults.")
@click.option("--children", default=0, show_default=True, help="Number of children.")
@click.option("--rooms", default=1, show_default=True, help="Number of rooms.")
@click.option("--stars", type=click.Choice(["3", "4", "5", "any"]), default="any", help="Minimum star rating filter.")
@click.option("--max-price", type=int, default=None, help="Max price per night (in local currency or USD).")
@click.option("--sort", type=click.Choice(["price", "rating", "distance", "popularity"]), default="price", show_default=True)
@click.option("--max-results", default=10, show_default=True, help="Limit number of results.")
@click.option("--currency", default=None, help="Preferred currency for prices (e.g. USD, SGD, JPY). Falls back to config.")
@handle_error
def hotel_search(
    city: str,
    checkin: str | None,
    checkout: str | None,
    adults: int,
    children: int,
    rooms: int,
    stars: str,
    max_price: int | None,
    sort: str,
    max_results: int,
    currency: str,
) -> None:
    """Search hotels on Trip.com."""
    if not checkin or not checkout:
        checkin, checkout = _default_dates()

    if currency is None:
        currency = get_config_value("currency", "USD")

    req = HotelSearchRequest(
        city=city,
        checkin=checkin,
        checkout=checkout,
        adults=adults,
        children=children,
        rooms=rooms,
        min_stars=None if stars == "any" else int(stars),
        max_price=max_price,
        sort=sort,
        max_results=max_results,
        currency=currency,
    )

    results = run_hotel_search(req)

    payload = {
        "query": {
            "city": city,
            "checkin": checkin,
            "checkout": checkout,
            "adults": adults,
            "children": children,
            "rooms": rooms,
            "currency": currency,
            "sort": sort,
        },
        "summary": {
            "count": len(results.get("hotels", [])),
            "cheapest_usd": results.get("cheapest"),
            "search_url": results.get("search_url"),
        },
        "hotels": results.get("hotels", []),
    }

    emit(payload, lambda d: render_hotel_table(d))


@hotel.command("details")
@click.argument("hotel_id")
@click.option("--currency", default=None, help="Preferred currency for prices (e.g. USD, SGD, JPY). Falls back to config.")
@click.option("--city", default=None, help="City slug for correct hotel detail URL (e.g. Bangkok, 'Kuala Lumpur'). Prevents 404 on direct links.")
@handle_error
def hotel_details(hotel_id: str, currency: str, city: str | None) -> None:
    """Get detailed information about a specific hotel."""
    if currency is None:
        currency = get_config_value("currency", "USD")

    details = get_hotel_details(hotel_id, currency, city=city)

    if _json_output:
        click.echo(json.dumps(details, indent=2, default=str))
        return

    click.echo(f"Hotel: {details.get('name', hotel_id)} (currency: {currency})")
    if details.get("rating"):
        click.echo(f"  Rating: {details['rating']} ({details.get('review_count', 'N/A')})")
    if details.get("address"):
        click.echo(f"  Address: {details['address']}")
    if details.get("amenities"):
        click.echo("  Key Amenities:")
        for a in details["amenities"][:10]:
            click.echo(f"    • {a}")
    if details.get("description"):
        desc = details["description"][:280] + "..." if len(details.get("description", "")) > 280 else details.get("description")
        click.echo(f"  Description: {desc}")
    click.echo(f"  Source: {details.get('url')}")


@cli.group()
def destination() -> None:
    """Destination and city lookup commands."""


@destination.command("search")
@click.argument("query")
@click.option("--limit", default=8, show_default=True)
@handle_error
def destination_search(query: str, limit: int) -> None:
    """Search for cities, areas or hotels by name."""
    results = search_destinations(query, limit)

    payload = {"query": query, "results": results}

    if _json_output:
        click.echo(json.dumps(payload, indent=2))
        return

    if not results:
        click.echo(f"No suggestions found for '{query}'.")
        return

    click.echo(f"Suggestions for '{query}':")
    for r in results:
        extra = f" (id={r.get('id')})" if r.get("id") else ""
        click.echo(f"  {r.get('name')}{extra}")


@cli.command("url")
@click.option("--city", required=True)
@click.option("--checkin", default=None)
@click.option("--checkout", default=None)
def build_url(city: str, checkin: str | None, checkout: str | None) -> None:
    """Print the Trip.com search URL for the given parameters (for debugging / verification).
    Uses the configured region (default hk.trip.com). Change with: trip-cli config set region sg
    """
    if not checkin or not checkout:
        checkin, checkout = _default_dates()
    from trip_cli.core.search import build_search_url

    url = build_search_url(city, checkin, checkout)
    click.echo(url)


@cli.command("version")
def version_cmd() -> None:
    """Show version."""
    from trip_cli import __version__

    click.echo(f"trip-cli {__version__}")


@cli.group()
def config() -> None:
    """View and modify global configuration."""


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a config value (e.g. currency USD)."""
    set_config_value(key, value)
    click.echo(f"Set {key} = {value}")


@config.command("get")
@click.argument("key")
def config_get(key: str) -> None:
    """Get a config value."""
    val = get_config_value(key)
    click.echo(f"{key} = {val}")


@config.command("list")
def config_list_cmd() -> None:
    """List all config values."""
    cfg = list_config()
    if not cfg:
        click.echo("No configuration set.")
        return
    for k, v in sorted(cfg.items()):
        click.echo(f"{k} = {v}")


@config.command("unset")
@click.argument("key")
def config_unset(key: str) -> None:
    """Remove a config value."""
    unset_config_value(key)
    click.echo(f"Unset {key}")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
