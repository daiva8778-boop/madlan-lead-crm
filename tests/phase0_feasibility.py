"""
Phase 0 feasibility test — run once, by hand, before building the full app.

Confirms (against REAL madlan.co.il pages, spending real Firecrawl credits):
  1. Plain requests vs Firecrawl behavior on a directory page and profile pages.
  2. Whether a __NEXT_DATA__ / Apollo JSON blob is embedded with agency data.
  3. Whether ?page=2 pagination works, and what the real mechanism is.
  4. The correct Hebrew URL slug for each of the 6 target cities.

Not part of the shipped app — this is throwaway diagnostic output.
"""
import json
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "").strip()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.madlan.co.il/",
}

CITIES = {
    "tel_aviv": "תל-אביב-יפו-ישראל",
    "jerusalem": "ירושלים-ישראל",
    "haifa": "חיפה-ישראל",
    "ramat_gan": "רמת-גן-ישראל",
    "netanya": "נתניה-ישראל",
    "rishon_lezion": "ראשון-לציון-ישראל",
}

DIRECTORY_BASE = "https://www.madlan.co.il/madad-search/"


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def try_plain_requests(url, label):
    print(f"\n--- Plain requests: {label} ---")
    print(f"URL: {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        print(f"Status: {r.status_code}, length: {len(r.text)}")
        return r
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return None


def try_firecrawl(url, label, fc_client):
    print(f"\n--- Firecrawl fallback: {label} ---")
    print(f"URL: {url}")
    try:
        doc = fc_client.scrape(url, formats=["markdown", "html"])
        html = getattr(doc, "html", None) or ""
        md = getattr(doc, "markdown", None) or ""
        print(f"Firecrawl OK. html length: {len(html)}, markdown length: {len(md)}")
        return doc
    except Exception as e:
        print(f"FIRECRAWL EXCEPTION: {e}")
        return None


def inspect_next_data(html, label):
    print(f"\n-- Checking for __NEXT_DATA__ / Apollo state in {label} --")
    if not html:
        print("No HTML to inspect.")
        return None
    m = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if m:
        try:
            data = json.loads(m.group(1))
            print("FOUND __NEXT_DATA__. Top-level keys:", list(data.keys()))
            dumped = json.dumps(data)
            print(f"Total JSON size: {len(dumped)} chars")
            has_phone = "phone" in dumped.lower() or "טלפון" in dumped
            print(f"Contains 'phone'-ish key anywhere: {has_phone}")
            # Save it for manual inspection
            out_path = os.path.join(os.path.dirname(__file__), f"next_data_{label}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Saved full blob to {out_path} for inspection")
            return data
        except Exception as e:
            print(f"Found tag but failed to parse JSON: {e}")
    else:
        print("No __NEXT_DATA__ script tag found.")

    apollo_m = re.search(r"__APOLLO_STATE__\s*=\s*(\{.*?\});", html, re.DOTALL)
    if apollo_m:
        print("FOUND window.__APOLLO_STATE__ blob.")
    else:
        print("No __APOLLO_STATE__ blob found either.")
    return None


def find_agency_links(html):
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        if "/agentsOffice/" in a["href"]:
            href = a["href"]
            if href.startswith("/"):
                href = "https://www.madlan.co.il" + href
            links.add(href.split("?")[0])
    return sorted(links)


def find_tel_link(html):
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    tel_a = soup.find("a", href=re.compile(r"^tel:"))
    return tel_a["href"] if tel_a else None


def find_website_link(html, exclude_domain="madlan.co.il"):
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and exclude_domain not in href:
            return href
    return None


def main():
    if not FIRECRAWL_API_KEY:
        print("ERROR: FIRECRAWL_API_KEY not set in .env — aborting.")
        sys.exit(1)

    from firecrawl import Firecrawl
    fc = Firecrawl(api_key=FIRECRAWL_API_KEY)

    section("STEP 1: Tel Aviv directory page — plain requests")
    tel_aviv_slug = CITIES["tel_aviv"]
    directory_url = DIRECTORY_BASE + tel_aviv_slug
    r = try_plain_requests(directory_url, "Tel Aviv directory p1")

    directory_html = None
    directory_method = None
    if r is not None and r.status_code == 200 and len(r.text) > 2000:
        links = find_agency_links(r.text)
        if links:
            directory_html = r.text
            directory_method = "requests"
            print(f"Plain requests SUCCEEDED — found {len(links)} agency links.")

    if directory_html is None:
        print("Plain requests failed or yielded no agency links — falling back to Firecrawl.")
        doc = try_firecrawl(directory_url, "Tel Aviv directory p1", fc)
        if doc is not None:
            directory_html = getattr(doc, "html", None)
            directory_method = "firecrawl"

    if directory_html is None:
        print("\nBOTH METHODS FAILED on the directory page. Stopping — see failure report below.")
        sys.exit(2)

    print(f"\nDirectory page obtained via: {directory_method}")
    inspect_next_data(directory_html, "directory_tel_aviv")
    agency_links = find_agency_links(directory_html)
    print(f"\nAgency profile links found on directory page: {len(agency_links)}")
    for l in agency_links[:10]:
        print("  ", l)

    section("STEP 2: Pagination check (?page=2)")
    page2_url = directory_url + "?page=2"
    r2 = try_plain_requests(page2_url, "Tel Aviv directory p2")
    page2_html = None
    if r2 is not None and r2.status_code == 200 and len(r2.text) > 2000:
        page2_links = find_agency_links(r2.text)
        if page2_links:
            page2_html = r2.text
            print(f"page=2 via requests SUCCEEDED — {len(page2_links)} links.")
    if page2_html is None:
        doc2 = try_firecrawl(page2_url, "Tel Aviv directory p2", fc)
        if doc2 is not None:
            page2_html = getattr(doc2, "html", None)
            page2_links = find_agency_links(page2_html) if page2_html else []

    if page2_html:
        overlap = set(agency_links) & set(page2_links)
        print(f"Links on page 1: {len(agency_links)}, page 2: {len(page2_links)}, overlap: {len(overlap)}")
        if overlap == set(agency_links) and agency_links:
            print("WARNING: page=2 returned IDENTICAL content to page 1 — ?page=N may not be the real pagination mechanism.")
        else:
            print("page=2 returned DIFFERENT agencies than page 1 — ?page=N pagination CONFIRMED working.")
    else:
        print("Could not fetch page 2 via either method.")

    section("STEP 3: 3 real agency profile pages")
    test_profiles = agency_links[:3]
    if not test_profiles:
        print("No profile links available from directory page to test — skipping.")
    for i, purl in enumerate(test_profiles, 1):
        print(f"\n### Profile {i}: {purl}")
        pr = try_plain_requests(purl, f"profile {i}")
        phtml = None
        pmethod = None
        if pr is not None and pr.status_code == 200 and len(pr.text) > 1000:
            if find_tel_link(pr.text):
                phtml = pr.text
                pmethod = "requests"
        if phtml is None:
            pdoc = try_firecrawl(purl, f"profile {i}", fc)
            if pdoc is not None:
                phtml = getattr(pdoc, "html", None)
                pmethod = "firecrawl"

        if phtml is None:
            print("BOTH METHODS FAILED on this profile page.")
            continue

        inspect_next_data(phtml, f"profile_{i}")
        soup = BeautifulSoup(phtml, "html.parser")
        title = soup.find("h1")
        tel = find_tel_link(phtml)
        website = find_website_link(phtml)
        print(f"Method used: {pmethod}")
        print(f"Name (h1): {title.get_text(strip=True) if title else 'NOT FOUND'}")
        print(f"tel: link: {tel}")
        print(f"Website link candidate: {website}")
        time.sleep(1.7)

    section("STEP 4: Verify city slugs for all 6 target cities")
    results = {}
    for key, slug in CITIES.items():
        if key == "tel_aviv":
            results[key] = (slug, "already confirmed above")
            continue
        url = DIRECTORY_BASE + slug
        r = try_plain_requests(url, f"{key} directory")
        ok = False
        method = None
        if r is not None and r.status_code == 200 and len(r.text) > 2000 and find_agency_links(r.text):
            ok = True
            method = "requests"
        else:
            doc = try_firecrawl(url, f"{key} directory", fc)
            if doc is not None:
                html = getattr(doc, "html", None)
                if html and find_agency_links(html):
                    ok = True
                    method = "firecrawl"
        results[key] = (slug, f"OK via {method}" if ok else "FAILED — slug likely wrong")
        time.sleep(1.7)

    print("\nCity slug verification results:")
    for key, (slug, status) in results.items():
        print(f"  {key:15s} slug='{slug}'  ->  {status}")

    section("DONE — review output above before proceeding to full build")


if __name__ == "__main__":
    main()
