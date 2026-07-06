#!/usr/bin/env python3
from pathlib import Path
import sys
from flask import Flask, jsonify, render_template


ANALYZERS_DIR = Path(__file__).resolve().parents[1] / "analyzers"
sys.path.insert(0, str(ANALYZERS_DIR))

import conntrack_analyzer  # noqa: E402
import log_analyzer  # noqa: E402


app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")

@app.route('/api/blocked')
def get_blocked():
    return jsonify(log_analyzer.analyze_logs('/var/log/firewall/dropped.log'))

@app.route("/api/connections")
def get_connections():
    return jsonify(conntrack_analyzer.analyze_connections())


@app.route("/api/health")
def get_health():
    return jsonify({"status": "ok", "service": "monitoring-dashboard"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
