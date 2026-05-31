import socket
import subprocess

import pytest

from conftest import FW_CONTAINERS, ensure_all_running, run_in_container


FW1_IPV6 = "fd00:20::11"
FW2_IPV6 = "fd00:20::12"
FW3_IPV6 = "fd00:20::13"
ALL_FW_IPV6 = [FW1_IPV6, FW2_IPV6, FW3_IPV6]


def has_icmpv6_rule(ruleset: str) -> bool:
    return "icmpv6" in ruleset or "ipv6-icmp" in ruleset


def ping6(target: str, from_container: str | None = None, count: int = 3) -> bool:
    cmd = f"ping6 -c {count} -W 2 {target}"
    if from_container:
        result = subprocess.run(
            ["docker", "exec", from_container, "bash", "-c", cmd],
            capture_output=True,
            timeout=15,
        )
        return result.returncode == 0
    return subprocess.run(cmd.split(), capture_output=True).returncode == 0


def tcp6_connect(ip: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((ip, port, 0, 0))
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def has_ipv6(container: str) -> bool:
    rc, out, _ = run_in_container(
        container,
        "ip -6 addr show | grep inet6 | grep -v fe80 | grep -v '::1'",
    )
    return rc == 0 and bool(out.strip())


class TestIPv6KernelConfig:
    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ipv6_forwarding_enabled(self, container, ensure_all_running):
        rc, out, _ = run_in_container(
            container,
            "cat /proc/sys/net/ipv6/conf/all/forwarding",
        )
        assert rc == 0
        assert out.strip() == "1", f"IPv6 forwarding is disabled on {container}."

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ipv6_loopback_works(self, container, ensure_all_running):
        assert ping6("::1", from_container=container), (
            f"Cannot ping IPv6 loopback from {container}."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ipv6_address_assigned(self, container, ensure_all_running):
        if not has_ipv6(container):
            pytest.skip("Docker IPv6 is not enabled for this container.")


class TestIPv6Ruleset:
    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ip6_or_inet_table_exists(self, container, ensure_all_running):
        rc, out, _ = run_in_container(container, "nft list ruleset")
        assert rc == 0
        assert "ip6" in out or "inet" in out, f"No IPv6 or inet table on {container}."

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_icmpv6_rule_present(self, container, ensure_all_running):
        rc, out, _ = run_in_container(container, "nft list ruleset")
        assert rc == 0
        assert has_icmpv6_rule(out), f"Missing ICMPv6 rule on {container}."

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_allowed_ipv6_prefix_fd00(self, container, ensure_all_running):
        rc, out, _ = run_in_container(container, "nft list ruleset")
        assert rc == 0
        assert "fd00" in out, f"IPv6 fd00 prefix missing from ruleset on {container}."

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ipv6_stateful_tracking(self, container, ensure_all_running):
        rc, out, _ = run_in_container(container, "nft list ruleset")
        assert rc == 0
        assert "established" in out, f"No stateful tracking in IPv6 rules on {container}."


class TestIPv6Connectivity:
    def _skip_if_no_ipv6(self, container: str):
        if not has_ipv6(container):
            pytest.skip("Docker IPv6 is not enabled.")

    def test_ping6_fw1_to_fw2(self, ensure_all_running):
        self._skip_if_no_ipv6("fw1")
        assert ping6(FW2_IPV6, from_container="fw1")

    def test_ping6_fw1_to_fw3(self, ensure_all_running):
        self._skip_if_no_ipv6("fw1")
        assert ping6(FW3_IPV6, from_container="fw1")

    @pytest.mark.parametrize("ipv6", ALL_FW_IPV6)
    def test_ssh_open_over_ipv6(self, ipv6, ensure_all_running):
        if not has_ipv6("fw1"):
            pytest.skip("Docker IPv6 is not enabled.")
        assert tcp6_connect(ipv6, 22)

    @pytest.mark.parametrize("ipv6", ALL_FW_IPV6)
    def test_blocked_port_over_ipv6(self, ipv6, ensure_all_running):
        if not has_ipv6("fw1"):
            pytest.skip("Docker IPv6 is not enabled.")
        assert not tcp6_connect(ipv6, 8080, timeout=3.0)
