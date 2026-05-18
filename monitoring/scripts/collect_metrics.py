#!/usr/bin/env python3

import subprocess
import json
import os
from datetime import datetime

METRICS_FILE = "/var/log/firewall/metrics.json"

def get_nftables_rules_count():
    try:
        result = subprocess.run(["nft", "list", "ruleset"], capture_output=True, text=True)
        return result.stdout.count("add rule")
    except:
        return 0

def get_connection_count():
    try:
        result = subprocess.run(["conntrack", "-C"], capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return 0

def collect_metrics():
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "nftables_rules": get_nftables_rules_count(),
        "connections": get_connection_count()
    }
    return metrics

if __name__ == "__main__":
    os.makedirs("/var/log/firewall", exist_ok=True)
    
    metrics = collect_metrics()
    
    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f, indent=2)
    
    print("Metrics saved to", METRICS_FILE)
    print(json.dumps(metrics, indent=2))
