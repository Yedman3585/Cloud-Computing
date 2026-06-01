#!/usr/bin/env python3
import argparse
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Check firewall Kubernetes service")
    parser.add_argument("--namespace", default="firewall")
    args = parser.parse_args()

    try:
        output = subprocess.check_output(
            ["kubectl", "get", "svc", "-n", args.namespace],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(output)
    services = max(len(output.strip().splitlines()) - 1, 0)
    if services > 0:
        print(f"[PASS] Found {services} service(s) in namespace {args.namespace}")
        return 0

    print(f"[FAIL] No service found in namespace {args.namespace}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
