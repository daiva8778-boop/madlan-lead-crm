import re

import requests
from bs4 import BeautifulSoup

import config
from scraper.phone_utils import normalize_il_phone, is_mobile

MOBILE_RE = re.compile(r"\b05\d(?:[-\s]?\d){7}\b")
WA_LINK_RE = re.compile(r"https?://(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(\d{9,15})")
CONTACT_LINK_KEYWORDS = ("צור קשר", "צרו קשר", "יצירת קשר", "contact")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}


def _extract_mobile_from_html(html):
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    tel_a = soup.find("a", href=re.compile(r"^tel:05"))
    if tel_a:
        normalized = normalize_il_phone(tel_a["href"].replace("tel:", ""))
        if normalized and is_mobile(normalized):
            return normalized

    for a in soup.find_all("a", href=True):
        wa_m = WA_LINK_RE.search(a["href"])
        if wa_m:
            normalized = normalize_il_phone(wa_m.group(1))
            if normalized:
                return normalized

    text = soup.get_text(" ", strip=True)
    mobile_m = MOBILE_RE.search(text)
    if mobile_m:
        normalized = normalize_il_phone(mobile_m.group(0))
        if normalized and is_mobile(normalized):
            return normalized

    return None


def _find_contact_page_url(html, base_url):
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        link_text = a.get_text(strip=True).lower()
        href = a["href"]
        if any(kw.lower() in link_text or kw.lower() in href.lower() for kw in CONTACT_LINK_KEYWORDS):
            if href.startswith("http"):
                return href
            if href.startswith("/"):
                from urllib.parse import urljoin
                return urljoin(base_url, href)
    return None


def try_enrich(website_url):
    """Best-effort direct-mobile lookup from an agency's own website.
    Never raises — a broken/slow site must never crash a scrape batch."""
    if not website_url:
        return None
    try:
        r = requests.get(website_url, headers=HEADERS, timeout=config.ENRICHMENT_TIMEOUT_SECONDS)
        if r.status_code != 200:
            return None
        homepage_html = r.text
    except Exception:
        return None

    mobile = _extract_mobile_from_html(homepage_html)
    if mobile:
        return mobile

    try:
        contact_url = _find_contact_page_url(homepage_html, website_url)
        if contact_url:
            r2 = requests.get(contact_url, headers=HEADERS, timeout=config.ENRICHMENT_TIMEOUT_SECONDS)
            if r2.status_code == 200:
                return _extract_mobile_from_html(r2.text)
    except Exception:
        return None

    return None
