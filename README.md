# Competitor Analysis Workflow

Generates a branded PDF competitor analysis report for your SaaS business. Discovers competitors, scrapes their websites and reviews, synthesizes insights with Claude AI, and outputs a polished report with your logo, colors, and typography.

## Setup

```bash
# Create and activate virtual environment
python -m venv venv && source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# macOS only — required for PDF generation
brew install pango

# Copy and fill in your API keys
cp .env.example .env
```

Edit `.env` and add:
```
ANTHROPIC_API_KEY=your_key_here
SERPER_API_KEY=your_key_here
```

## One-Time Configuration

**1. Fill in your company details** — edit `config/company.json`:
- `name`, `tagline`, `description`
- `category` — the market you compete in (e.g. `"AI penetration testing software"`)
- `key_features`, `pricing_tiers`, `strengths`
- `known_competitors` — optional seed list of competitor URLs

**2. Set your brand** — edit `config/brand.json`:
- Hex color codes for `primary_color`, `secondary_color`, `accent_color`
- Google Font names for `font_heading` and `font_body` (e.g. `"Inter"`, `"Poppins"`)

**3. Add your logo** — drop your file into `assets/logo.png` (PNG or SVG)

---

## Option A — Run with Claude Code (Recommended)

Open this project in [Claude Code](https://claude.ai/code) and say:

> **"Run the competitor analysis workflow"**

Claude will read `workflows/competitor_analysis.md` and execute all five steps automatically, handling errors and retries along the way.

You can also ask Claude to:
- "Re-run the analysis with updated competitor data"
- "Add [competitor name] to the analysis"
- "Regenerate the PDF with my new brand colors"

---

## Option B — Run from the Bash Command Line

Run from the repo root with the venv activated (`source venv/bin/activate`).

### Step 1 — Discover Competitors

```bash
python tools/discover_competitors.py
```

Output: `.tmp/competitors.json`

> **Note:** For niche or new brands, auto-discovery may return blog posts instead of product homepages. If that happens, manually edit `.tmp/competitors.json` with the correct competitor names and URLs, then continue to Step 2.

### Step 2 — Scrape Each Competitor

Run once per competitor found in Step 1:

```bash
python tools/scrape_competitor.py --url "https://competitor.com" --name "Competitor Name"
```

Output: `.tmp/scraped_<name>.json` per competitor

### Step 3 — Fetch Reviews

Run once per competitor, using the **same name** as Step 2:

```bash
python tools/get_reviews.py --name "Competitor Name"
```

Output: `.tmp/reviews_<name>.json` per competitor

### Step 4 — Generate Analysis

```bash
python tools/generate_analysis.py
```

Output: `.tmp/analysis.json`

### Step 5 — Generate Branded PDF

```bash
python tools/generate_pdf.py
```

Output: `output/YYYY-MM-DD_competitor_analysis.pdf`

---

## Report Contents

| Section | Description |
|---|---|
| Cover page | Logo, report title, date, competitor count |
| Executive summary | 3–4 sentence landscape overview |
| Market overview | Competitive dynamics and key trends |
| Competitor profiles | Positioning, strengths, weaknesses, pricing, review sentiment, threat level |
| Feature comparison matrix | Your product vs all competitors |
| Opportunities | Market gaps you can exploit |
| Threats | Competitive risks and mitigations |
| Strategic recommendations | Prioritized action list with next steps |

---

## Project Structure

```
config/
  company.json        # Your business details
  brand.json          # Colors, fonts, logo path
assets/
  logo.png            # Your logo (add this)
tools/
  discover_competitors.py
  scrape_competitor.py
  get_reviews.py
  generate_analysis.py
  generate_pdf.py
templates/
  report.html         # Jinja2 report layout
  report.css          # Brand-variable CSS
workflows/
  competitor_analysis.md  # Full SOP with error handling guide
output/               # Generated PDFs land here
.tmp/                 # Intermediate data (regenerated each run)
```

## Troubleshooting

| Error | Fix |
|---|---|
| `cannot load library 'libgobject-2.0-0'` | `brew install pango` |
| `SERPER_API_KEY not set` | Add key to `.env` |
| `ANTHROPIC_API_KEY not set` | Add key to `.env` |
| Competitor data missing / JS-heavy site | Expected — Claude notes gaps in the analysis |
| `Could not parse Claude response as JSON` | Re-run `python tools/generate_analysis.py` |
