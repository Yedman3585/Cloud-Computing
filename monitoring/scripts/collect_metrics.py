#!/usr/bin/env python3
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path


def run_count(command: list[str]) -> str | int:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return 0
    return result.stdout.strip() if result.returncode == 0 else 0


def collect_metrics() -> dict:
    ruleset = run_count(["nft", "list", "ruleset"])
    return {
        "timestamp": datetime.now().isoformat(),
        "nftables_rules": str(ruleset).count("counter"),
        "connections": run_count(["conntrack", "-C"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect firewall metrics")
    parser.add_argument("--output", default="monitoring/data/metrics.json")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    metrics = collect_metrics()
    output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
