from db.database import now_iso


def agency_exists(conn, office_id):
    row = conn.execute(
        "SELECT 1 FROM agencies WHERE madlan_office_id=?", (office_id,)
    ).fetchone()
    return row is not None


def insert_agency(conn, *, office_id, name, city, profile_url, deals_count,
                   exclusives_count, phone_raw, direct_mobile, phone_used,
                   phone_source, website_url, has_website, source_method):
    ts = now_iso()
    cur = conn.execute(
        """INSERT INTO agencies (
            madlan_office_id, name, city, profile_url, deals_count, exclusives_count,
            phone_raw, direct_mobile, phone_used, phone_source, website_url, has_website,
            status, scraped_at, last_seen_at, source_method, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'NEW',?,?,?,?,?) RETURNING id""",
        (office_id, name, city, profile_url, deals_count, exclusives_count,
         phone_raw, direct_mobile, phone_used, phone_source, website_url,
         1 if has_website else 0, ts, ts, source_method, ts, ts),
    )
    new_id = cur.lastrowid
    conn.commit()
    return new_id


def get_scrape_progress(conn, city):
    row = conn.execute("SELECT * FROM scrape_progress WHERE city=?", (city,)).fetchone()
    if row:
        return dict(row)
    return {"city": city, "scroll_depth": 0, "city_exhausted": 0, "total_scraped_so_far": 0}


def save_scrape_progress(conn, city, scroll_depth, city_exhausted, total_scraped_so_far):
    conn.execute(
        """INSERT INTO scrape_progress (city, scroll_depth, city_exhausted, total_scraped_so_far, updated_at)
           VALUES (?,?,?,?,?)
           ON CONFLICT(city) DO UPDATE SET
             scroll_depth=excluded.scroll_depth,
             city_exhausted=excluded.city_exhausted,
             total_scraped_so_far=excluded.total_scraped_so_far,
             updated_at=excluded.updated_at""",
        (city, scroll_depth, 1 if city_exhausted else 0, total_scraped_so_far, now_iso()),
    )
    conn.commit()


def log_failed_url(conn, url, url_type, city, reason):
    conn.execute(
        """INSERT INTO failed_urls (url, url_type, city, reason, attempted_at)
           VALUES (?,?,?,?,?)""",
        (url, url_type, city, reason, now_iso()),
    )
    conn.commit()


def increment_firecrawl_credits(conn, amount):
    if amount <= 0:
        return
    conn.execute(
        """UPDATE settings SET firecrawl_credits_used_total = firecrawl_credits_used_total + ?,
           updated_at=? WHERE id=1""",
        (amount, now_iso()),
    )
    conn.commit()
