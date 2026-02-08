"""
Persistent timeline storage for Gantt chart.
Records every status check (not just changes) as periodic snapshots.
Stores data in a JSON file, retaining last 3 days.
"""
import json
import os
import threading
import logging
from datetime import timedelta

from config import now_il

logger = logging.getLogger(__name__)

TIMELINE_FILE = os.environ.get("TIMELINE_FILE", "timeline_data.json")
RETENTION_DAYS = 3


class TimelineStore:
    def __init__(self, filepath=TIMELINE_FILE):
        self.filepath = filepath
        self._lock = threading.Lock()
        self._events = self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Handle old format (list of change events) - convert to new format
                if isinstance(data, list):
                    logger.info(f"Migrating {len(data)} old-format timeline events")
                    return data
                # New format: dict with "checks" key
                checks = data.get("checks", [])
                logger.info(f"Loaded {len(checks)} timeline check records")
                return checks
            except Exception as e:
                logger.error(f"Error loading timeline: {e}")
        return []

    def _save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({"checks": self._events}, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving timeline: {e}")

    def _prune(self):
        """Remove records older than RETENTION_DAYS."""
        cutoff = (now_il() - timedelta(days=RETENTION_DAYS)).isoformat()
        self._events = [e for e in self._events if e.get("timestamp", "") >= cutoff]

    def record_check(self, station_id, station_name, status, timestamp):
        """Record a single station check result."""
        with self._lock:
            self._events.append({
                "station_id": station_id,
                "station_name": station_name,
                "status": status,
                "timestamp": timestamp,
            })

    def save_cycle(self):
        """Save to disk and prune old data. Call once per cycle."""
        with self._lock:
            self._prune()
            self._save()

    def get_timeline(self, days=RETENTION_DAYS):
        """Return check records from the last N days."""
        cutoff = (now_il() - timedelta(days=days)).isoformat()
        with self._lock:
            return [e for e in self._events if e.get("timestamp", "") >= cutoff]
