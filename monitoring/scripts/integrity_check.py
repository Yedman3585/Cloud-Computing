#!/usr/bin/env python3

import hashlib
import json
import os
from datetime import datetime

RULES_FILE = "/home/grp5user/20261_group_05/generated.nft"
HASH_FILE = "/var/log/firewall/rules_hash.json"

def calculate_hash():
    if not os.path.exists(RULES_FILE):
        return None
    with open(RULES_FILE, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def check_integrity():
    current_hash = calculate_hash()
    
    if not os.path.exists(HASH_FILE):
        with open(HASH_FILE, 'w') as f:
            json.dump({"hash": current_hash, "timestamp": str(datetime.now())}, f)
        print("First run: hash saved")
        return True
    
    with open(HASH_FILE, 'r') as f:
        saved = json.load(f)
    
    if saved["hash"] == current_hash:
        print("OK: Rules unchanged")
        return True
    else:
        print("WARNING: Rules have been changed!")
        print(f"  Old hash: {saved['hash']}")
        print(f"  New hash: {current_hash}")
        return False

if __name__ == "__main__":
    check_integrity()
