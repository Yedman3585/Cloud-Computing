#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


def calculate_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check rendered firewall rules integrity")
    parser.add_argument("--rules-file", default="/etc/nftables.conf")
    parser.add_argument("--state-file", default="monitoring/data/rules_hash.json")
    args = parser.parse_args()

    rules_file = Path(args.rules_file)
    state_file = Path(args.state_file)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    current_hash = calculate_hash(rules_file)
    if current_hash is None:
        print(f"[WARN] Rules file not found: {rules_file}")
        return 1

    if not state_file.exists():
        state_file.write_text(
            json.dumps({"hash": current_hash, "timestamp": datetime.now().isoformat()}, indent=2),
            encoding="utf-8",
        )
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
