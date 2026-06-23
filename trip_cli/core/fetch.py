"""Playwright-based fetcher for Trip.com hotel search results.

This provides a resilient way to extract structured hotel data from the dynamic Trip.com hotel list pages.
"""

from __future__ import annotations

import re
import time
from typing import Any

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from trip_cli.config import get_trip_domain


def _parse_price_text(text: str | None) -> float | None:
    """Extract numeric price from various formats like '$128', 'USD 128', '128.00'."""
    if not text:
        return None
    import re

    m = re.search(r"[\d,]+(\.\d+)?", text.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def fetch_hotels(
    search_url: str,
    city: str,
    checkin: str,
    checkout: str,
    max_results: int = 10,
    sort: str = "price",
    timeout_ms: int = 60000,
) -> list[dict[str, Any]]:
    """Perform hotel search on Trip.com by interacting with the search form.

    This is more reliable than guessing list URLs (which often redirect).
    Returns raw hotel records.
    """
    results: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )
        page = context.new_page()

        try:
            # Always prefer direct URL (regional Trip.com with slug-id works reliably)
            target = search_url or f"https://{get_trip_domain()}/hotels/"
            page.goto(target, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(1800)

            # Scroll progressively to load lazy hotel list
            for _ in range(5):
                page.mouse.wheel(0, 1400)
                page.wait_for_timeout(550)

            # Extract hotel cards - strong signal is real /hotel-detail- links on SERP
            extracted = page.evaluate(
                """(maxRes) => {
                    const out = [];
                    let anchors = Array.from(document.querySelectorAll('a[href*="/hotel-detail-"]'));
                    if (anchors.length < 3) {
                        anchors = Array.from(document.querySelectorAll('a[href*="/hotels/"][href*="detail"]'));
                    }
                    anchors.slice(0, 60).forEach(a => {
                        if (out.length >= maxRes) return;
                        const name = (a.innerText || a.textContent || "").trim().replace(/\\s+/g, " ").slice(0, 95);
                        if (!name || /hotels in |see more|view all|list your/i.test(name)) return;

                        // Climb a couple levels to locate sibling price / rating info
                        let container = a.parentElement;
                        for (let i=0; i<3 && container; i++) {
                            if (container.querySelector && container.querySelector("[class*='price' i]")) break;
                            container = container.parentElement;
                        }
                        const priceEl = container && container.querySelector ? container.querySelector("[class*='price' i], [class*='Price'], [class*='amount']") : null;
                        const ratingEl = container && container.querySelector ? container.querySelector("[class*='score' i], [class*='rating'], [class*='review']") : null;

                        const m = a.href.match(/detail-(\\d+)/i);
                        out.push({
                            name,
                            price_text: priceEl ? priceEl.innerText.trim() : null,
                            rating_text: ratingEl ? ratingEl.innerText.trim() : null,
                            url: a.href,
                            hotel_id: m ? m[1] : null,
                        });
                    });
                    return out;
                }""",
                max_results,
            )

            for item in extracted or []:
                results.append({
                    "name": item.get("name"),
                    "price_text": item.get("price_text"),
                    "rating_text": item.get("rating_text"),
                    "url": item.get("url"),
                    "hotel_id": item.get("hotel_id"),
                })

            # Last resort broad scrape for hotel detail links that have good names
            if len(results) < 2:
                detail_links = page.eval_on_selector_all(
                    'a[href*="/hotel-detail-"]',
                    """els => els.map(e => ({href: e.href, text: (e.innerText||e.textContent||"").trim().slice(0,80)}))"""
                )
                for l in detail_links:
                    if l["text"] and len(l["text"]) > 5 and not l["text"].lower().startswith("hotel"):
                        results.append({"name": l["text"], "url": l["href"]})

        except PlaywrightTimeout as e:
            raise RuntimeError(
                f"Timeout scraping Trip.com hotel search for '{city}'. "
                f"Check dates (must be future) and internet. Underlying: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to scrape Trip.com hotels: {e}") from e
        finally:
            context.close()
            browser.close()

    # dedup + trim
    seen = set()
    dedup = []
    for r in results:
        key = (r.get("name") or "").strip().lower()[:50]
        if key and key not in seen:
            seen.add(key)
            dedup.append(r)
    return dedup[:max_results]


def fetch_destination_suggestions(query: str, max_results: int = 8):
    """Search for destinations, cities or areas on Trip.com."""
    suggestions = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
            locale="en-US",
        )
        page = context.new_page()

        try:
            page.goto(f"https://{get_trip_domain()}/hotels/", timeout=30000)
            page.wait_for_timeout(800)

            # Find and interact with the destination input
            input_selectors = [
                "input[placeholder*='Where' i]",
                "input[placeholder*='city' i]",
                "input[placeholder*='destination' i]",
            ]
            inp = None
            for sel in input_selectors:
                try:
                    candidate = page.locator(sel).first
                    if candidate.count() > 0:
                        inp = candidate
                        break
                except:
                    continue

            if inp:
                inp.click()
                inp.fill(query)
                page.wait_for_timeout(1600)  # Let suggestions load

                # Extract suggestions using JS
                suggestions = page.evaluate(
                    f"""() => {{
                        const results = [];
                        const selectors = [
                            '[class*="suggest"]',
                            '[class*="search-result"]',
                            '[role="option"]',
                            '.city-item',
                            '[data-id]',
                            '[class*="result-item"]'
                        ];
                        let nodes = [];
                        selectors.forEach(s => {{
                            nodes = nodes.concat(Array.from(document.querySelectorAll(s)));
                        }});
                        nodes.slice(0, 15).forEach(el => {{
                            const text = (el.innerText || el.textContent || '').trim().split('\\n')[0].slice(0, 90);
                            if (!text || text.length < 3) return;
                            const href = el.getAttribute('href') || (el.querySelector('a') ? el.querySelector('a').getAttribute('href') : '');
                            const idMatch = (href || '').match(/list-(\\d+)/i) || (href || '').match(/detail-(\\d+)/i);
                            results.push({{
                                name: text,
                                id: idMatch ? idMatch[1] : null,
                                type: href && href.includes('hotel') ? 'hotel' : 'destination',
                            }});
                        }});
                        // Dedup by name
                        const seen = new Set();
                        return results.filter(r => {{
                            if (seen.has(r.name)) return false;
                            seen.add(r.name);
                            return true;
                        }}).slice(0, {max_results});
                    }}"""
                )
        except Exception as e:
            # Fallback to empty on error
            suggestions = []
        finally:
            context.close()
            browser.close()

    return suggestions or []


