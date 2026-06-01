#!/usr/bin/env python3
import argparse
import subprocess
import sys


def kubectl_get(kind: str, namespace: str) -> str:
    return subprocess.check_output(
        ["kubectl", "get", kind, "-n", namespace],
        stderr=subprocess.STDOUT,
        text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Check firewall Kubernetes deployment")
    parser.add_argument("--namespace", default="firewall")
    args = parser.parse_args()

    try:
        output = kubectl_get("deployment", args.namespace)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(output)
    deployments = max(len(output.strip().splitlines()) - 1, 0)
    if deployments > 0:
        print(f"[PASS] Found {deployments} deployment(s) in namespace {args.namespace}")
        return 0

    print(f"[FAIL] No deployments found in namespace {args.namespace}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
