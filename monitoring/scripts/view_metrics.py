#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="View collected firewall metrics")
    parser.add_argument("--input", default="monitoring/data/metrics.json")
    args = parser.parse_args()

    metrics_path = Path(args.input)
    if not metrics_path.exists():
        print(f"No metrics file found: {metrics_path}")
        return 1

    data = json.loads(metrics_path.read_text(encoding="utf-8"))
    print("=" * 40)
    print("FIREWALL METRICS")
    print("=" * 40)
    print(f"Timestamp:      {data.get('timestamp', 'N/A')}")
    print(f"nftables rules: {data.get('nftables_rules', 0)}")
    print(f"Connections:    {data.get('connections', 0)}")
    print("=" * 40)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
