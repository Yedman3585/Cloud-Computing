import subprocess
import sys

try:
    output = subprocess.check_output(
        ["kubectl", "get", "pods", "-n", "firewall"],
        stderr=subprocess.STDOUT
    ).decode()

    print(output)

    running = output.count("Running")

    if running >= 3:
        print("[PASS] Firewall deployment healthy")
        sys.exit(0)

    print("[FAIL] Firewall deployment unhealthy")
    sys.exit(1)

except Exception as e:
    print("[ERROR]", e)
    sys.exit(1)