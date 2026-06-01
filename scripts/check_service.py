import subprocess
import sys

try:
    output = subprocess.check_output(
        ["kubectl", "get", "svc", "-n", "firewall"],
        stderr=subprocess.STDOUT
    ).decode()

    print(output)

    # Count service entries (excluding header line)
    services = len(output.strip().splitlines()) - 1

    if services > 0:
        print(f"[PASS] Found {services} service(s) in firewall namespace")
        sys.exit(0)

    print("[FAIL] No services found in firewall namespace")
    sys.exit(1)

except Exception as e:
    print("[ERROR]", e)
    sys.exit(1)