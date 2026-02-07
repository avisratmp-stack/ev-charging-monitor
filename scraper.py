import threading
import time
import logging
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class StationScraper:
    def __init__(self, stations, check_interval, on_status_change, on_station_checked=None, on_cycle_complete=None):
        self.stations = stations
        self.check_interval = check_interval
        self.on_status_change = on_status_change
        self.on_station_checked = on_station_checked
        self.on_cycle_complete = on_cycle_complete

        self._lock = threading.Lock()
        self._statuses = {}
        self._in_use_since = {}  # track when each station entered "in_use"
        self._history = []
        self._running = False
        self._driver = None
        self._thread = None
        self._cycle_count = 0

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Scraper thread started")

    def stop(self):
        self._running = False
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass

    def get_all_statuses(self):
        with self._lock:
            return dict(self._statuses)

    def get_history(self, limit=50):
        with self._lock:
            return list(self._history[-limit:])

    def _init_driver(self):
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1280,720")
        opts.add_argument("--lang=he")
        service = Service(ChromeDriverManager().install())
        self._driver = webdriver.Chrome(service=service, options=opts)
        self._driver.set_page_load_timeout(30)
        logger.info("Chrome WebDriver initialized")

    def _check_station(self, station):
        try:
            self._driver.get(station["url"])
            time.sleep(10)
            source = self._driver.page_source

            # Skip button elements that may contain status text
            lines = source.split("\n")
            for line in lines:
                stripped = line.strip()
                if '<button tabindex="-1"' in stripped:
                    continue
                if "Available to charge" in stripped or "\u05d6\u05de\u05d9\u05df \u05dc\u05d8\u05e2\u05d9\u05e0\u05d4" in stripped:
                    return "available"
                if "In Use" in stripped or "\u05d1\u05e9\u05d9\u05de\u05d5\u05e9" in stripped:
                    return "in_use"

            return "unknown"
        except Exception as e:
            logger.error(f"Error checking {station['id']}: {e}")
            return "error"

    def _loop(self):
        self._init_driver()

        while self._running:
            try:
                for station in self.stations:
                    if not self._running:
                        break

                    new_status = self._check_station(station)
                    now = datetime.now().isoformat()

                    with self._lock:
                        old_entry = self._statuses.get(station["id"])
                        old_status = old_entry["status"] if old_entry else None

                        # Track when station entered "in_use"
                        if new_status == "in_use" and old_status != "in_use":
                            self._in_use_since[station["id"]] = now
                        elif new_status != "in_use":
                            self._in_use_since.pop(station["id"], None)

                        self._statuses[station["id"]] = {
                            "status": new_status,
                            "last_check": now,
                            "in_use_since": self._in_use_since.get(station["id"]),
                        }

                        if old_status != new_status:
                            event = {
                                "station_id": station["id"],
                                "station_name": station["name"],
                                "old_status": old_status,
                                "new_status": new_status,
                                "timestamp": now,
                            }
                            self._history.append(event)
                            if len(self._history) > 200:
                                self._history = self._history[-200:]

                    # Always notify UI of the latest check time
                    if self.on_station_checked:
                        in_use_since = self._in_use_since.get(station["id"])
                        self.on_station_checked(
                            station["id"], new_status, now, in_use_since
                        )

                    if old_status != new_status:
                        self.on_status_change(
                            station["id"],
                            station["name"],
                            old_status,
                            new_status,
                            now,
                        )

                self._cycle_count += 1

                # Notify UI that cycle is done, countdown begins
                if self.on_cycle_complete:
                    self.on_cycle_complete(self.check_interval)

                # Proactive driver restart every 100 cycles to prevent memory leaks
                if self._cycle_count % 100 == 0:
                    logger.info("Proactive driver restart for memory management")
                    try:
                        self._driver.quit()
                    except Exception:
                        pass
                    self._init_driver()

            except WebDriverException as e:
                logger.error(f"WebDriver crashed: {e}, reinitializing...")
                try:
                    self._driver.quit()
                except Exception:
                    pass
                self._init_driver()
            except Exception as e:
                logger.error(f"Unexpected error in scraper loop: {e}")

            # Sleep in small increments for clean shutdown
            for _ in range(self.check_interval):
                if not self._running:
                    break
                time.sleep(1)

        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
