import os
import socket
import subprocess
import time
from typing import Optional

import pytest

FW1_MGMT = os.environ.get("FW1_MGMT_IP", "172.20.0.11")
FW2_MGMT = os.environ.get("FW2_MGMT_IP", "172.20.0.12")
FW3_MGMT = os.environ.get("FW3_MGMT_IP", "172.20.0.13")

FW1_FRONT = os.environ.get("FW1_FRONTEND_IP", "172.21.0.11")
FW2_FRONT = os.environ.get("FW2_FRONTEND_IP", "172.21.0.12")
FW3_FRONT = os.environ.get("FW3_FRONTEND_IP", "172.21.0.13")

VIRTUAL_IP = os.environ.get("VIRTUAL_IP", "172.20.0.100")
SERVER1_IP = os.environ.get("SERVER1_IP", "172.22.0.31")
SERVER2_IP = os.environ.get("SERVER2_IP", "172.22.0.32")

ALL_FW_MGMT = [FW1_MGMT, FW2_MGMT, FW3_MGMT]
ALL_FW_FRONT = [FW1_FRONT, FW2_FRONT, FW3_FRONT]
FW_CONTAINERS = ["fw1", "fw2", "fw3"]
FW_MGMT_BY_CONTAINER = {
    "fw1": FW1_MGMT,
    "fw2": FW2_MGMT,
    "fw3": FW3_MGMT,
}
FW_CONTAINER_BY_MGMT = {ip: container for container, ip in FW_MGMT_BY_CONTAINER.items()}


def run_in_container(container: str, command: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["docker", "exec", container, "bash", "-c", command],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def ping(target_ip: str, from_container: str | None = None, count: int = 3) -> bool:
    cmd = f"ping -c {count} -W 2 {target_ip}"
    if from_container:
        rc, _, _ = run_in_container(from_container, cmd)
        return rc == 0
    result = subprocess.run(cmd.split(), capture_output=True)
    return result.returncode == 0


def is_container_running(name: str) -> bool:
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", name],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "true"


def tcp_connect(ip: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def tcp_connect_from_container(
    container: str, ip: str, port: int, timeout: float = 3.0
) -> bool:
    cmd = f"timeout {int(timeout)} bash -c '</dev/tcp/{ip}/{port}'"
    rc, _, _ = run_in_container(container, cmd)
    return rc == 0


def get_vip_owner() -> Optional[str]:
    for container in FW_CONTAINERS:
        if not is_container_running(container):
            continue
        rc, out, _ = run_in_container(container, f"ip addr show | grep {VIRTUAL_IP}")
        if rc == 0 and VIRTUAL_IP in out:
            return container
    return None


def wait_for_vip(timeout: int = 30, poll: float = 1.0) -> Optional[str]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        owner = get_vip_owner()
        if owner:
            return owner
        time.sleep(poll)
    return None


def wait_for_vip_owner(expected_owner: str, timeout: int = 30, poll: float = 1.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if get_vip_owner() == expected_owner:
            return True
        time.sleep(poll)
    return False


def get_vip_probe_container() -> Optional[str]:
    owner = get_vip_owner()
    for container in FW_CONTAINERS:
        if container != owner and is_container_running(container):
            return container
    return owner if owner and is_container_running(owner) else None


def stop_container(name: str) -> None:
    subprocess.run(["docker", "stop", name], check=True, capture_output=True)


def ensure_conntrackd_running(container: str, timeout: int = 15) -> bool:
    if run_in_container(container, "pgrep conntrackd")[0] == 0:
        return True

    run_in_container(
        container,
        (
            "/etc/init.d/conntrackd stop >/dev/null 2>&1 || true; "
            "rm -f /var/lock/conntrack.lock /run/conntrackd.ctl /var/run/conntrackd.ctl; "
            "/etc/init.d/conntrackd start >/dev/null 2>&1 || "
            "conntrackd -d -C /etc/conntrackd/conntrackd.conf"
        ),
    )

    deadline = time.time() + timeout
    while time.time() < deadline:
        if run_in_container(container, "pgrep conntrackd")[0] == 0:
            return True
        time.sleep(1)
    return False


def start_container(name: str) -> None:
    if not is_container_running(name):
        subprocess.run(["docker", "start", name], check=True, capture_output=True)
    if name in FW_CONTAINERS:
        wait_for_healthy(name, timeout=60)
        run_in_container(name, "/etc/init.d/keepalived start")
        ensure_conntrackd_running(name)


def wait_for_healthy(name: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", name],
            capture_output=True,
            text=True,
        )
        if result.stdout.strip() == "healthy":
            return True
        time.sleep(2)
    return False


@pytest.fixture(scope="session")
def fw_ips():
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
    for container in FW_CONTAINERS:
        start_container(container)
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", container],
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "true", (
            f"Container '{container}' is not running.\n"
            f"Start with: docker compose up -d"
        )
        assert ensure_conntrackd_running(container), (
            f"conntrackd could not be started on {container}."
        )
    assert wait_for_vip_owner("fw1", timeout=45), (
        f"fw1 did not own VIP {VIRTUAL_IP} before the test session started."
    )


@pytest.fixture(scope="function")
def restore_fw1():
    start_container("fw1")
    wait_for_healthy("fw1", timeout=60)
    assert wait_for_vip_owner("fw1", timeout=45), (
        f"fw1 did not own VIP {VIRTUAL_IP} before the test started."
    )
    yield
    start_container("fw1")
    wait_for_healthy("fw1", timeout=60)
    assert wait_for_vip_owner("fw1", timeout=45), (
        f"fw1 did not reclaim VIP {VIRTUAL_IP} after test cleanup."
    )