def fetch_hotel_details(hotel_id: str, currency: str = "HKD", city: str | None = None):
    """Fetch detailed information for a single hotel by its ID.
    If city is provided, uses city-prefixed path (e.g. bangkok-hotel-detail-xxx) which is required to avoid 404.
    """
    domain = get_trip_domain()
    if city:
        from trip_cli.core.search import resolve_city
        info = resolve_city(city)
        cslug = info.get("slug", city.strip().lower().replace(" ", "-"))
        url = f"https://{domain}/hotels/{cslug}-hotel-detail-{hotel_id}/?curr={currency}"
    else:
        # Bare form often 404s on Trip.com; prefer passing --city or use full URL from search results
        url = f"https://{domain}/hotels/hotel-detail-{hotel_id}/?curr={currency}"

    details = {"hotel_id": hotel_id, "url": url, "currency": currency}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        page = context.new_page()

        try:
            page.goto(url, timeout=45000)
            page.wait_for_timeout(2200)
            page.mouse.wheel(0, 600)  # load more content
            page.wait_for_timeout(800)

            details = page.evaluate(
                """(hotelId) => {
                    const getText = (sel) => {
                        const el = document.querySelector(sel);
                        return el ? el.innerText.trim().replace(/\\s+/g, ' ').slice(0, 600) : null;
                    };
                    const getList = (sel) => {
                        return Array.from(document.querySelectorAll(sel))
                            .map(e => e.innerText.trim())
                            .filter(t => t.length > 1 && t.length < 80)
                            .slice(0, 25);
                    };

                    const name = getText('h1') || getText('[class*="hotelName"], [class*="title"]');
                    const rating = getText('[class*="score"], [class*="ratingScore"]');
                    const reviewCount = getText('[class*="review"], [class*="reviewsCount"]');

                    const address = getText('[class*="address"], [class*="location"], .map-info');
                    const desc = getText('.description, [class*="intro"], [class*="about-hotel"]');

                    const amenities = getList('[class*="amenity"], .facility-item, [class*="facility"], [class*="service"]');

                    return {
                        hotel_id: hotelId,
                        name: name,
                        rating: rating,
                        review_count: reviewCount,
                        address: address,
                        description: desc,
                        amenities: amenities,
                        url: window.location.href
                    };
                }""",
                hotel_id,
            )
        except PlaywrightTimeout as e:
            details["error"] = f"Timeout loading hotel details: {e}"
        except Exception as e:
            details["error"] = str(e)
        finally:
            context.close()
            browser.close()

    return details
