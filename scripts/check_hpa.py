import subprocess
import sys

try:
    output = subprocess.check_output(
        ["kubectl", "get", "hpa", "-n", "firewall"],
        stderr=subprocess.STDOUT
    ).decode()

    print(output)

    # Count HPA entries (excluding header)
    hpas = len(output.strip().splitlines()) - 1

    if hpas > 0:
        print(f"[PASS] Found {hpas} HPA(s) in firewall namespace")
        sys.exit(0)

    print("[FAIL] No HPAs found in firewall namespace")
    sys.exit(1)

except Exception as e:
    print("[ERROR]", e)
    sys.exit(1)