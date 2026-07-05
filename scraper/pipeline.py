import psycopg2

import config
from db.database import get_db, now_iso
from db import repo
from scraper import madlan_client, directory_parser, profile_parser, enrichment
from scraper.phone_utils import normalize_il_phone

MOBILE_RESCRAPE_BATCH_SIZE = 5


class RunSummary:
    def __init__(self):
        self.new_saved = 0
        self.rejected_count = 0
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


def scrape_next_mobile_leads(city_key, progress_callback=None):
    """Only a real 05X mobile number is actually reachable over WhatsApp —
    Madlan's own 073 tracking numbers generally aren't registered there — so
    this only saves agencies to the CRM once a direct mobile is confirmed.
    Everything else checked along the way (no website, or a website with no
    mobile found) is recorded in rejected_office_ids purely so future runs
    don't keep re-visiting it, without cluttering the CRM with unreachable
    contacts. Keeps walking the directory's full office list (fetched once,
    free) until SCRAPE_BATCH_TARGET real mobiles are found or the city runs
    out of candidates."""
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
        candidates = [
            s for s in stubs
            if not repo.agency_exists(conn, s.office_id) and not repo.is_rejected(conn, s.office_id)
        ]

        if not candidates:
            repo.save_scrape_progress(conn, city_key, 0, True, progress["total_scraped_so_far"])
            summary.city_exhausted = True
            return summary

        total_scraped_so_far = progress["total_scraped_so_far"]

        for stub in candidates:
            if summary.new_saved >= config.SCRAPE_BATCH_TARGET:
                break

            profile_fetch = madlan_client.fetch_profile(stub.profile_url)
            summary.credits_used += profile_fetch["credits_used"]

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

            has_website = bool(website_url)
            direct_mobile = enrichment.try_enrich(website_url) if has_website else None

            if profile_fetch["method"] != "requests":
                madlan_client.polite_sleep()

            # Decide the outcome once, up front — everything below is just
            # writing it to the DB, so counters only ever get touched once
            # per candidate no matter how many write-attempts it takes.
            if direct_mobile:
                summary.new_saved += 1
            else:
                summary.rejected_count += 1
            total_scraped_so_far += 1

            # A long-running batch (checking many candidates to find enough
            # with a real mobile) can outlast Neon's idle-connection window —
            # confirmed live. Reconnect once and retry this candidate's DB
            # writes rather than losing the whole run. mark_rejected and
            # insert_agency (guarded by an agency_exists check) are both
            # safe to retry without double-writing.
            for attempt in (1, 2):
                try:
                    repo.increment_firecrawl_credits(conn, profile_fetch["credits_used"])
                    if not profile_fetch["success"]:
                        repo.log_failed_url(conn, stub.profile_url, "profile", city_key,
                                             f"blocked after {profile_fetch['attempts']} attempts — "
                                             f"used directory-page phone/name as fallback")

                    if not direct_mobile:
                        repo.mark_rejected(conn, stub.office_id, city_key,
                                            "no_website" if not has_website else "no_mobile_found")
                    elif not repo.agency_exists(conn, stub.office_id):
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
                            phone_used=direct_mobile,
                            phone_source="direct_mobile",
                            website_url=website_url,
                            has_website=has_website,
                            source_method=source_method,
                        )

                    repo.save_scrape_progress(conn, city_key, 0, False, total_scraped_so_far)
                    break
                except psycopg2.OperationalError:
                    conn.close()
                    conn = get_db()
                    if attempt == 2:
                        summary.failed_count += 1

            if progress_callback:
                progress_callback(summary.new_saved, config.SCRAPE_BATCH_TARGET,
                                   summary.rejected_count, summary.credits_used)

        return summary
    finally:
        conn.close()


def rescrape_mobile_batch(progress_callback=None):
    """Re-checks agencies that have a website but no confirmed direct mobile
    yet (phone_source != 'direct_mobile') — the first enrichment attempt can
    miss it (site slow/down at scrape time, contact page not found that
    round), so retrying later can pick up ones that were missed. Processes
    MOBILE_RESCRAPE_BATCH_SIZE at a time, never-checked-first then
    longest-since-checked — every attempt (found or not) stamps
    mobile_check_attempted_at, so repeated clicks actually rotate through
    the whole list instead of hammering the same few agencies forever."""
    conn = get_db()
    summary = MobileRescrapeSummary()
    try:
        rows = conn.execute(
            """SELECT id, name, website_url FROM agencies
               WHERE has_website=1 AND phone_source != 'direct_mobile'
               ORDER BY mobile_check_attempted_at ASC NULLS FIRST, id ASC LIMIT ?""",
            (MOBILE_RESCRAPE_BATCH_SIZE,),
        ).fetchall()

        for row in rows:
            direct_mobile = enrichment.try_enrich(row["website_url"])
            summary.checked += 1
            ts = now_iso()

            if direct_mobile:
                conn.execute(
                    """UPDATE agencies SET direct_mobile=?, phone_used=?,
                       phone_source='direct_mobile', mobile_check_attempted_at=?,
                       updated_at=? WHERE id=?""",
                    (direct_mobile, direct_mobile, ts, ts, row["id"]),
                )
                summary.found += 1
            else:
                conn.execute(
                    "UPDATE agencies SET mobile_check_attempted_at=? WHERE id=?",
                    (ts, row["id"]),
                )
            conn.commit()

            if progress_callback:
                progress_callback(summary.checked, len(rows), summary.found)

        return summary
    finally:
        conn.close()
