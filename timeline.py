"""
Persistent timeline storage for Gantt chart.
Stores status change events in a JSON file, retaining last 3 days.
"""
import json
import os
import threading
import logging
from datetime import datetime, timedelta

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
                logger.info(f"Loaded {len(data)} timeline events from {self.filepath}")
                return data
            except Exception as e:
                logger.error(f"Error loading timeline: {e}")
        return []

    def _save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._events, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving timeline: {e}")

    def _prune(self):
        """Remove events older than RETENTION_DAYS."""
        cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).isoformat()
        self._events = [e for e in self._events if e.get("timestamp", "") >= cutoff]

    def add_event(self, station_id, station_name, old_status, new_status, timestamp):
        with self._lock:
            self._events.append({
                "station_id": station_id,
                "station_name": station_name,
                "old_status": old_status,
                "new_status": new_status,
                "timestamp": timestamp,
            })
            self._prune()
            self._save()

    def get_timeline(self, days=RETENTION_DAYS):
        """Return events from the last N days, sorted by timestamp."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self._lock:
            return [e for e in self._events if e.get("timestamp", "") >= cutoff]
