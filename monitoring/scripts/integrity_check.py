#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path


def read_container_file(container: str, path: str) -> bytes | None:
    try:
        result = subprocess.run(
            ["docker", "exec", container, "cat", path],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    return result.stdout if result.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Check deployed firewall rules integrity")
    parser.add_argument("--container", default=os.environ.get("FIREWALL_METRICS_CONTAINER", "fw1"))
    parser.add_argument("--rules-file", default="/etc/nftables.conf")
    parser.add_argument("--state-file", default="monitoring/data/rules_hash.json")
    args = parser.parse_args()

    state_file = Path(args.state_file)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    rules = read_container_file(args.container, args.rules_file)
    if rules is None:
        print(f"[WARN] Could not read {args.rules_file} from container {args.container}")
        return 1

    current_hash = hashlib.sha256(rules).hexdigest()
    current = {
        "hash": current_hash,
        "timestamp": datetime.now().isoformat(),
        "container": args.container,
        "rules_file": args.rules_file,
    }

    if not state_file.exists():
        state_file.write_text(json.dumps(current, indent=2), encoding="utf-8")
        print("[PASS] First run: hash saved")
        return 0

    saved = json.loads(state_file.read_text(encoding="utf-8"))
    if saved.get("hash") == current_hash:
        print("[PASS] Rules unchanged")
        return 0

    print("[FAIL] Rules have changed")
    print(f"old: {saved.get('hash')}")
    print(f"new: {current_hash}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
