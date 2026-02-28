import os
from datetime import datetime
from zoneinfo import ZoneInfo

IL_TZ = ZoneInfo("Asia/Jerusalem")


def now_il():
    """Return current datetime in Israel timezone."""
    return datetime.now(IL_TZ)

# --- Station Definitions (fixed list) ---
STATIONS = [
    {
        "id": "maagal60a",
        "name": "Maagal 60 - A",
        "name_he": "המעגל 60 - A",
        "address": "המעגל 60, קריית אונו",
        "url": "https://account.afconev.co.il/findCharger?32.0482749,34.8653581,20z,%D7%94%D7%9E%D7%A2%D7%92%D7%9C%2060,1087st,1795sk",
        "lat": 32.0482749,
        "lng": 34.8653581,
    },
    {
        "id": "maagal60b",
        "name": "Maagal 60 - B",
        "name_he": "המעגל 60 - B",
        "address": "המעגל 60, קריית אונו",
        "url": "https://account.afconev.co.il/findCharger?32.0482749,34.8653581,20z,%D7%94%D7%9E%D7%A2%D7%92%D7%9C%2060,1087st,1796sk",
        "lat": 32.0482749,
        "lng": 34.8653581,
    },
    {
        "id": "maagal2a",
        "name": "Maagal 2 - A",
        "name_he": "המעגל 2 - A",
        "address": "המעגל 2, קריית אונו",
        "url": "https://account.afconev.co.il/findCharger?32.0482749,34.8653581,20z,%D7%94%D7%9E%D7%A2%D7%92%D7%9C%202,3982st,5851sk",
        "lat": 32.0482749,
        "lng": 34.8653581,
    },
    {
        "id": "maagal2b",
        "name": "Maagal 2 - B",
        "name_he": "המעגל 2 - B",
        "address": "המעגל 2, קריית אונו",
        "url": "https://account.afconev.co.il/findCharger?32.0482749,34.8653581,20z,%D7%94%D7%9E%D7%A2%D7%92%D7%9C%202,3982st,5852sk",
        "lat": 32.0482749,
        "lng": 34.8653581,
    },
]

# --- Scraping ---
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "40"))  # seconds

# --- Email (SMTP) ---
SMTP_ENABLED = os.environ.get("SMTP_ENABLED", "false").lower() == "true"
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "")
SMTP_TO = os.environ.get("SMTP_TO", "")  # comma-separated

# --- Database ---
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# --- Flask ---
SECRET_KEY = os.environ.get("SECRET_KEY", "ev-charger-monitor-secret")
