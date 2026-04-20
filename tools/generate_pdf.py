#!/usr/bin/env python3
"""
Generate a branded PDF competitor analysis report from analysis data and brand config.

Usage:
    python tools/generate_pdf.py \
        --analysis .tmp/analysis.json \
        --company-config config/company.json \
        --brand config/brand.json \
        --output output/
"""

import argparse
import base64
import json
import os
import sys
from datetime import date
from pathlib import Path

# weasyprint on macOS needs Homebrew's pango/gobject libs in the search path
if sys.platform == "darwin":
    _homebrew_lib = "/opt/homebrew/lib"
    _current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if _homebrew_lib not in _current:
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = f"{_homebrew_lib}:{_current}".rstrip(":")

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

load_dotenv()

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")


def load_logo_base64(logo_path: str) -> tuple[str, str]:
    """Return (base64_data, extension) or ('', '') if not found."""
    if not logo_path or not os.path.exists(logo_path):
        return "", "png"

    ext = Path(logo_path).suffix.lstrip(".").lower()
    if ext == "svg":
        ext = "svg+xml"

    with open(logo_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, ext


def render_css(brand: dict) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    css_template = env.get_template("report.css")
    return css_template.render(
        primary_color=brand.get("primary_color", "#1A2E4A"),
        secondary_color=brand.get("secondary_color", "#2D7DD2"),
        accent_color=brand.get("accent_color", "#F4A261"),
        background_color=brand.get("background_color", "#F8F9FA"),
        text_color=brand.get("text_color", "#1A1A2E"),
        font_heading=brand.get("font_heading", "Inter"),
        font_body=brand.get("font_body", "Inter"),
    )


def render_html(analysis: dict, company: dict, brand: dict, css: str) -> str:
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    # Make dict.get available in templates
    env.globals["dict"] = dict

    html_template = env.get_template("report.html")

    logo_path = brand.get("logo_path", "assets/logo.png")
    logo_data, logo_ext = load_logo_base64(logo_path)

    competitor_count = len(analysis.get("competitor_profiles", []))

    return html_template.render(
        analysis=analysis,
        company=company,
        brand=brand,
        css=css,
        logo_data=logo_data,
        logo_ext=logo_ext,
        report_date=date.today().strftime("%B %d, %Y"),
        competitor_count=competitor_count,
    )


def generate_pdf(analysis_path: str, company_config_path: str, brand_path: str, output_dir: str) -> str:
    with open(analysis_path) as f:
        analysis = json.load(f)

    with open(company_config_path) as f:
        company = json.load(f)

    with open(brand_path) as f:
        brand = json.load(f)

    if "raw_response" in analysis:
        print("Warning: analysis.json contains raw text, not structured data. PDF will be minimal.", file=sys.stderr)

    css = render_css(brand)
    html_content = render_html(analysis, company, brand, css)

    os.makedirs(output_dir, exist_ok=True)
    filename = f"{date.today().isoformat()}_competitor_analysis.pdf"
    output_path = os.path.join(output_dir, filename)

    print(f"Rendering PDF...")
    HTML(string=html_content, base_url=os.getcwd()).write_pdf(output_path)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate branded competitor analysis PDF")
    parser.add_argument("--analysis", default=".tmp/analysis.json")
    parser.add_argument("--company-config", default="config/company.json")
    parser.add_argument("--brand", default="config/brand.json")
    parser.add_argument("--output", default="output/")
    args = parser.parse_args()

    for path in [args.analysis, args.company_config, args.brand]:
        if not os.path.exists(path):
            print(f"Error: File not found: {path}", file=sys.stderr)
            sys.exit(1)

    output_path = generate_pdf(args.analysis, args.company_config, args.brand, args.output)
    print(f"PDF saved → {output_path}")


if __name__ == "__main__":
    main()
