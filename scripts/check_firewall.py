#!/usr/bin/env python3
import argparse
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Check firewall Kubernetes pods")
    parser.add_argument("--namespace", default="firewall")
    parser.add_argument("--minimum-running", type=int, default=3)
    args = parser.parse_args()

    try:
        output = subprocess.check_output(
            ["kubectl", "get", "pods", "-n", args.namespace],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(output)
    running = output.count("Running")
    if running >= args.minimum_running:
        print(f"[PASS] {running} firewall pod(s) are running")
        return 0

    print(f"[FAIL] Only {running} firewall pod(s) are running")
    return 1


if __name__ == "__main__":
    sys.exit(main())
