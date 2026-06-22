#!/usr/bin/env python3

import re
from collections import Counter
from pathlib import Path

def analyze_logs(log_path="/var/log/firewall/dropped.log"):
    blocked_ips = Counter()
    path = Path(log_path)

    if not path.exists():
        return {
            "total": 0,
            "blocked_ips": {},
            "message": f"log file {log_path} not found",
        }
    
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            match = re.search(r'SRC=(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                blocked_ips[match.group(1)] += 1
    
    top_blocked = dict(blocked_ips.most_common(10))
    return {
        "total": sum(blocked_ips.values()),
        "blocked_ips": top_blocked,
    }

if __name__ == "__main__":
    print("Blocked IP analysis:")
    stats = analyze_logs()
    for ip, count in stats.get("blocked_ips", {}).items():
        print(f"   {ip}: {count} blocks")
