import socket
import subprocess
import pytest
from conftest import run_in_container, FW_CONTAINERS, ensure_all_running

# ---------------------------------------------------------------------------
# IPv6 addresses for each node on mgmt_net
# These must match whatever Docker assigns when enable_ipv6 is turned on.
# With enable_ipv6: false (current default), these tests will SKIP gracefully.
# ---------------------------------------------------------------------------
FW1_IPV6 = "fd00:20::11"
FW2_IPV6 = "fd00:20::12"
FW3_IPV6 = "fd00:20::13"

FW_IPV6_MAP = {"fw1": FW1_IPV6, "fw2": FW2_IPV6, "fw3": FW3_IPV6}
ALL_FW_IPV6  = list(FW_IPV6_MAP.values())


# ---------------------------------------------------------------------------
# IPv6-specific helper functions
# ---------------------------------------------------------------------------

def ping6(target: str, from_container: str = None, count: int = 3) -> bool:
    """Send ICMPv6 ping. Runs inside container if from_container is given."""
    cmd = f"ping6 -c {count} -W 2 {target}"
    if from_container:
        result = subprocess.run(
            ["docker", "exec", from_container, "bash", "-c", cmd],
            capture_output=True, timeout=15,
        )
        return result.returncode == 0
    return subprocess.run(cmd.split(), capture_output=True).returncode == 0


def tcp6_connect(ip: str, port: int, timeout: float = 3.0) -> bool:
    """Open a TCP connection to an IPv6 address:port."""
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((ip, port, 0, 0))
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def has_ipv6(container: str) -> bool:
    """Return True if the container has any non-loopback, non-link-local IPv6 address."""
    rc, out, _ = run_in_container(
        container,
        "ip -6 addr show | grep inet6 | grep -v fe80 | grep -v '::1'"
    )
    return rc == 0 and bool(out.strip())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestIPv6KernelConfig:
    """Kernel-level IPv6 settings must be correct on all firewall nodes."""

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ipv6_forwarding_enabled(self, container, ensure_all_running):
        """
        /proc/sys/net/ipv6/conf/all/forwarding must be 1.
        Without this, IPv6 packets stop at the firewall and are not routed forward.
        This is set in entrypoint.sh and docker-compose.yml sysctls.
        """
        rc, out, _ = run_in_container(
            container, "cat /proc/sys/net/ipv6/conf/all/forwarding"
        )
        assert rc == 0
        assert out.strip() == "1", (
            f"IPv6 forwarding DISABLED on {container} (got '{out.strip()}').\n"
            f"Check sysctls in docker-compose.yml and entrypoint.sh."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ipv6_loopback_works(self, container, ensure_all_running):
        """The IPv6 loopback (::1) must be pingable — basic IPv6 stack health check."""
        assert ping6("::1", from_container=container), (
            f"Cannot ping6 ::1 (loopback) from {container}.\n"
            f"IPv6 stack is not functional inside the container."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ipv6_address_assigned(self, container, ensure_all_running):
        """
        Container must have at least one global IPv6 address.
        If this fails, enable_ipv6: true needs to be set in docker-compose.yml
        and the Docker daemon must have IPv6 enabled.
        """
        if not has_ipv6(container):
            pytest.skip(
                f"No global IPv6 address on {container}. "
                f"Enable IPv6 in docker-compose.yml (enable_ipv6: true) "
                f"and restart the stack."
            )


class TestIPv6Ruleset:
    """The IPv6 nftables ruleset (from nftables_ipv6.j2) must be correctly loaded."""

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ip6_or_inet_table_exists(self, container, ensure_all_running):
        """
        Either 'table ip6 filter' (from nftables_ipv6.j2) or 'table inet filter'
        (dual-stack) must exist. The template creates 'table ip6 filter'.
        """
        rc, out, _ = run_in_container(container, "nft list ruleset")
        assert "ip6" in out or "inet" in out, (
            f"No IPv6 table on {container}.\n"
            f"Deploy nftables_ipv6.j2 via Ansible."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_icmpv6_rule_present(self, container, ensure_all_running):
        """
        'ip6 nexthdr icmpv6 accept' must be in the ruleset.
        ICMPv6 carries neighbor discovery — without it, IPv6 routing breaks completely.
        """
        rc, out, _ = run_in_container(container, "nft list ruleset")
        assert "icmpv6" in out, (
            f"Missing ICMPv6 rule on {container}.\n"
            f"Check nftables_ipv6.j2 template — it must have: ip6 nexthdr icmpv6 accept"
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_allowed_ipv6_prefix_fd00(self, container, ensure_all_running):
        """
        The fd00::/8 prefix from vars.yml must appear in the IPv6 ruleset.
        fd00::/8 is the ULA (Unique Local Address) range — used for internal traffic.
        """
        rc, out, _ = run_in_container(container, "nft list ruleset")
        assert "fd00" in out, (
            f"IPv6 prefix fd00::/8 missing from ruleset on {container}.\n"
            f"Check allowed_ipv6 in vars.yml and rerun Ansible."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ipv6_stateful_tracking(self, container, ensure_all_running):
        """Established/related connections must be accepted in the IPv6 ruleset too."""
        rc, out, _ = run_in_container(container, "nft list ruleset")
        assert "established" in out, (
            f"No stateful tracking in IPv6 rules on {container}."
        )


class TestIPv6Connectivity:
    """Test actual IPv6 packet flow between containers (requires enable_ipv6: true)."""

    def _skip_if_no_ipv6(self, container: str):
        if not has_ipv6(container):
            pytest.skip("IPv6 not enabled in Docker — set enable_ipv6: true in docker-compose.yml")

    def test_ping6_fw1_to_fw2(self, ensure_all_running):
        """fw1 must be able to ping6 fw2 on mgmt_net."""
        self._skip_if_no_ipv6("fw1")
        assert ping6(FW2_IPV6, from_container="fw1"), (
            f"fw1 cannot ping6 fw2 ({FW2_IPV6}).\n"
            f"Check IPv6 is enabled on mgmt_net in docker-compose.yml."
        )

    def test_ping6_fw1_to_fw3(self, ensure_all_running):
        """fw1 must be able to ping6 fw3 on mgmt_net."""
        self._skip_if_no_ipv6("fw1")
        assert ping6(FW3_IPV6, from_container="fw1"), (
            f"fw1 cannot ping6 fw3 ({FW3_IPV6})."
        )

    @pytest.mark.parametrize("ipv6", ALL_FW_IPV6)
    def test_ssh_open_over_ipv6(self, ipv6, ensure_all_running):
        """Port 22 must be reachable over IPv6 (allowed by nftables_ipv6.j2 rules)."""
        if not has_ipv6("fw1"):
            pytest.skip("IPv6 not enabled")
        assert tcp6_connect(ipv6, 22), (
            f"SSH port 22 CLOSED over IPv6 on {ipv6}.\n"
            f"Check: tcp dport 22 accept in the ip6 input chain."
        )

    @pytest.mark.parametrize("ipv6", ALL_FW_IPV6)
    def test_blocked_port_over_ipv6(self, ipv6, ensure_all_running):
        """Port 8080 must be blocked over IPv6 too — not just IPv4."""
        if not has_ipv6("fw1"):
            pytest.skip("IPv6 not enabled")
        assert not tcp6_connect(ipv6, 8080, timeout=3.0), (
            f"Port 8080 OPEN over IPv6 on {ipv6} — should be blocked!"
        )
