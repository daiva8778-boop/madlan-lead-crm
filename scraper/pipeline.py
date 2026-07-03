import config
from db.database import get_db, now_iso
from db import repo
from scraper import madlan_client, directory_parser, profile_parser, enrichment
from scraper.phone_utils import normalize_il_phone

MOBILE_RESCRAPE_BATCH_SIZE = 5


class RunSummary:
    def __init__(self):
        self.new_saved = 0
        self.no_website_count = 0
        self.credits_used = 0
        self.failed_count = 0
        self.city_exhausted = False


class MobileRescrapeSummary:
    def __init__(self):
        self.checked = 0
        self.found = 0


def _build_directory_url(city_key):
    slug = config.CITIES[city_key]["slug"]
    return config.DIRECTORY_BASE_URL + slug


def scrape_next_50(city_key, progress_callback=None):
    """Madlan's directory page embeds the FULL office list for the city
    (every agency, with phone numbers) in a single server-rendered JSON blob —
    confirmed live (633/633 Tel Aviv offices in one fetch). One directory
    fetch gets the full list; each new agency's own profile page is then
    visited (also SSR-rendered data, not DOM scraping) to confirm phone and
    pick up a website URL, which — if present — is used for direct-mobile
    enrichment per the original spec."""
    conn = get_db()
    summary = RunSummary()
    try:
        progress = repo.get_scrape_progress(conn, city_key)
        if progress["city_exhausted"]:
            summary.city_exhausted = True
            return summary

        directory_url = _build_directory_url(city_key)
        dir_fetch = madlan_client.fetch_directory(directory_url)
        summary.credits_used += dir_fetch["credits_used"]
        repo.increment_firecrawl_credits(conn, dir_fetch["credits_used"])

        if not dir_fetch["success"]:
            repo.log_failed_url(conn, directory_url, "directory", city_key,
                                 "both methods failed to load the directory listing")
            summary.failed_count += 1
            return summary

        stubs = directory_parser.parse_directory_redux_state(dir_fetch["html"])
        new_stubs = [s for s in stubs if not repo.agency_exists(conn, s.office_id)]

        if not new_stubs:
            repo.save_scrape_progress(conn, city_key, 0, True, progress["total_scraped_so_far"])
            summary.city_exhausted = True
            return summary

        total_scraped_so_far = progress["total_scraped_so_far"]
        batch = new_stubs[:config.SCRAPE_BATCH_TARGET]

        for stub in batch:
            profile_fetch = madlan_client.fetch_profile(stub.profile_url)
            summary.credits_used += profile_fetch["credits_used"]
            repo.increment_firecrawl_credits(conn, profile_fetch["credits_used"])
            if profile_fetch["method"] != "requests":
                madlan_client.polite_sleep()

            name = stub.name
            phone_raw = normalize_il_phone(stub.phone_raw)
            website_url = None
            source_method = dir_fetch["method"]

            if profile_fetch["success"]:
                profile = profile_parser.parse_profile_page(profile_fetch["html"])
                name = profile.name or stub.name
                phone_raw = normalize_il_phone(profile.phone_raw) or phone_raw
                website_url = profile.website_url
                source_method = profile_fetch["method"]
            else:
                repo.log_failed_url(conn, stub.profile_url, "profile", city_key,
                                     f"blocked after {profile_fetch['attempts']} attempts — "
                                     f"used directory-page phone/name as fallback")

            has_website = bool(website_url)
            direct_mobile = enrichment.try_enrich(website_url) if has_website else None

            if direct_mobile:
                phone_used, phone_source = direct_mobile, "direct_mobile"
            elif phone_raw:
                phone_used, phone_source = phone_raw, "tracking_073"
            else:
                phone_used, phone_source = None, "none"

            repo.insert_agency(
                conn,
                office_id=stub.office_id,
                name=name,
                city=city_key,
                profile_url=stub.profile_url,
                deals_count=stub.deals_count,
                exclusives_count=stub.exclusives_count,
                phone_raw=phone_raw,
                direct_mobile=direct_mobile,
                phone_used=phone_used,
                phone_source=phone_source,
                website_url=website_url,
                has_website=has_website,
                source_method=source_method,
            )
            summary.new_saved += 1
            total_scraped_so_far += 1
            if not has_website:
                summary.no_website_count += 1

            if progress_callback:
                progress_callback(summary.new_saved, len(batch),
                                   summary.no_website_count, summary.credits_used)

            repo.save_scrape_progress(conn, city_key, 0, False, total_scraped_so_far)

        return summary
    finally:
        conn.close()


def rescrape_mobile_batch(progress_callback=None):
    """Re-checks agencies that have a website but no confirmed direct mobile
    yet (phone_source != 'direct_mobile') — the first enrichment attempt can
    miss it (site slow/down at scrape time, contact page not found that
    round), so retrying later can pick up ones that were missed. Processes
    MOBILE_RESCRAPE_BATCH_SIZE at a time, oldest-scraped first."""
    conn = get_db()
    summary = MobileRescrapeSummary()
    try:
        rows = conn.execute(
            """SELECT id, name, website_url FROM agencies
               WHERE has_website=1 AND phone_source != 'direct_mobile'
               ORDER BY id LIMIT ?""",
            (MOBILE_RESCRAPE_BATCH_SIZE,),
        ).fetchall()

        for row in rows:
            direct_mobile = enrichment.try_enrich(row["website_url"])
            summary.checked += 1

            if direct_mobile:
                conn.execute(
                    """UPDATE agencies SET direct_mobile=?, phone_used=?,
                       phone_source='direct_mobile', updated_at=? WHERE id=?""",
                    (direct_mobile, direct_mobile, now_iso(), row["id"]),
                )
                conn.commit()
                summary.found += 1

            if progress_callback:
                progress_callback(summary.checked, len(rows), summary.found)

        return summary
    finally:
        conn.close()
