# Competitor Analysis Workflow

## Objective
Produce a branded PDF report analyzing competitors for a SaaS business. The report covers positioning, features, pricing, customer sentiment, market opportunities, threats, and strategic recommendations.

## Required Inputs
Before running, ensure the following are in place:

| Input | Location | Notes |
|---|---|---|
| Company brief | `config/company.json` | Fill in all fields, especially `name`, `category`, and `description` |
| Brand settings | `config/brand.json` | Hex colors, font names, logo path |
| Logo file | `assets/logo.png` (or .svg) | Drop your logo here; update `logo_path` in brand.json if using a different filename |
| API keys | `.env` | `ANTHROPIC_API_KEY` and `SERPER_API_KEY` must be set |

## Step-by-Step Execution

### Step 1 — Discover Competitors
```bash
python tools/discover_competitors.py --company-config config/company.json
```
**Output:** `.tmp/competitors.json` — list of up to 8 competitors with name, URL, description.

**Notes:**
- If auto-discovery misses key competitors, add them to `known_competitors` in `config/company.json` and re-run.
- The script skips review aggregators (G2, Capterra, Reddit) and tries to return direct competitor homepages.
- **For niche/new brands:** If the company name is not widely indexed, the first search pass may return blog posts rather than product homepages. In that case, manually edit `.tmp/competitors.json` with the correct company names and URLs before proceeding to Step 2. Known AI pen testing competitors: vonahi.io, horizon3.ai, pentera.io, zerothreat.ai, escape.tech, terra.security.

---

### Step 2 — Scrape Each Competitor
Run once per competitor from `.tmp/competitors.json`:
```bash
python tools/scrape_competitor.py --url "https://competitor.com" --name "Competitor Name"
```
**Output:** `.tmp/scraped_<name>.json` — headline, value prop, features, pricing text.

**Notes:**
- Some pages are JavaScript-heavy and may return minimal data. This is expected — Claude will note gaps in the analysis.
- Paywalled or login-protected pricing pages will be skipped gracefully.
- If a competitor returns an error, try running again once. If it consistently fails, skip it and note the gap.

---

### Step 3 — Fetch Reviews for Each Competitor
Run once per competitor:
```bash
python tools/get_reviews.py --name "Competitor Name"
```
**Output:** `.tmp/reviews_<name>.json` — rating, review count, pros/cons themes.

**Notes:**
- Review data is pulled from Serper search snippets, not scraped directly from G2/Capterra. Ratings may be approximate.
- If no reviews are found, the JSON will have null fields — this is fine; Claude will handle it.

---

### Step 4 — Generate Analysis
```bash
python tools/generate_analysis.py --company-config config/company.json --data-dir .tmp/
```
**Output:** `.tmp/analysis.json` — structured JSON with all report sections.

**Notes:**
- Uses `claude-sonnet-4-6`. This call costs approximately $0.05–$0.15 depending on data volume.
- If Claude returns malformed JSON, the script saves the raw text with a warning. In that case, re-run once.
- The analysis is grounded in the scraped data — Claude will not fabricate details for competitors with missing data.

---

### Step 5 — Generate Branded PDF
```bash
python tools/generate_pdf.py \
  --analysis .tmp/analysis.json \
  --company-config config/company.json \
  --brand config/brand.json \
  --output output/
```
**Output:** `output/YYYY-MM-DD_competitor_analysis.pdf`

**Notes:**
- `weasyprint` requires system fonts or Google Fonts to be accessible. If fonts fail to load, the PDF will fall back to a system sans-serif font.
- Logo must be PNG or SVG. It's embedded as base64, so no path issues in the PDF.
- Open the PDF and check the cover page, competitor profiles, and feature matrix to verify branding looks correct.

---

## End-to-End Quick Run (all at once)

If you prefer to run the full workflow without supervision, here's the sequence to execute:

```
1. python tools/discover_competitors.py
2. [for each competitor in .tmp/competitors.json]
   python tools/scrape_competitor.py --url <url> --name <name>
   python tools/get_reviews.py --name <name>
3. python tools/generate_analysis.py
4. python tools/generate_pdf.py
```

---

## Brand Asset Setup (one-time)

1. Drop your logo into `assets/logo.png` (PNG recommended, SVG also works)
2. Open `config/brand.json` and update:
   - `primary_color` — main brand color (used for cover, headings, section bars)
   - `secondary_color` — secondary color (used for rec numbers, links)
   - `accent_color` — accent/highlight color (used for callout borders)
   - `font_heading` and `font_body` — must be valid Google Fonts names (e.g., "Inter", "Roboto", "Poppins")
3. Open `config/company.json` and fill in all fields

---

## Error Handling Reference

| Error | Cause | Fix |
|---|---|---|
| `SERPER_API_KEY not set` | Missing env var | Add `SERPER_API_KEY=your_key` to `.env` |
| `ANTHROPIC_API_KEY not set` | Missing env var | Add `ANTHROPIC_API_KEY=your_key` to `.env` |
| `Could not fetch <url>` | Site blocking scraper or rate limiting | Wait 30s and retry once; if persistent, skip competitor |
| `No scraped competitor data found` | Step 2 was skipped | Run `scrape_competitor.py` for at least one competitor before Step 4 |
| `Could not parse Claude response as JSON` | Claude returned markdown | Re-run `generate_analysis.py` once |
| Font rendering issues in PDF | Google Fonts not loading | Check internet connection; fallback to a system font in `brand.json` |

---

## Output Sections in the PDF

1. **Cover page** — Logo, report title, date, competitor count
2. **Executive summary** — 3–4 sentence landscape overview
3. **Market overview** — Competitive dynamics and trends
4. **Competitor profiles** — Per-competitor card with positioning, strengths, weaknesses, pricing, review sentiment, threat level
5. **Feature comparison matrix** — Your product vs all competitors
6. **Opportunities** — Market gaps you can exploit
7. **Threats** — Competitive risks and mitigations
8. **Strategic recommendations** — Prioritized action list

---

## Keeping the Workflow Current

After each run, note any recurring issues here:
- If a competitor consistently blocks scraping, add it to a known-blocked list and manually enter its data into `.tmp/scraped_<name>.json`
- If Serper rate limits you, space out Step 2/3 runs by a few seconds between competitors
- Update `config/company.json` whenever your own features or pricing changes — this keeps the analysis accurate
