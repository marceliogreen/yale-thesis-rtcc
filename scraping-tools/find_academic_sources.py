#!/usr/bin/env python3
"""
Direct access to known RTCC effectiveness sources.
"""
import requests
from pathlib import Path
import json

# Known academic sources from literature
sources = {
    "guerette_2025": {
        "title": "An Extended Impact Evaluation of RTCC Technologies on Violent Crime Outcomes",
        "url": "https://www.tandfonline.com/doi/abs/10.1080/24751979.2025.2475515",
        "journal": "Justice Evaluation Journal",
        "year": "2025"
    },
    "guerette_2023": {
        "title": "Does the Rapid Deployment of Information to Police Improve Crime Solvability?",
        "url": "https://www.tandfonline.com/doi/abs/10.1080/07418825.2023.2264362",
        "journal": "Justice Quarterly",
        "year": "2023"
    },
    "police_quarterly_2022": {
        "title": "The centralization and rapid deployment of police agency information technologies",
        "url": "https://journals.sagepub.com/doi/abs/10.1177/0032258X221107587",
        "journal": "Police Quarterly",
        "year": "2022"
    },
    "bulletin_2023": {
        "title": "Documenting the continued growth of real-time crime centers",
        "url": "https://journals.sagepub.com/doi/abs/10.1177/0032258X261436634",
        "journal": "FBI Law Enforcement Bulletin",
        "year": "2023"
    }
}

output = []

for key, info in sources.items():
    print(f"\nChecking: {info['title']}")
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(info['url'], headers=headers, timeout=10)
        print(f"  Status: {response.status_code}")
        output.append({
            "key": key,
            "title": info['title'],
            "url": info['url'],
            "status": response.status_code,
            "accessible": response.status_code == 200
        })
    except Exception as e:
        print(f"  Error: {e}")
        output.append({
            "key": key,
            "title": info['title'],
            "url": info['url'],
            "error": str(e),
            "accessible": False
        })

# Save results
out_path = Path("scraping-tools/scraped_content/source_availability.json")
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nSaved to {out_path}")

# Print summary
print("\n" + "="*60)
print("SOURCE ACCESSIBILITY SUMMARY")
print("="*60)
for item in output:
    status = "✓ ACCESSIBLE" if item.get("accessible") else "✗ BLOCKED"
    print(f"{status}: {item['title'][:50]}...")

