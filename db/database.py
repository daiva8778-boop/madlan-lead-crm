from datetime import datetime
from urllib.parse import urlparse, parse_qs

import psycopg2
import psycopg2.extras
import psycopg2.pool

import config

_pool = None


def _resolve_via_public_dns(hostname):
    """Some local networks' default DNS server fails to resolve Neon's
    hostname even though the hostname is fine (confirmed: Google's DNS
    resolves it instantly). Query 8.8.8.8 directly, bypassing whatever's
    configured as the system resolver, rather than changing that system-wide
    setting. Returns None if this doesn't work for any reason (e.g. outbound
    DNS-over-UDP blocked) so the caller can fall back to normal resolution —
    harmless in environments (like cloud hosts) where system DNS is fine."""
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
        resolver.timeout = 5
        resolver.lifetime = 5
        answer = resolver.resolve(hostname, "A")
        return str(answer[0])
    except Exception:
        return None


def _connect_kwargs():
    """Builds psycopg2 connection kwargs from DATABASE_URL, with hostaddr set
    to a directly-resolved IP when possible. Passing both `host` (kept, for
    TLS/SNI certificate verification) and `hostaddr` (the resolved IP) lets
    libpq skip its own hostname resolution entirely for the actual connection."""
    parsed = urlparse(config.DATABASE_URL)
    query = parse_qs(parsed.query)
    kwargs = {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "user": parsed.username,
        "password": parsed.password,
        "dbname": parsed.path.lstrip("/"),
        "sslmode": query.get("sslmode", ["require"])[0],
    }
    resolved_ip = _resolve_via_public_dns(parsed.hostname)
    if resolved_ip:
        kwargs["hostaddr"] = resolved_ip
    return kwargs


def _get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(1, 10, **_connect_kwargs())
    return _pool


class _CursorResult:
    """Thin shim so call sites written for sqlite3 (fetchone/fetchall, dict-like
    rows, .lastrowid) keep working unchanged against psycopg2."""

    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        # only meaningful right after an INSERT ... RETURNING id
        row = self._cursor.fetchone()
        return row["id"] if row else None


class PgConnection:
    """Wraps a psycopg2 connection so existing sqlite3-style call sites
    (conn.execute("... ? ...", params), row["col"] access, conn.commit(),
    conn.close()) keep working without touching every route file."""

    def __init__(self, raw_conn, pool):
        self._raw = raw_conn
        self._pool = pool

    def execute(self, sql, params=()):
        pg_sql = sql.replace("?", "%s")
        cur = self._raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(pg_sql, params)
        return _CursorResult(cur)

    def executescript(self, sql_text):
        cur = self._raw.cursor()
        cur.execute(sql_text)
        self._raw.commit()

    def commit(self):
        self._raw.commit()

    def close(self):
        self._pool.putconn(self._raw)


def get_db():
    pool = _get_pool()
    raw_conn = pool.getconn()
    return PgConnection(raw_conn, pool)


def init_db():
    conn = get_db()
    try:
        with open(config.SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    finally:
        conn.close()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def backup_if_needed():
    """No-op: Neon (or whichever Postgres host DATABASE_URL points at) handles
    automated backups / point-in-time recovery itself, unlike the old local
    SQLite file which needed the app to make its own copies."""
    return None
