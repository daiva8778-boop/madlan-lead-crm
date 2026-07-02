from scraper.ssr_extract import extract_ssr_state


class AgencyStub:
    def __init__(self, office_id, name, deals_count, exclusives_count, phone_raw):
        self.office_id = office_id
        self.name = name
        self.profile_url = f"https://www.madlan.co.il/agentsOffice/{office_id}"
        self.deals_count = deals_count
        self.exclusives_count = exclusives_count
        self.phone_raw = phone_raw


def parse_directory_redux_state(raw_html):
    """Madlan server-side embeds the FULL office list (every agency in the
    city, not just what's initially visible) directly in the directory page's
    HTML, including each office's phone number — confirmed via live inspection
    (633/633 Tel Aviv offices present in a single fetch). This makes scrolling
    through the directory unnecessary — one fetch returns everything.
    Returns a list of AgencyStub, deduplicated by office_id."""
    data = extract_ssr_state(raw_html)
    if not data:
        return []

    try:
        offices = (
            data["reduxInitialState"]["domainData"]["searchMadadAgentsOffices"]
            ["data"]["madadAgentsOffices"]["office"]
        )
    except (KeyError, TypeError):
        return []

    stubs = {}
    for o in offices:
        office_id = o.get("officeId")
        name = o.get("officeName")
        if not office_id or not name:
            continue
        if office_id in stubs:
            continue
        stubs[office_id] = AgencyStub(
            office_id=office_id,
            name=name,
            deals_count=o.get("soldCount"),
            exclusives_count=o.get("exclusiveListingCount"),
            phone_raw=o.get("phone"),
        )
    return list(stubs.values())
