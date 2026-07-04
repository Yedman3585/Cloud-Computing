#!/usr/bin/env python3

import re
from collections import Counter
from pathlib import Path

# Matches IPv4 (SRC=1.2.3.4) and IPv6 (SRC=fd00:20::11) source addresses
# from netfilter/ulogd LOGEMU-style drop log lines.
SRC_RE = re.compile(r'SRC=([0-9a-fA-F:.]+)')


def analyze_logs(log_path="/var/log/firewall/dropped.log"):
    blocked_ips = Counter()
    blocked_ipv4 = Counter()
    blocked_ipv6 = Counter()
    path = Path(log_path)

    if not path.exists():
        return {
            "total": 0,
            "blocked_ips": {},
            "blocked_ipv4": {},
            "blocked_ipv6": {},
            "message": f"log file {log_path} not found",
        }

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            match = SRC_RE.search(line)
            if not match:
                continue
            ip = match.group(1)
            blocked_ips[ip] += 1
            if ":" in ip:
                blocked_ipv6[ip] += 1
            else:
                blocked_ipv4[ip] += 1

    return {
        "total": sum(blocked_ips.values()),
        "blocked_ips": dict(blocked_ips.most_common(10)),
        "blocked_ipv4": dict(blocked_ipv4.most_common(10)),
        "blocked_ipv6": dict(blocked_ipv6.most_common(10)),
    }


if __name__ == "__main__":
    print("Blocked IP analysis:")
    stats = analyze_logs()
    for ip, count in stats.get("blocked_ips", {}).items():
        print(f"   {ip}: {count} blocks")