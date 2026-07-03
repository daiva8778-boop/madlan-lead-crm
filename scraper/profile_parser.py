from scraper.ssr_extract import extract_ssr_state


def _normalize_website_url(url):
    """Madlan's websiteUrl field is sometimes missing the scheme entirely
    (e.g. "www.example.co.il" instead of "https://www.example.co.il") —
    confirmed via live data. Without a scheme, requests.get() fails outright
    and a browser link resolves relative to whatever page it's clicked from,
    so this is fixed at the source rather than patched at every call site."""
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    return url


class ProfileResult:
    def __init__(self, name, phone_raw, website_url):
        self.name = name
        self.phone_raw = phone_raw
        self.website_url = website_url


def parse_profile_page(raw_html):
    """The profile page's own window.__SSR_HYDRATED_CONTEXT__ blob includes a
    structured getRealEstateOfficeById record with an explicit websiteUrl
    field (distinct from linkedinUrl/instagramUrl/facebookPageUrl) and a
    virtualPhone — confirmed via live inspection. This is far more reliable
    than guessing from rendered DOM links (no risk of picking a social-media
    link as the "website")."""
    data = extract_ssr_state(raw_html)
    if not data:
        return ProfileResult(None, None, None)

    try:
        office = data["reduxInitialState"]["domainData"]["officeById"]["data"]["getRealEstateOfficeById"]
    except (KeyError, TypeError):
        return ProfileResult(None, None, None)

    if not office:
        return ProfileResult(None, None, None)

    return ProfileResult(
        name=office.get("officeName"),
        phone_raw=office.get("virtualPhone"),
        website_url=_normalize_website_url(office.get("websiteUrl")),
    )
