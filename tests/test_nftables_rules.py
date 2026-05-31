import pytest

from conftest import (
    ALL_FW_MGMT,
    FW_CONTAINER_BY_MGMT,
    FW_CONTAINERS,
    ensure_all_running,
    ping,
    run_in_container,
    tcp_connect_from_container,
)


def ruleset(container: str) -> str:
    rc, output, err = run_in_container(container, "nft list ruleset")
    assert rc == 0, f"nft failed on {container}: {err}"
    return output


def has_icmpv6_rule(output: str) -> bool:
    return "icmpv6" in output or "ipv6-icmp" in output


class TestRulesetLoaded:
    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_ruleset_not_empty(self, container, ensure_all_running):
        assert "table" in ruleset(container), (
            f"Ruleset is empty on {container}. Run the Ansible firewall role."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_input_chain_has_drop_policy(self, container, ensure_all_running):
        output = ruleset(container)
        assert "chain input" in output, f"No input chain found on {container}"
        assert "policy drop" in output, (
            f"Input chain on {container} does not use default-drop."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_forward_chain_exists(self, container, ensure_all_running):
        assert "chain forward" in ruleset(container), (
            f"No forward chain on {container}."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_dual_stack_table_present(self, container, ensure_all_running):
        output = ruleset(container)
        assert "table inet" in output or ("table ip" in output and "table ip6" in output), (
            f"No dual-stack nftables table on {container}."
        )


class TestAllowedManagementTraffic:
    @pytest.mark.parametrize("fw_ip", ALL_FW_MGMT)
    def test_ssh_port_22_open(self, fw_ip, ensure_all_running):
        source = FW_CONTAINER_BY_MGMT[fw_ip]
        assert tcp_connect_from_container(source, fw_ip, 22), (
            f"SSH port 22 is closed on {fw_ip}; Ansible cannot manage the node."
        )

    @pytest.mark.parametrize("fw_ip", ALL_FW_MGMT)
    def test_ping_responds(self, fw_ip, ensure_all_running):
        source = FW_CONTAINER_BY_MGMT[fw_ip]
        assert ping(fw_ip, from_container=source), (
            f"Cannot ping firewall management IP {fw_ip} from {source}."
        )


class TestRuleContent:
    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_http_forward_ports_are_allowed_in_ruleset(self, container, ensure_all_running):
        output = ruleset(container)
        assert "dport { 80, 443 }" in output or "dport 80" in output, (
            f"HTTP/HTTPS forward rule missing on {container}."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_blocked_ports_are_not_explicitly_allowed(self, container, ensure_all_running):
        output = ruleset(container)
        for blocked_port in ("8080", "3306", "23"):
            assert f"dport {blocked_port}" not in output, (
                f"Unexpected allow rule for port {blocked_port} on {container}."
            )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_stateful_tracking_rule(self, container, ensure_all_running):
        output = ruleset(container)
        assert "established" in output and "related" in output, (
            f"Missing stateful tracking rule on {container}."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_loopback_accepted(self, container, ensure_all_running):
        output = ruleset(container)
        assert "iif" in output and "lo" in output, (
            f"Missing loopback accept rule on {container}."
        )

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_icmpv6_accepted(self, container, ensure_all_running):
        assert has_icmpv6_rule(ruleset(container)), (
            f"Missing ICMPv6 accept rule on {container}."
        )
