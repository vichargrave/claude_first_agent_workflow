#!/usr/bin/env python3
"""
Fetch customer review data for a competitor from G2 and Capterra via Serper.dev.

Usage:
    python tools/get_reviews.py --name "Competitor Name"
"""

import argparse
import json
import os
import re
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def serper_search(query: str, api_key: str, num: int = 5) -> list[dict]:
    response = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "num": num},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("organic", [])


def extract_rating(text: str) -> float | None:
    # Match patterns like "4.5 out of 5", "4.5/5", "Rating: 4.5"
    patterns = [
        r"(\d+\.?\d*)\s*(?:out of|/)\s*5",
        r"rating[:\s]+(\d+\.?\d*)",
        r"(\d+\.?\d*)\s*stars?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            val = float(match.group(1))
            if 0 <= val <= 5:
                return val
    return None


def extract_review_count(text: str) -> int | None:
    patterns = [
        r"([\d,]+)\s+reviews?",
        r"([\d,]+)\s+ratings?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def get_reviews(name: str, api_key: str) -> dict:
    queries = [
        f'"{name}" reviews site:g2.com',
        f'"{name}" reviews site:capterra.com',
        f'"{name}" pros cons user reviews 2024',
    ]

    snippets: list[str] = []
    rating: float | None = None
    review_count: int | None = None
    sources: list[str] = []

    for query in queries:
        print(f"Searching reviews: {query}")
        try:
            results = serper_search(query, api_key, num=5)
        except Exception as e:
            print(f"  Search failed: {e}", file=sys.stderr)
            continue

        for hit in results:
            snippet = hit.get("snippet", "").strip()
            title = hit.get("title", "")
            link = hit.get("link", "")

            if snippet and snippet not in snippets:
                snippets.append(snippet)

            if link not in sources:
                sources.append(link)

            # Try to extract rating/count from snippet or title
            combined = f"{title} {snippet}"
            if rating is None:
                rating = extract_rating(combined)
            if review_count is None:
                review_count = extract_review_count(combined)

        if len(snippets) >= 6:
            break

    # Parse pros/cons themes from snippets using keyword heuristics
    pros_keywords = ["easy", "intuitive", "great", "excellent", "love", "fast", "simple", "helpful", "reliable", "good"]
    cons_keywords = ["difficult", "expensive", "slow", "missing", "lack", "hard", "confusing", "limited", "poor", "bad"]

    pros: list[str] = []
    cons: list[str] = []

    for snippet in snippets:
        lower = snippet.lower()
        if any(kw in lower for kw in pros_keywords) and len(pros) < 5:
            pros.append(snippet[:200])
        elif any(kw in lower for kw in cons_keywords) and len(cons) < 5:
            cons.append(snippet[:200])

    return {
        "name": name,
        "rating": rating,
        "review_count": review_count,
        "pros": pros,
        "cons": cons,
        "raw_snippets": snippets[:10],
        "sources": sources[:5],
    }


def main():
    parser = argparse.ArgumentParser(description="Fetch competitor reviews via Serper.dev")
    parser.add_argument("--name", required=True, help="Competitor name")
    parser.add_argument("--output-dir", default=".tmp")
    args = parser.parse_args()

    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        print("Error: SERPER_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    data = get_reviews(args.name, api_key)

    os.makedirs(args.output_dir, exist_ok=True)
    safe_name = re.sub(r"[^a-z0-9]", "_", args.name.lower())
    output_path = os.path.join(args.output_dir, f"reviews_{safe_name}.json")

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Saved → {output_path}")
    if data["rating"]:
        print(f"  Rating: {data['rating']}/5 ({data['review_count'] or 'unknown'} reviews)")


if __name__ == "__main__":
    main()
