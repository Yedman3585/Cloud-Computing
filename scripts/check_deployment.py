import subprocess
import sys

try:
    output = subprocess.check_output(
        ["kubectl", "get", "deployment", "-n", "firewall"],
        stderr=subprocess.STDOUT
    ).decode()

    print(output)

    # Count deployments (excluding header)
    deployments = len(output.strip().splitlines()) - 1

    if deployments > 0:
        print(f"[PASS] Found {deployments} deployment(s) in firewall namespace")
        sys.exit(0)

    print("[FAIL] No deployments found in firewall namespace")
    sys.exit(1)

except Exception as e:
    print("[ERROR]", e)
    sys.exit(1)