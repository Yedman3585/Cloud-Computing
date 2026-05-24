# =============================================================================
# tests/test_nftables_rules.py
# Task 6 — Python tests for nftables rules
#
# Tests are grouped into classes. Each class tests one aspect.
# @pytest.mark.parametrize runs the same test once per firewall node.
# =============================================================================

import pytest
from conftest import (
    run_in_container, tcp_connect, ping,
    ALL_FW_MGMT, ALL_FW_FRONT, FW_CONTAINERS,
    ensure_all_running,
)


class TestRulesetLoaded:
    """Verify nftables is running and the ruleset is not empty on all nodes."""

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ruleset_not_empty(self, container, ensure_all_running):
        """
        'nft list ruleset' must return at least one table.
        If the ruleset is empty it means Ansible hasn't deployed the rules yet.
        """
        rc, output, _ = run_in_container(container, "nft list ruleset")
        assert rc == 0, f"nft command failed on {container} — is nftables installed?"
        assert "table" in output, (
            f"Ruleset is empty on {container}.\n"
            f"Fix: run the Ansible playbook to deploy rules."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_input_chain_has_drop_policy(self, container, ensure_all_running):
        """
        The input chain must have 'policy drop'.
        Default-allow is dangerous — any unlisted traffic would pass.
        """
        rc, output, _ = run_in_container(container, "nft list ruleset")
        assert "chain input" in output, f"No input chain found on {container}"
        assert "policy drop" in output, (
            f"Input chain on {container} does NOT have 'policy drop'.\n"
            f"This means traffic is default-allow — a security hole!"
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_forward_chain_exists(self, container, ensure_all_running):
        """Forward chain must exist — it routes traffic between frontend and backend."""
        rc, output, _ = run_in_container(container, "nft list ruleset")
        assert "chain forward" in output, (
            f"No forward chain on {container} — traffic cannot be routed."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ipv4_table_present(self, container, ensure_all_running):
        """An IPv4 ('ip') or dual-stack ('inet') table must exist."""
        rc, output, _ = run_in_container(container, "nft list ruleset")
        assert "table inet" in output or "table ip" in output, (
            f"No IPv4/inet table on {container}. Deploy nftables_ipv4.j2 via Ansible."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ipv6_table_present(self, container, ensure_all_running):
        """An IPv6 ('ip6') or dual-stack ('inet') table must exist."""
        rc, output, _ = run_in_container(container, "nft list ruleset")
        assert "table inet" in output or "table ip6" in output, (
            f"No IPv6/inet table on {container}. Deploy nftables_ipv6.j2 via Ansible."
        )


class TestAllowedPorts:
    """Ports in vars.yml allowed_ports (22, 80, 443) must be reachable."""

    @pytest.mark.parametrize("fw_ip", ALL_FW_MGMT)
    def test_ssh_port_22_open(self, fw_ip, ensure_all_running):
        """
        Port 22 must be open on the management interface.
        Critical: Ansible connects here to manage the nodes.
        """
        assert tcp_connect(fw_ip, 22), (
            f"SSH port 22 CLOSED on {fw_ip}.\n"
            f"Check: 'tcp dport 22 accept' in the input chain."
        )

    @pytest.mark.parametrize("fw_ip", ALL_FW_FRONT)
    def test_http_port_80_open(self, fw_ip, ensure_all_running):
        """Port 80 must be reachable on the frontend (client-facing) interface."""
        assert tcp_connect(fw_ip, 80), (
            f"HTTP port 80 CLOSED on {fw_ip}.\n"
            f"Check allowed_ports in vars.yml and rerun Ansible."
        )

    @pytest.mark.parametrize("fw_ip", ALL_FW_FRONT)
    def test_https_port_443_open(self, fw_ip, ensure_all_running):
        """Port 443 must be reachable on the frontend interface."""
        assert tcp_connect(fw_ip, 443), (
            f"HTTPS port 443 CLOSED on {fw_ip}.\n"
            f"Check allowed_ports in vars.yml and rerun Ansible."
        )


class TestBlockedPorts:
    """Ports NOT in allowed_ports must be silently dropped (not refused, not open)."""

    @pytest.mark.parametrize("fw_ip", ALL_FW_FRONT)
    def test_port_8080_blocked(self, fw_ip, ensure_all_running):
        """
        Port 8080 is not in vars.yml — must be filtered (no reply).
        tcp_connect returns False when connection times out = filtered.
        If it returned True, the firewall is not blocking it.
        """
        assert not tcp_connect(fw_ip, 8080, timeout=3.0), (
            f"Port 8080 is OPEN on {fw_ip} — it should be blocked!\n"
            f"The default-drop policy is not working."
        )

    @pytest.mark.parametrize("fw_ip", ALL_FW_FRONT)
    def test_port_3306_blocked(self, fw_ip, ensure_all_running):
        """MySQL port 3306 must never be exposed externally."""
        assert not tcp_connect(fw_ip, 3306, timeout=3.0), (
            f"MySQL port 3306 OPEN on {fw_ip} — critical security issue!"
        )

    @pytest.mark.parametrize("fw_ip", ALL_FW_FRONT)
    def test_port_23_blocked(self, fw_ip, ensure_all_running):
        """Telnet port 23 must be blocked."""
        assert not tcp_connect(fw_ip, 23, timeout=3.0), (
            f"Telnet port 23 is OPEN on {fw_ip}!"
        )


class TestICMP:
    """ICMP ping must work — allowed by 'ip protocol icmp accept' rule."""

    @pytest.mark.parametrize("fw_ip", ALL_FW_MGMT)
    def test_ping_responds(self, fw_ip, ensure_all_running):
        assert ping(fw_ip), (
            f"Cannot ping {fw_ip}.\n"
            f"Check: 'ip protocol icmp accept' in input chain."
        )


class TestRuleContent:
    """Check that specific critical rules exist inside the ruleset text."""

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_stateful_tracking_rule(self, container, ensure_all_running):
        """
        'ct state established,related accept' is mandatory.
        Without it, responses to outgoing connections are blocked — nothing works.
        'ct' = connection tracking, 'established' = ongoing connections.
        """
        rc, output, _ = run_in_container(container, "nft list ruleset")
        assert "established" in output and "related" in output, (
            f"Missing stateful tracking rule on {container}.\n"
            f"Without it, all return traffic is dropped."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_loopback_accepted(self, container, ensure_all_running):
        """Loopback (lo) must be accepted — local services (DNS etc.) need it."""
        rc, output, _ = run_in_container(container, "nft list ruleset")
        assert "iif" in output and "lo" in output, (
            f"Missing loopback accept rule on {container}."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_icmpv6_accepted(self, container, ensure_all_running):
        """ICMPv6 must be accepted — IPv6 neighbor discovery depends on it."""
        rc, output, _ = run_in_container(container, "nft list ruleset")
        assert "icmpv6" in output, (
            f"Missing ICMPv6 accept rule on {container}.\n"
            f"IPv6 neighbor discovery will fail without it."
        )
