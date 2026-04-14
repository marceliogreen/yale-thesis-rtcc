#!/usr/bin/env python3
"""
Find open-access RTCC research sources.
"""
import requests
from pathlib import Path
import re

# Open-access sources to check
open_access_sources = [
    ("NIJ RTCC", "https://nij.ojp.gov/topics/articles/real-time-crime-centers"),
    ("BJS RTCC", "https://bjs.ojp.gov/"),
    ("CJTTec RTCC", "https://cjttec.org/real-time-crime-centers-integrating-technology-to-e"),
    ("RAND Chicago", "https://www.rand.org/pubs/research_reports/RR3242.html"),
    ("UCF Thesis", "https://stars.library.ucf.edu/cgi/viewcontent.cgi?article=2243&context=etd2020"),
    ("ResearchGate RTCC", "https://www.researchgate.net/search?q=real-time+crime+center"),
    ("Google Scholar", "https://scholar.google.com/scholar?q=real+time+crime+center+effectiveness"),
]

print("="*80)
print("OPEN-ACCESS RTCC RESEARCH SOURCES")
print("="*80)

for name, url in open_access_sources:
    print(f"\n{name}: {url}")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            # Look for key terms
            content = response.text.lower()
            if "clearance" in content:
                print(f"  ✓ Contains 'clearance' data")
            if "effectiveness" in content or "effective" in content:
                print(f"  ✓ Contains effectiveness information")
            if "pdf" in content or ".pdf" in content:
                print(f"  ✓ Contains PDF downloads")
    except Exception as e:
        print(f"  Error: {e}")

# Search for additional open-access papers
print("\n" + "="*80)
print("KNOWN OPEN-ACCESS RTCC PAPERS")
print("="*80)

known_papers = [
    {
        "title": "Law enforcement motivations for establishing real-time crime centers",
        "author": "Unknown (UCF Thesis, 2020)",
        "url": "https://stars.library.ucf.edu/cgi/viewcontent.cgi?article=2243&context=etd2020",
        "access": "OPEN"
    },
    {
        "title": "Real-Time Crime Centers as Frontiers of Technology in Policing",
        "author": "Przeszlowski (FIU Dissertation, 2023)",
        "url": "https://digitalcommons.fiu.edu/record/14169/files/FIDC01117.pdf",
        "access": "DOWNLOADED"
    },
    {
        "title": "Do real-time crime centers improve case clearance?",
        "author": "Arietti (Journal of Criminal Justice, 2024)",
        "url": "https://read-me.org/s/1-s20-S0047235223001162-main.pdf",
        "access": "DOWNLOADED"
    },
    {
        "title": "Real Time Crime Centers in Chicago (RAND Report)",
        "author": "Hollywood et al. (2019)",
        "url": "https://www.rand.org/pubs/research_reports/RR3242.html",
        "access": "DOWNLOADED"
    },
]

for paper in known_papers:
    print(f"\n[{paper['access']}] {paper['title']}")
    print(f"  Author: {paper['author']}")
    print(f"  URL: {paper['url']}")

