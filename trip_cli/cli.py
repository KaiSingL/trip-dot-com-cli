#!/usr/bin/env python3
"""Trip.com CLI — agent-native hotel search for Trip.com."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta

import click

from trip_cli.core.format import render_hotel_table
from trip_cli.core.search import (
    HotelSearchRequest,
    run_hotel_search,
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
@click.option("--currency", default="USD", show_default=True, help="Preferred currency for prices (e.g. USD, SGD, JPY).")
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


@cli.command("url")
@click.option("--city", required=True)
@click.option("--checkin", default=None)
@click.option("--checkout", default=None)
def build_url(city: str, checkin: str | None, checkout: str | None) -> None:
    """Print the Trip.com search URL for the given parameters (for debugging / verification)."""
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


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
