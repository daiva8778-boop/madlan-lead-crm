from scraper.ssr_extract import extract_ssr_state


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
        website_url=office.get("websiteUrl") or None,
    )
