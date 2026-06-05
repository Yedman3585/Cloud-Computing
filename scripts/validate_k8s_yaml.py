#!/usr/bin/env python3
from pathlib import Path

import yaml


def main() -> int:
    manifest_dir = Path("k8s")
    paths = sorted(manifest_dir.glob("*.yaml"))
    if not paths:
        print("No Kubernetes YAML manifests found under k8s/")
        return 1

    for path in paths:
        with path.open(encoding="utf-8") as handle:
            documents = [doc for doc in yaml.safe_load_all(handle) if doc]
        if not documents:
            print(f"{path}: no YAML documents found")
            return 1
        for document in documents:
            if not document.get("apiVersion") or not document.get("kind"):
                print(f"{path}: missing apiVersion or kind")
                return 1
        print(f"ok {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
