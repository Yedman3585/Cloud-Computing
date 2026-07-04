#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


def run_text(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def docker_exec(container: str, command: list[str]) -> list[str]:
    return ["docker", "exec", container, *command]


def collect_metrics(container: str) -> dict:
    ruleset = run_text(docker_exec(container, ["nft", "list", "ruleset"]))
    connections = run_text(docker_exec(container, ["conntrack", "-C"]))
    return {
        "timestamp": datetime.now().isoformat(),
        "container": container,
        "nftables_rules": ruleset.count("counter"),
        "connections": connections or 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect firewall metrics from a lab container")
    parser.add_argument("--container", default=os.environ.get("FIREWALL_METRICS_CONTAINER", "fw1"))
    parser.add_argument("--output", default="monitoring/data/metrics.json")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    metrics = collect_metrics(args.container)
    output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
