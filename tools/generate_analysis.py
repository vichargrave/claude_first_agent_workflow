#!/usr/bin/env python3
"""
Synthesize competitor research data into a structured analysis using Claude.

Usage:
    python tools/generate_analysis.py --company-config config/company.json --data-dir .tmp/
"""

import argparse
import json
import os
import sys
from glob import glob

import anthropic
from dotenv import load_dotenv

load_dotenv()

ANALYSIS_PROMPT = """You are a strategic business analyst. I'm providing you with research data about a SaaS company and its competitors. Produce a thorough, actionable competitor analysis.

## My Company
{company_json}

## Competitor Research
{competitor_data}

---

Produce a JSON response with EXACTLY this structure (no markdown fences, just raw JSON):

{{
  "executive_summary": "3-4 sentence overview of the competitive landscape and your company's position",
  "market_overview": "1-2 paragraphs describing the market dynamics, key trends, and competitive intensity",
  "competitor_profiles": [
    {{
      "name": "Competitor name",
      "url": "https://...",
      "positioning": "1-2 sentences on how they position themselves",
      "target_customer": "Who they're targeting",
      "strengths": ["strength 1", "strength 2", "strength 3"],
      "weaknesses": ["weakness 1", "weakness 2"],
      "pricing_summary": "How they price (tiers, price points if known)",
      "review_sentiment": "Summary of customer sentiment from reviews",
      "threat_level": "High | Medium | Low"
    }}
  ],
  "feature_comparison": {{
    "features": ["Feature A", "Feature B", "Feature C"],
    "matrix": [
      {{
        "entity": "Your Company",
        "scores": {{"Feature A": "Yes", "Feature B": "Partial", "Feature C": "No"}}
      }}
    ]
  }},
  "opportunities": [
    {{
      "title": "Opportunity title",
      "description": "What this opportunity is and why it exists",
      "action": "Specific thing to do or build"
    }}
  ],
  "threats": [
    {{
      "title": "Threat title",
      "description": "What makes this a threat",
      "mitigation": "How to respond"
    }}
  ],
  "recommendations": [
    {{
      "priority": 1,
      "title": "Recommendation title",
      "rationale": "Why this matters",
      "next_step": "Concrete first action"
    }}
  ]
}}

For the feature_comparison matrix, include your company as the first row, then each competitor. Use "Yes", "No", or "Partial" for each feature score.

Base all analysis strictly on the provided data. If data is missing for a competitor, note it rather than fabricating details."""


def load_competitor_data(data_dir: str) -> list[dict]:
    competitors = []
    scraped_files = glob(os.path.join(data_dir, "scraped_*.json"))
    for path in scraped_files:
        with open(path) as f:
            scraped = json.load(f)

        name = scraped.get("name", "Unknown")
        safe_name = os.path.basename(path).replace("scraped_", "reviews_")
        reviews_path = os.path.join(data_dir, safe_name)

        reviews = {}
        if os.path.exists(reviews_path):
            with open(reviews_path) as f:
                reviews = json.load(f)

        competitors.append({
            "scraped": scraped,
            "reviews": reviews,
        })

    return competitors


def main():
    parser = argparse.ArgumentParser(description="Generate competitor analysis via Claude")
    parser.add_argument("--company-config", default="config/company.json")
    parser.add_argument("--data-dir", default=".tmp")
    parser.add_argument("--output", default=".tmp/analysis.json")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    with open(args.company_config) as f:
        company = json.load(f)

    competitors = load_competitor_data(args.data_dir)
    if not competitors:
        print(f"Error: No scraped competitor data found in {args.data_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing {len(competitors)} competitors with Claude...")

    prompt = ANALYSIS_PROMPT.format(
        company_json=json.dumps(company, indent=2),
        competitor_data=json.dumps(competitors, indent=2),
    )

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    try:
        analysis = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Warning: Could not parse Claude response as JSON: {e}", file=sys.stderr)
        print("Saving raw response instead.", file=sys.stderr)
        analysis = {"raw_response": raw}

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"Analysis saved → {args.output}")
    if "competitor_profiles" in analysis:
        print(f"  {len(analysis['competitor_profiles'])} competitor profiles generated")
    if "recommendations" in analysis:
        print(f"  {len(analysis['recommendations'])} recommendations")


if __name__ == "__main__":
    main()
