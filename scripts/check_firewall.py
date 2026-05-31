import subprocess
import sys

try:
    output = subprocess.check_output(
        ["kubectl", "get", "pods", "-n", "firewall"],
        stderr=subprocess.STDOUT
    ).decode()

    print(output)

    if "Running" in output:
        print("[PASS] Firewall pods running")
    else:
        print("[FAIL] No running pods")
        sys.exit(1)

except Exception as e:
    print("[ERROR]", e)
    sys.exit(1)