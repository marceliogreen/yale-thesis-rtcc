#!/usr/bin/env python3
"""
Scrape RTCC effectiveness sources using alternative tools.
Uses trafilatura and requests when firecrawl is unavailable.
"""

import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import trafilatura
from urllib.parse import urljoin


def scrape_with_trafilatura(url: str) -> dict:
    """Scrape URL using requests + trafilatura for clean text extraction."""
    print(f"Scraping: {url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        # Fetch with requests first
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        downloaded = response.content

        content = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            no_fallback=False
        )

        # Try to get metadata
        title = ""
        try:
            title = trafilatura.extract_title(downloaded) or ""
        except:
            pass

        return {
            "url": url,
            "title": title,
            "content": content or "",
            "success": bool(content)
        }
    except Exception as e:
        print(f"  Error: {e}")

    return {"url": url, "success": False, "content": ""}


def scrape_pdf_indirect(url: str) -> dict:
    """Try to get PDF metadata/information."""
    print(f"PDF URL: {url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        return {
            "url": url,
            "content_type": response.headers.get("content-type", ""),
            "content_length": response.headers.get("content-length", ""),
            "status": response.status_code,
            "note": "PDF file - use download separately"
        }
    except Exception as e:
        return {"url": url, "error": str(e)}


def main():
    output_dir = Path("scraping-tools/scraped_content")
    output_dir.mkdir(exist_ok=True)

    # Key sources to scrape
    sources = {
        "nij_rtcc": "https://nij.ojp.gov/library/publications/real-time-crime-centers-integ",
        "state_tech": "https://statetechmagazine.com/article/2025/04/real-time-crime-centers-",
        "case_for_rtcc": "https://resources.missioncriticalpartners.com/insights/the-case-for-re",
        "police1": "https://www.police1.com/tech-pulse/criminologist-how-real-time-crime-c",
        "cjttec": "https://cjttec.org/real-time-crime-centers-integrating-technology-to-e",
    }

    pdfs = {
        "fiu_rtcc": "https://digitalcommons.fiu.edu/record/14169/files/FIDC01117.pdf",
        "fdle_rtcc": "https://www.fdle.state.fl.us/getContentAsset/3238f645-2645-4f60-aa6b-e",
        "rand_chicago": "https://yidawang.ca/pdf/rand.pdf",
        "lexipol_guide": "https://lexipol.brightspotcdn.com/2a/b3/c9ffbfe24ec3b5f1ee6e87bda5a5/p",
    }

    results = {}

    # Scrape HTML sources
    print("=" * 60)
    print("Scraping HTML Sources")
    print("=" * 60)

    for name, url in sources.items():
        result = scrape_with_trafilatura(url)
        results[name] = result

        # Save individual file
        if result.get("success"):
            filename = output_dir / f"{name}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# {result.get('title', url)}\n\n")
                f.write(f"Source: {url}\n\n")
                f.write(result["content"])
            print(f"  Saved to {filename}")

    # Get PDF info
    print("\n" + "=" * 60)
    print("PDF Sources (download separately)")
    print("=" * 60)

    for name, url in pdfs.items():
        info = scrape_pdf_indirect(url)
        results[name] = info
        print(f"  {name}: {info.get('note', info.get('status', 'unknown'))}")

    # Save summary
    summary_path = output_dir / "scrape_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nSummary saved to {summary_path}")

    # Extract key findings from successful scrapes
    print("\n" + "=" * 60)
    print("KEY FINDINGS EXTRACTED")
    print("=" * 60)

    for name, result in results.items():
        if result.get("success") and result.get("content"):
            content = result["content"]
            # Look for effectiveness mentions
            if "effectiveness" in content.lower() or "effective" in content.lower():
                print(f"\n{name.upper()}:")
                # Find sentences with effectiveness keywords
                sentences = content.split(". ")
                for sent in sentences:
                    if "effective" in sent.lower() or "clearance" in sent.lower() or "outcome" in sent.lower():
                        print(f"  - {sent[:200]}...")
                        break


if __name__ == "__main__":
    main()
