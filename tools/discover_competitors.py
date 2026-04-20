#!/usr/bin/env python3
"""
Discover competitors for a SaaS product using Serper.dev web search.

Usage:
    python tools/discover_competitors.py --company-config config/company.json
"""

import argparse
import json
import os
import sys
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()


def serper_search(query: str, api_key: str, num: int = 10) -> list[dict]:
    response = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "num": num},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("organic", [])


def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return domain.removeprefix("www.")
    except Exception:
        return url


SKIP_DOMAINS = {
    "g2.com", "capterra.com", "trustpilot.com", "getapp.com",
    "softwareadvice.com", "producthunt.com", "reddit.com",
    "quora.com", "linkedin.com", "twitter.com", "youtube.com",
    "cbinsights.com", "gartner.com", "forrester.com", "idc.com",
    "zoominfo.com", "crunchbase.com", "pitchbook.com",
    "saasadviser.co", "getkisi.com", "bouncewatch.com",
    "cybermagazine.com", "csoonline.com", "techradar.com",
    "pcmag.com", "techrepublic.com", "zdnet.com",
    "businessinsider.com", "forbes.com", "inc.com",
    "alternativeto.net", "slashdot.org", "sourceforge.net",
}


def discover_competitors(company_config: dict, api_key: str) -> list[dict]:
    name = company_config["name"]
    category = company_config.get("category", "software").rstrip("')")
    features = company_config.get("key_features", [])
    feature_hint = features[0].lower() if features else ""

    # Lead with category-level searches so unknown brands still yield real competitors
    queries = [
        f"best {category} tools platforms 2024 2025",
        f"top {category} companies",
        f"{feature_hint} {category} software" if feature_hint else f"{category} SaaS",
        f"{name} competitors alternatives",
    ]

    seen_domains: set[str] = set()
    results: list[dict] = []

    own_seeds = {name.lower().replace(" ", ""), name.lower().replace(" ", "-")}

    for query in queries:
        print(f"Searching: {query}")
        hits = serper_search(query, api_key, num=10)
        for hit in hits:
            url = hit.get("link", "")
            domain = extract_domain(url)

            if domain in SKIP_DOMAINS:
                continue
            if any(seed in domain for seed in own_seeds):
                continue
            if domain in seen_domains:
                continue
            # Skip domains that look like news/blog/info sites (no product)
            if any(domain.endswith(s) for s in [".org", ".gov", ".edu"]):
                continue

            seen_domains.add(domain)
            results.append({
                "name": hit.get("title", domain).split("|")[0].split("-")[0].strip(),
                "url": f"https://{domain}",
                "description": hit.get("snippet", ""),
                "domain": domain,
            })

        if len(results) >= 8:
            break

    # Also include any manually seeded competitors from config
    for seed in company_config.get("known_competitors", []):
        seed_domain = extract_domain(seed if seed.startswith("http") else f"https://{seed}")
        if seed_domain not in seen_domains:
            seen_domains.add(seed_domain)
            results.append({
                "name": seed_domain.split(".")[0].capitalize(),
                "url": f"https://{seed_domain}",
                "description": "Manually added competitor",
                "domain": seed_domain,
            })

    return results[:8]


def main():
    parser = argparse.ArgumentParser(description="Discover SaaS competitors via Serper.dev")
    parser.add_argument("--company-config", default="config/company.json")
    parser.add_argument("--output", default=".tmp/competitors.json")
    args = parser.parse_args()

    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        print("Error: SERPER_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    with open(args.company_config) as f:
        company = json.load(f)

    competitors = discover_competitors(company, api_key)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(competitors, f, indent=2)

    print(f"Found {len(competitors)} competitors → {args.output}")
    for c in competitors:
        print(f"  - {c['name']} ({c['url']})")


if __name__ == "__main__":
    main()
