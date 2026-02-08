import logging
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit

import config
from config import now_il
from scraper import StationScraper
from notifier import send_availability_email
from timeline import TimelineStore

SW_VERSION = now_il().strftime("%Y%m%d-%H%M%S")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
timeline_store = TimelineStore()


@app.after_request
def add_no_cache(response):
    if response.content_type and "text/html" in response.content_type:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def on_status_change(station_id, station_name, old_status, new_status, timestamp):
    socketio.emit("status_update", {
        "station_id": station_id,
        "station_name": station_name,
        "old_status": old_status,
        "new_status": new_status,
        "timestamp": timestamp,
    })
    send_availability_email(config, station_name, new_status, timestamp)
    logger.info(f"{station_name}: {old_status} -> {new_status}")


def on_station_checked(station_id, status, timestamp, in_use_since=None):
    # Record every check for the Gantt timeline
    station = next((s for s in config.STATIONS if s["id"] == station_id), None)
    station_name = station["name"] if station else station_id
    timeline_store.record_check(station_id, station_name, status, timestamp)

    socketio.emit("station_checked", {
        "station_id": station_id,
        "status": status,
        "last_check": timestamp,
        "in_use_since": in_use_since,
    })


def on_cycle_complete(interval):
    # Save timeline to disk once per cycle
    timeline_store.save_cycle()

    socketio.emit("cycle_complete", {
        "interval": interval,
    })


scraper = StationScraper(
    stations=config.STATIONS,
    check_interval=config.CHECK_INTERVAL,
    on_status_change=on_status_change,
    on_station_checked=on_station_checked,
    on_cycle_complete=on_cycle_complete,
)


@app.route("/")
def index():
    return render_template("index.html", stations=config.STATIONS, sw_version=SW_VERSION)


@app.route("/api/status")
def api_status():
    return jsonify({
        "statuses": scraper.get_all_statuses(),
        "history": scraper.get_history(limit=50),
    })


@app.route("/api/timeline")
def api_timeline():
    return jsonify(timeline_store.get_timeline())


@socketio.on("connect")
def handle_connect():
    emit("initial_state", {
        "statuses": scraper.get_all_statuses(),
        "history": scraper.get_history(limit=50),
    })


@socketio.on("request_refresh")
def handle_refresh():
    emit("initial_state", {
        "statuses": scraper.get_all_statuses(),
        "history": scraper.get_history(limit=50),
    })


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    scraper.start()
    socketio.run(app, host="0.0.0.0", port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
