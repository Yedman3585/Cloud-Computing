#!/usr/bin/env python3
"""Network bandwidth per interface from /proc/net/dev.

Same data source that iftop / cbm use: the kernel byte counters.
We take two samples 1 second apart and compute bytes/sec per interface.
"""
import time

PROC_NET_DEV = "/proc/net/dev"


def _read_counters():
    counters = {}
    try:
        with open(PROC_NET_DEV) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return None
    for line in lines[2:]:           # first two lines are headers
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        fields = rest.split()
        if len(fields) < 16:
            continue
        counters[name.strip()] = (int(fields[0]), int(fields[8]))  # rx, tx bytes
    return counters


def _human(bps):
    value = float(bps)
    for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
        if value < 1024 or unit == "GB/s":
            return f"{value:.1f} {unit}"
        value /= 1024


def get_bandwidth(interval=1.0, skip_loopback=True):
    first = _read_counters()
    if first is None:
        return {"interfaces": {}, "message": "/proc/net/dev not available"}
    time.sleep(interval)
    second = _read_counters()

    result = {}
    for name, (rx2, tx2) in second.items():
        if skip_loopback and name == "lo":
            continue
        rx1, tx1 = first.get(name, (rx2, tx2))
        rx_rate = max(0, rx2 - rx1) / interval
        tx_rate = max(0, tx2 - tx1) / interval
        result[name] = {
            "rx_bytes_per_sec": int(rx_rate),
            "tx_bytes_per_sec": int(tx_rate),
            "rx_human": _human(rx_rate),
            "tx_human": _human(tx_rate),
        }
    return {"interfaces": result}


if __name__ == "__main__":
    data = get_bandwidth()
    print("Bandwidth per interface (1s sample):")
    for name, stats in data.get("interfaces", {}).items():
        print(f"  {name}: down {stats['rx_human']}  up {stats['tx_human']}")
