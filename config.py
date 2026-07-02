import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "madlan_crm.db"
BACKUPS_DIR = BASE_DIR / "db" / "backups"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"

FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "").strip()

# city key -> (display label, Madlan URL slug)
CITIES = {
    "tel_aviv": {"label": "Tel Aviv", "slug": "תל-אביב-יפו-ישראל"},
    "jerusalem": {"label": "Jerusalem", "slug": "ירושלים-ישראל"},
    "haifa": {"label": "Haifa", "slug": "חיפה-ישראל"},
    "ramat_gan": {"label": "Ramat Gan", "slug": "רמת-גן-ישראל"},
    "netanya": {"label": "Netanya", "slug": "נתניה-ישראל"},
    "rishon_lezion": {"label": "Rishon LeZion", "slug": "ראשון-לציון-ישראל"},
}

DIRECTORY_BASE_URL = "https://www.madlan.co.il/madad-search/"
PROFILE_URL_MARKER = "/agentsOffice/"

SCRAPE_BATCH_TARGET = 50
POLITE_DELAY_MIN = 1.5
POLITE_DELAY_MAX = 2.0

# Firecrawl needs a long client-side render wait for Madlan profile pages —
# confirmed via live testing: 6s wait returns an empty accessibility-widget
# shell, 15s wait returns the fully hydrated page (name/phone/website).
FIRECRAWL_PROFILE_WAIT_MS = 15000
FIRECRAWL_DIRECTORY_WAIT_MS = 8000

# Madlan's profile pages are intermittently blocked for automated renderers —
# confirmed via live testing (~8% single-attempt success rate). A bounded retry
# loop recovers most of these without risking unbounded credit spend per agency.
PROFILE_FETCH_MAX_ATTEMPTS = 5
PROFILE_FETCH_RETRY_DELAY_MIN = 3.0
PROFILE_FETCH_RETRY_DELAY_MAX = 6.0

FOLLOW_UP_DUE_DAYS = 3

ENRICHMENT_TIMEOUT_SECONDS = 10

FLASK_PORT = 5000
