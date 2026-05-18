#!/usr/bin/env python3

from flask import Flask, jsonify, render_template
import sys
import os

sys.path.append('/home/grp5user/20261_group_05/monitoring/analyzers')
import log_analyzer
import conntrack_analyzer

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/blocked')
def get_blocked():
    return jsonify(log_analyzer.analyze_logs())

@app.route('/api/connections')
def get_connections():
    return jsonify(conntrack_analyzer.analyze_connections())

@app.route('/api/health')
def get_health():
    return jsonify({"status": "ok", "service": "monitoring-dashboard"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
