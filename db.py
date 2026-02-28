"""
PostgreSQL persistence layer for scraper state and timeline data.
Falls back to JSON files when DATABASE_URL is not set.
"""
import json
import logging
import os
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

_conn = None


def get_conn(database_url):
    global _conn
    if not database_url:
        return None
    try:
        if _conn is None or _conn.closed:
            _conn = psycopg2.connect(database_url, sslmode="require")
            _conn.autocommit = True
        return _conn
    except Exception as e:
        logger.error(f"DB connection error: {e}")
        _conn = None
        return None


def init_tables(database_url):
    conn = get_conn(database_url)
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scraper_state (
                    station_id TEXT PRIMARY KEY,
                    status TEXT,
                    last_check TEXT,
                    in_use_since TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS status_history (
                    id SERIAL PRIMARY KEY,
                    station_id TEXT,
                    station_name TEXT,
                    old_status TEXT,
                    new_status TEXT,
                    timestamp TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS timeline_checks (
                    id SERIAL PRIMARY KEY,
                    station_id TEXT,
                    station_name TEXT,
                    status TEXT,
                    timestamp TEXT
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_timeline_ts
                ON timeline_checks (timestamp)
            """)
        logger.info("Database tables initialized")
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False


# --- Scraper state ---

def save_statuses(database_url, statuses, in_use_since):
    conn = get_conn(database_url)
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            for sid, info in statuses.items():
                cur.execute("""
                    INSERT INTO scraper_state (station_id, status, last_check, in_use_since)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (station_id) DO UPDATE
                    SET status = EXCLUDED.status,
                        last_check = EXCLUDED.last_check,
                        in_use_since = EXCLUDED.in_use_since
                """, (sid, info["status"], info["last_check"], info.get("in_use_since")))
    except Exception as e:
        logger.error(f"Error saving statuses: {e}")


def load_statuses(database_url):
    conn = get_conn(database_url)
    if not conn:
        return {}, {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM scraper_state")
            rows = cur.fetchall()
        statuses = {}
        in_use_since = {}
        for r in rows:
            statuses[r["station_id"]] = {
                "status": r["status"],
                "last_check": r["last_check"],
                "in_use_since": r["in_use_since"],
            }
            if r["in_use_since"]:
                in_use_since[r["station_id"]] = r["in_use_since"]
        return statuses, in_use_since
    except Exception as e:
        logger.error(f"Error loading statuses: {e}")
        return {}, {}


def save_history_event(database_url, event):
    conn = get_conn(database_url)
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO status_history (station_id, station_name, old_status, new_status, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            """, (event["station_id"], event["station_name"],
                  event["old_status"], event["new_status"], event["timestamp"]))
    except Exception as e:
        logger.error(f"Error saving history event: {e}")


def load_history(database_url, limit=200):
    conn = get_conn(database_url)
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT station_id, station_name, old_status, new_status, timestamp "
                "FROM status_history ORDER BY id DESC LIMIT %s", (limit,))
            rows = cur.fetchall()
        return list(reversed(rows))
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        return []


# --- Timeline checks ---

def save_timeline_checks(database_url, checks):
    conn = get_conn(database_url)
    if not conn or not checks:
        return
    try:
        with conn.cursor() as cur:
            for c in checks:
                cur.execute("""
                    INSERT INTO timeline_checks (station_id, station_name, status, timestamp)
                    VALUES (%s, %s, %s, %s)
                """, (c["station_id"], c["station_name"], c["status"], c["timestamp"]))
    except Exception as e:
        logger.error(f"Error saving timeline checks: {e}")


def load_timeline(database_url, cutoff_iso):
    conn = get_conn(database_url)
    if not conn:
        return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT station_id, station_name, status, timestamp "
                "FROM timeline_checks WHERE timestamp >= %s ORDER BY timestamp",
                (cutoff_iso,))
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Error loading timeline: {e}")
        return []


def prune_timeline(database_url, cutoff_iso):
    conn = get_conn(database_url)
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM timeline_checks WHERE timestamp < %s", (cutoff_iso,))
    except Exception as e:
        logger.error(f"Error pruning timeline: {e}")


def prune_history(database_url, max_rows=200):
    conn = get_conn(database_url)
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM status_history
                WHERE id NOT IN (
                    SELECT id FROM status_history ORDER BY id DESC LIMIT %s
                )
            """, (max_rows,))
    except Exception as e:
        logger.error(f"Error pruning history: {e}")
