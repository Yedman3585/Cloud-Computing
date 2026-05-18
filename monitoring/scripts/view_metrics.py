#!/usr/bin/env python3

import json
import os

METRICS_FILE = "/var/log/firewall/metrics.json"

def view_metrics():
    if not os.path.exists(METRICS_FILE):
        print("No metrics file found")
        return
    
    with open(METRICS_FILE, 'r') as f:
        data = json.load(f)
    
    print("=" * 40)
    print("FIREWALL METRICS")
    print("=" * 40)
    print(f"Timestamp:      {data.get('timestamp', 'N/A')}")
    print(f"nftables rules: {data.get('nftables_rules', 0)}")
    print(f"Connections:    {data.get('connections', 0)}")
    print("=" * 40)

if __name__ == "__main__":
    view_metrics()
