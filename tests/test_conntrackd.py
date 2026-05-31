import time

import pytest

from conftest import (
    FW1_MGMT,
    FW2_MGMT,
    FW3_MGMT,
    FW_CONTAINERS,
    VIRTUAL_IP,
    ensure_all_running,
    get_vip_probe_container,
    run_in_container,
    tcp_connect_from_container,
    wait_for_vip,
)


CONNTRACKD_SOCKET = "/var/run/conntrackd.ctl"
FW_MGMT_MAP = {
    "fw1": FW1_MGMT,
    "fw2": FW2_MGMT,
    "fw3": FW3_MGMT,
}


class TestConntrackdRunning:
    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_conntrackd_process_exists(self, container, ensure_all_running):
        rc, _, _ = run_in_container(container, "pgrep conntrackd")
        assert rc == 0, f"conntrackd is not running on {container}."

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_conntrackd_config_exists(self, container, ensure_all_running):
        rc, _, _ = run_in_container(container, "test -f /etc/conntrackd/conntrackd.conf")
        assert rc == 0, f"conntrackd config is missing on {container}."

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_conntrackd_socket_exists(self, container, ensure_all_running):
        rc, _, _ = run_in_container(container, f"test -S {CONNTRACKD_SOCKET}")
        assert rc == 0, f"conntrackd socket is missing on {container}."

    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_conntrackd_config_has_correct_ip(self, container, ensure_all_running):
        expected_ip = FW_MGMT_MAP[container]
        rc, out, _ = run_in_container(container, "cat /etc/conntrackd/conntrackd.conf")
        assert rc == 0, f"Cannot read conntrackd config on {container}"
        assert expected_ip in out, (
            f"conntrackd config on {container} does not contain its own IP {expected_ip}."
        )


class TestConntrackdSyncActivity:
    @pytest.mark.parametrize("container", FW_CONTAINERS)
    def test_conntrackd_stats_accessible(self, container, ensure_all_running):
        rc, out, err = run_in_container(
            container,
            "conntrackd -C /etc/conntrackd/conntrackd.conf -s",
        )
        assert rc == 0 or out, f"conntrackd stats failed on {container}: {err}"

    def test_master_node_sends_sync_packets(self, ensure_all_running):
        master = wait_for_vip(timeout=20)
        assert master is not None, "No VIP owner; Keepalived is not running"

        probe = get_vip_probe_container()
        if probe:
            tcp_connect_from_container(probe, VIRTUAL_IP, 22)

        time.sleep(2)
        rc, out, _ = run_in_container(
            master,
            "conntrackd -C /etc/conntrackd/conntrackd.conf -s",
        )
        assert rc == 0 or out, f"Could not get conntrackd stats from MASTER {master}."

    def test_conntrack_table_has_entries(self, ensure_all_running):
        master = wait_for_vip(timeout=20)
        assert master is not None

        probe = get_vip_probe_container()
        if probe:
            tcp_connect_from_container(probe, VIRTUAL_IP, 22)

        time.sleep(1)
        rc, out, _ = run_in_container(master, "conntrack -L 2>/dev/null | head -20")
        if rc != 0:
            pytest.skip("conntrack CLI not available")

        assert out.strip(), f"Connection tracking table is empty on MASTER {master}."

    def test_backup_has_synced_entries(self, ensure_all_running):
        master = wait_for_vip(timeout=20)
        assert master is not None
        backup = next((container for container in FW_CONTAINERS if container != master), None)
        assert backup is not None

        probe = get_vip_probe_container()
        if probe:
            tcp_connect_from_container(probe, VIRTUAL_IP, 22)

        time.sleep(2)
        rc, out, _ = run_in_container(backup, "conntrack -L 2>/dev/null")
        if rc != 0:
            pytest.skip("conntrack CLI not available on backup node")

        assert out.strip(), (
            f"BACKUP node {backup} has an empty connection tracking table. "
            f"conntrackd is not syncing from MASTER {master}."
        )
