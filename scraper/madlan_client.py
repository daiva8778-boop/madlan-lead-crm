import random
import time

import requests

import config
from scraper import firecrawl_client

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.madlan.co.il/",
}


def polite_sleep():
    time.sleep(random.uniform(config.POLITE_DELAY_MIN, config.POLITE_DELAY_MAX))


def _has_agency_links(html):
    # directory pages embed the full office list (incl. phone numbers) as a
    # window.__SSR_HYDRATED_CONTEXT__ blob — that's what we actually need,
    # not the rendered DOM cards.
    return bool(html) and "__SSR_HYDRATED_CONTEXT__" in html and '"officeId"' in html


def _has_office_data(html):
    # profile pages embed a structured getRealEstateOfficeById record (phone,
    # website, etc.) in the same kind of SSR blob.
    return bool(html) and "__SSR_HYDRATED_CONTEXT__" in html and "getRealEstateOfficeById" in html


def fetch_directory(url):
    """requests-first, Firecrawl fallback. The directory page embeds the FULL
    office list (every agency in the city, including phone numbers) as a
    window.__SSR_HYDRATED_CONTEXT__ blob inside a <script> tag — confirmed via
    live inspection (633/633 Tel Aviv offices in one fetch). We need the RAW
    page source to see that script tag (Firecrawl's cleaned 'html' format
    strips <script> tags), hence 'rawHtml'. No scrolling/pagination needed —
    everything is present on the first load.
    Returns dict(html, method, credits_used, success)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = "utf-8"  # madlan.co.il is UTF-8; requests' auto-detection
                               # misreads this large mixed-content Hebrew page otherwise
        if r.status_code == 200 and _has_agency_links(r.text):
            return {"html": r.text, "method": "requests", "credits_used": 0, "success": True}
    except requests.RequestException:
        pass

    html, _md, credits = firecrawl_client.scrape(
        url,
        wait_for=config.FIRECRAWL_DIRECTORY_WAIT_MS,
        formats=["rawHtml"],
    )
    if _has_agency_links(html):
        return {"html": html, "method": "firecrawl", "credits_used": credits, "success": True}
    return {"html": None, "method": "firecrawl", "credits_used": credits, "success": False}


def fetch_profile(url):
    """requests-first, Firecrawl fallback. Profile pages embed a structured
    office record (phone, website, social links) in the same kind of SSR blob
    as the directory page — confirmed live. Madlan's profile-page bot
    protection has been intermittent in testing (sometimes blocked, sometimes
    not), so a bounded retry loop backs up the Firecrawl fallback path in case
    a given attempt gets a blocked/empty response.
    Returns dict(html, method, credits_used, success, attempts)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = "utf-8"
        if r.status_code == 200 and _has_office_data(r.text):
            return {"html": r.text, "method": "requests", "credits_used": 0, "success": True, "attempts": 1}
    except requests.RequestException:
        pass

    total_credits = 0
    last_html = None
    for attempt in range(1, config.PROFILE_FETCH_MAX_ATTEMPTS + 1):
        html, _md, credits = firecrawl_client.scrape(
            url,
            wait_for=config.FIRECRAWL_PROFILE_WAIT_MS,
            formats=["rawHtml"],
        )
        total_credits += credits
        last_html = html
        if _has_office_data(html):
            return {"html": html, "method": "firecrawl", "credits_used": total_credits,
                    "success": True, "attempts": attempt}
        if attempt < config.PROFILE_FETCH_MAX_ATTEMPTS:
            time.sleep(random.uniform(config.PROFILE_FETCH_RETRY_DELAY_MIN, config.PROFILE_FETCH_RETRY_DELAY_MAX))

    return {"html": last_html, "method": "firecrawl", "credits_used": total_credits,
            "success": False, "attempts": config.PROFILE_FETCH_MAX_ATTEMPTS}
