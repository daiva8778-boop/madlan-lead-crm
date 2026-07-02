CREATE TABLE IF NOT EXISTS agencies (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    madlan_office_id    TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    city                TEXT NOT NULL,
    profile_url         TEXT NOT NULL,
    deals_count         INTEGER,
    exclusives_count    INTEGER,
    phone_raw           TEXT,
    direct_mobile       TEXT,
    phone_used          TEXT,
    phone_source        TEXT CHECK(phone_source IN ('direct_mobile','tracking_073','manual','none')) DEFAULT 'none',
    website_url         TEXT,
    has_website         INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'NEW'
                         CHECK(status IN ('NEW','SENT','REPLIED','MEETING','CLIENT',
                                           'NOT_INTERESTED','DO_NOT_CONTACT')),
    sent_at             TEXT,
    replied_at          TEXT,
    auto_reply_sent     INTEGER NOT NULL DEFAULT 0,
    auto_reply_sent_at  TEXT,
    notes               TEXT NOT NULL DEFAULT '',
    scraped_at          TEXT NOT NULL,
    last_seen_at        TEXT,
    source_method       TEXT CHECK(source_method IN ('requests','firecrawl','mixed')),
    do_not_contact_locked INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_agencies_city ON agencies(city);
CREATE INDEX IF NOT EXISTS idx_agencies_status ON agencies(status);
CREATE INDEX IF NOT EXISTS idx_agencies_sent_at ON agencies(sent_at);
CREATE INDEX IF NOT EXISTS idx_agencies_has_website ON agencies(has_website);
CREATE INDEX IF NOT EXISTS idx_agencies_scraped_at ON agencies(scraped_at);

CREATE TABLE IF NOT EXISTS message_log (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    agency_id          INTEGER NOT NULL REFERENCES agencies(id) ON DELETE CASCADE,
    template_key       TEXT NOT NULL CHECK(template_key IN
                        ('opener_has_site','opener_no_site','followup','auto_reply')),
    template_version   TEXT NOT NULL,
    message_text       TEXT NOT NULL,
    triggered_by       TEXT NOT NULL CHECK(triggered_by IN ('manual_click','auto_reply_module')),
    sent_at            TEXT NOT NULL,
    voided             INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_message_log_agency ON message_log(agency_id);
CREATE INDEX IF NOT EXISTS idx_message_log_version ON message_log(template_version);

CREATE TABLE IF NOT EXISTS scrape_progress (
    city                  TEXT PRIMARY KEY,
    scroll_depth          INTEGER NOT NULL DEFAULT 0,
    city_exhausted        INTEGER NOT NULL DEFAULT 0,
    total_scraped_so_far  INTEGER NOT NULL DEFAULT 0,
    updated_at            TEXT
);

CREATE TABLE IF NOT EXISTS failed_urls (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url           TEXT NOT NULL,
    url_type      TEXT NOT NULL CHECK(url_type IN ('directory','profile','enrichment')),
    city          TEXT,
    reason        TEXT,
    attempted_at  TEXT NOT NULL,
    resolved      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_failed_urls_type ON failed_urls(url_type);
CREATE INDEX IF NOT EXISTS idx_failed_urls_resolved ON failed_urls(resolved);

CREATE TABLE IF NOT EXISTS settings (
    id                            INTEGER PRIMARY KEY CHECK (id = 1),
    autoreply_enabled             INTEGER NOT NULL DEFAULT 0,
    autoreply_connection_status   TEXT NOT NULL DEFAULT 'not_running',
    firecrawl_credits_used_total  INTEGER NOT NULL DEFAULT 0,
    last_backup_date              TEXT,
    updated_at                    TEXT
);
INSERT OR IGNORE INTO settings (id, updated_at) VALUES (1, datetime('now'));
