#!/usr/bin/env python3
"""
Scrape a competitor's homepage and pricing page for product/feature/pricing data.

Usage:
    python tools/scrape_competitor.py --url https://competitor.com --name "Competitor Name"
"""

import argparse
import json
import os
import re
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 15


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_page(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  Could not fetch {url}: {e}", file=sys.stderr)
        return None


def remove_boilerplate(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(["nav", "footer", "header", "script", "style", "noscript", "iframe"]):
        tag.decompose()


def extract_homepage_data(soup: BeautifulSoup) -> dict:
    remove_boilerplate(soup)

    # Headline: h1, then og:title
    headline = ""
    h1 = soup.find("h1")
    if h1:
        headline = clean_text(h1.get_text())
    if not headline:
        og = soup.find("meta", property="og:title")
        if og:
            headline = clean_text(og.get("content", ""))

    # Sub-headline / value prop
    subheadline = ""
    h2 = soup.find("h2")
    if h2:
        subheadline = clean_text(h2.get_text())

    # Features: look for feature-like sections (h3/h4 lists)
    features = []
    for tag in soup.find_all(["h3", "h4"]):
        text = clean_text(tag.get_text())
        if 3 < len(text) < 80 and text not in features:
            features.append(text)
    features = features[:15]

    # Meta description as fallback summary
    meta_desc = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta:
        meta_desc = clean_text(meta.get("content", ""))

    return {
        "headline": headline,
        "subheadline": subheadline,
        "meta_description": meta_desc,
        "features": features,
    }


def find_pricing_url(base_url: str, soup: BeautifulSoup) -> str | None:
    pricing_patterns = ["/pricing", "/plans", "/price", "/packages", "/subscribe"]
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if any(p in href for p in pricing_patterns):
            return urljoin(base_url, a["href"])
    # Try common paths directly
    for path in pricing_patterns:
        return urljoin(base_url, path)
    return None


def extract_pricing_data(soup: BeautifulSoup) -> str:
    remove_boilerplate(soup)

    # Grab all visible text from pricing-related containers
    pricing_text_parts = []

    # Look for price-like patterns: $, /mo, /month, /year, per user
    price_pattern = re.compile(r"(\$[\d,]+|\d+\s*/\s*mo|\bfree\b|per user|per month|per year|annual|monthly)", re.I)

    for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "span", "div"]):
        text = clean_text(tag.get_text())
        if price_pattern.search(text) and 3 < len(text) < 300:
            if text not in pricing_text_parts:
                pricing_text_parts.append(text)

    if not pricing_text_parts:
        # Fall back to all visible body text (truncated)
        body_text = clean_text(soup.get_text())
        pricing_text_parts = [body_text[:2000]]

    return "\n".join(pricing_text_parts[:30])


def scrape_competitor(name: str, url: str) -> dict:
    print(f"Scraping homepage: {url}")
    homepage_soup = fetch_page(url)

    if not homepage_soup:
        return {"name": name, "url": url, "error": "Could not fetch homepage"}

    homepage_data = extract_homepage_data(homepage_soup)

    # Find and scrape pricing page
    pricing_url = find_pricing_url(url, homepage_soup)
    pricing_text = ""
    if pricing_url:
        print(f"Scraping pricing: {pricing_url}")
        pricing_soup = fetch_page(pricing_url)
        if pricing_soup:
            pricing_text = extract_pricing_data(pricing_soup)

    return {
        "name": name,
        "url": url,
        "headline": homepage_data["headline"],
        "subheadline": homepage_data["subheadline"],
        "meta_description": homepage_data["meta_description"],
        "features": homepage_data["features"],
        "pricing_url": pricing_url or "",
        "pricing_text": pricing_text,
    }


def main():
    parser = argparse.ArgumentParser(description="Scrape competitor homepage and pricing")
    parser.add_argument("--url", required=True, help="Competitor homepage URL")
    parser.add_argument("--name", required=True, help="Competitor name")
    parser.add_argument("--output-dir", default=".tmp")
    args = parser.parse_args()

    data = scrape_competitor(args.name, args.url)

    os.makedirs(args.output_dir, exist_ok=True)
    safe_name = re.sub(r"[^a-z0-9]", "_", args.name.lower())
    output_path = os.path.join(args.output_dir, f"scraped_{safe_name}.json")

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved → {output_path}")


if __name__ == "__main__":
    main()
