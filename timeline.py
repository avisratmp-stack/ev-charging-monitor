"""
Persistent timeline storage for Gantt chart.
Records every status check (not just changes) as periodic snapshots.
Uses PostgreSQL when DATABASE_URL is set, falls back to JSON file.
"""
import json
import os
import threading
import logging
from datetime import timedelta

import config
from config import now_il
import db

logger = logging.getLogger(__name__)

TIMELINE_FILE = os.environ.get("TIMELINE_FILE", "timeline_data.json")
RETENTION_DAYS = 3


class TimelineStore:
    def __init__(self, filepath=TIMELINE_FILE):
        self.filepath = filepath
        self._db_url = config.DATABASE_URL
        self._lock = threading.Lock()
        self._pending = []  # buffer checks until save_cycle
        self._events = self._load()

    def _load(self):
        if self._db_url:
            cutoff = (now_il() - timedelta(days=RETENTION_DAYS)).isoformat()
            checks = db.load_timeline(self._db_url, cutoff)
            logger.info(f"Loaded {len(checks)} timeline checks from DB")
            return [dict(c) for c in checks]

        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    logger.info(f"Migrating {len(data)} old-format timeline events")
                    return data
                checks = data.get("checks", [])
                logger.info(f"Loaded {len(checks)} timeline check records")
                return checks
            except Exception as e:
                logger.error(f"Error loading timeline: {e}")
        return []

    def _save(self):
        if self._db_url:
            if self._pending:
                db.save_timeline_checks(self._db_url, self._pending)
                self._pending = []
            cutoff = (now_il() - timedelta(days=RETENTION_DAYS)).isoformat()
            db.prune_timeline(self._db_url, cutoff)
            return

        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({"checks": self._events}, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving timeline: {e}")

    def _prune(self):
        cutoff = (now_il() - timedelta(days=RETENTION_DAYS)).isoformat()
        self._events = [e for e in self._events if e.get("timestamp", "") >= cutoff]

    def record_check(self, station_id, station_name, status, timestamp):
        with self._lock:
            check = {
                "station_id": station_id,
                "station_name": station_name,
                "status": status,
                "timestamp": timestamp,
            }
            self._events.append(check)
            if self._db_url:
                self._pending.append(check)

    def save_cycle(self):
        with self._lock:
            self._prune()
            self._save()

    def get_timeline(self, days=RETENTION_DAYS):
        cutoff = (now_il() - timedelta(days=days)).isoformat()
        with self._lock:
            return [e for e in self._events if e.get("timestamp", "") >= cutoff]
