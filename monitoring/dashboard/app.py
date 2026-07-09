#!/usr/bin/env python3
from pathlib import Path
import sys
import threading
import time
from flask import Flask, jsonify, render_template

ANALYZERS_DIR = Path(__file__).resolve().parents[1] / "analyzers"
sys.path.insert(0, str(ANALYZERS_DIR))

import conntrack_analyzer
import log_analyzer
import bandwidth_analyzer

app = Flask(__name__)

# Cache bandwidth result in background so API responds instantly
_bandwidth_cache = {"interfaces": {}}
_bandwidth_lock = threading.Lock()


def _bandwidth_updater():
    global _bandwidth_cache
    while True:
        result = bandwidth_analyzer.get_bandwidth(interval=1.0)
        with _bandwidth_lock:
            _bandwidth_cache = result
        time.sleep(3)


_bg = threading.Thread(target=_bandwidth_updater, daemon=True)
_bg.start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/blocked")
def get_blocked():
    return jsonify(
        log_analyzer.analyze_logs("/var/log/firewall/dropped.log")
    )


@app.route("/api/connections")
def get_connections():
    return jsonify(conntrack_analyzer.analyze_connections())


@app.route("/api/bandwidth")
def get_bandwidth():
    with _bandwidth_lock:
        return jsonify(_bandwidth_cache)


@app.route("/api/health")
def get_health():
    return jsonify({"status": "ok", "service": "monitoring-dashboard"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)