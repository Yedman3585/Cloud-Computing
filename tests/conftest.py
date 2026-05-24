import os
import time
import subprocess
import socket
from typing import Optional
import pytest
import requests

# ---------------------------------------------------------------------------
# IP constants — read from env vars (set in docker-compose.yml)
# Defaults match the static IPs assigned in docker-compose.yml
# ---------------------------------------------------------------------------
FW1_MGMT   = os.environ.get("FW1_MGMT_IP",     "172.20.0.11")
FW2_MGMT   = os.environ.get("FW2_MGMT_IP",     "172.20.0.12")
FW3_MGMT   = os.environ.get("FW3_MGMT_IP",     "172.20.0.13")

FW1_FRONT  = os.environ.get("FW1_FRONTEND_IP", "172.21.0.11")
FW2_FRONT  = os.environ.get("FW2_FRONTEND_IP", "172.21.0.12")
FW3_FRONT  = os.environ.get("FW3_FRONTEND_IP", "172.21.0.13")

VIRTUAL_IP = os.environ.get("VIRTUAL_IP",      "172.20.0.100")
SERVER1_IP = os.environ.get("SERVER1_IP",      "172.22.0.31")
SERVER2_IP = os.environ.get("SERVER2_IP",      "172.22.0.32")

ALL_FW_MGMT  = [FW1_MGMT,  FW2_MGMT,  FW3_MGMT]
ALL_FW_FRONT = [FW1_FRONT, FW2_FRONT, FW3_FRONT]
FW_CONTAINERS = ["fw1", "fw2", "fw3"]


# ---------------------------------------------------------------------------
# Low-level helper functions (not fixtures — imported directly by test files)
# ---------------------------------------------------------------------------

def run_in_container(container: str, command: str) -> tuple[int, str, str]:
    """
    Run a shell command inside a Docker container and return the result.

    Args:
        container: container name, e.g. "fw1"
        command:   shell command string, e.g. "nft list ruleset"

    Returns:
        (return_code, stdout, stderr)
        return_code 0 = success, non-zero = failure
    """
    result = subprocess.run(
        ["docker", "exec", container, "bash", "-c", command],
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def ping(target_ip: str, from_container: str = None, count: int = 3) -> bool:
    """
    Ping target_ip. If from_container is given, runs inside that container.
    Returns True if at least one reply received.
    """
    cmd = f"ping -c {count} -W 2 {target_ip}"
    if from_container:
        rc, _, _ = run_in_container(from_container, cmd)
        return rc == 0
    result = subprocess.run(cmd.split(), capture_output=True)
    return result.returncode == 0


def tcp_connect(ip: str, port: int, timeout: float = 3.0) -> bool:
    """
    Try to open a TCP connection to ip:port.
    Returns True if connection succeeds (port open), False otherwise.
    This is the same as what curl or a browser does when connecting.
    """
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def get_vip_owner() -> Optional[str]:
    """
    Check which container currently holds the Virtual IP (172.20.0.100).
    Asks each node: 'do you have this IP on any of your interfaces?'
    Returns container name ("fw1", "fw2", "fw3") or None if no owner.
    """
    for container in FW_CONTAINERS:
        rc, out, _ = run_in_container(container, f"ip addr show | grep {VIRTUAL_IP}")
        if rc == 0 and VIRTUAL_IP in out:
            return container
    return None


def wait_for_vip(timeout: int = 30, poll: float = 1.0) -> Optional[str]:
    """
    Poll every `poll` seconds until some container owns the VIP.
    Returns the owner name, or None if timeout expires.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        owner = get_vip_owner()
        if owner:
            return owner
        time.sleep(poll)
    return None


def stop_container(name: str) -> None:
    """Stop a container — simulates a node crash for failover tests."""
    subprocess.run(["docker", "stop", name], check=True, capture_output=True)


def start_container(name: str) -> None:
    """Start a previously stopped container — simulates node recovery."""
    subprocess.run(["docker", "start", name], check=True, capture_output=True)


def wait_for_healthy(name: str, timeout: int = 60) -> bool:
    """
    Wait until Docker reports the container as 'healthy'.
    Uses the healthcheck defined in docker-compose.yml (nft list ruleset).
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", name],
            capture_output=True, text=True,
        )
        if result.stdout.strip() == "healthy":
            return True
        time.sleep(2)
    return False


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def fw_ips():
    """All firewall IPs as a dict — available to any test that requests it."""
    return {
        "fw1": {"mgmt": FW1_MGMT, "frontend": FW1_FRONT},
        "fw2": {"mgmt": FW2_MGMT, "frontend": FW2_FRONT},
        "fw3": {"mgmt": FW3_MGMT, "frontend": FW3_FRONT},
        "vip": VIRTUAL_IP,
        "server1": SERVER1_IP,
        "server2": SERVER2_IP,
    }


@pytest.fixture(scope="session")
def ensure_all_running():
    """
    Session-scoped: runs ONCE before all tests.
    Verifies all 3 fw containers are running — fails fast with a clear message.
    'scope=session' means it only executes once for the whole test run.
    """
    for container in FW_CONTAINERS:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", container],
            capture_output=True, text=True,
        )
        assert result.stdout.strip() == "true", (
            f"Container '{container}' is not running.\n"
            f"Start with: docker compose up -d"
        )


@pytest.fixture(scope="function")
def restore_fw1():
    """
    Function-scoped fixture used by failover tests.
    The 'yield' means: run the test, THEN run the teardown below.
    Teardown always runs even if the test crashes — guarantees fw1 is restored.
    """
    yield   # ← test runs here
    # Teardown: always restart fw1 after a failover test
    start_container("fw1")
    wait_for_healthy("fw1", timeout=60)
