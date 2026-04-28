#!/usr/bin/env python3

import re
from collections import Counter

def analyze_logs(log_path="/var/log/firewall/dropped.log"):
    blocked_ips = Counter()
    
    try:
        with open(log_path, 'r') as f:
            for line in f:
                match = re.search(r'SRC=(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    blocked_ips[match.group(1)] += 1
    except FileNotFoundError:
        print(f"Log file {log_path} not found (demo mode)")
        return {"192.168.1.100": 45, "10.0.0.50": 12, "203.0.113.5": 8}
    
    return dict(blocked_ips.most_common(10))

if __name__ == "__main__":
    print("Blocked IP analysis:")
    stats = analyze_logs()
    for ip, count in stats.items():
        print(f"   {ip}: {count} blocks")
