import time

import pytest

from conftest import (
    FW_CONTAINERS,
    VIRTUAL_IP,
    ensure_all_running,
    get_vip_probe_container,
    ping,
    restore_fw1,
    run_in_container,
    start_container,
    stop_container,
    tcp_connect_from_container,
    wait_for_healthy,
    wait_for_vip,
    wait_for_vip_owner,
)


FAILOVER_TIMEOUT = 15
PREEMPT_TIMEOUT = 20


class TestInitialState:
    def test_exactly_one_vip_owner(self, ensure_all_running):
        owners = [
            container
            for container in FW_CONTAINERS
            if run_in_container(container, f"ip addr show | grep {VIRTUAL_IP}")[0] == 0
            and VIRTUAL_IP in run_in_container(container, f"ip addr show | grep {VIRTUAL_IP}")[1]
        ]
        assert len(owners) == 1, (
            f"Expected exactly one VIP owner, got {len(owners)}: {owners}"
        )

    def test_fw1_is_master(self, ensure_all_running):
        owner = wait_for_vip(timeout=20)
        assert owner == "fw1", (
            f"Expected fw1 as MASTER because it has highest priority, got {owner}."
        )

    def test_vip_is_pingable(self, ensure_all_running):
        probe = get_vip_probe_container()
        assert probe is not None
        assert ping(VIRTUAL_IP, from_container=probe), (
            f"VIP {VIRTUAL_IP} does not respond to ping from {probe}."
        )

    def test_vip_ssh_reachable(self, ensure_all_running):
        probe = get_vip_probe_container()
        assert probe is not None
        assert tcp_connect_from_container(probe, VIRTUAL_IP, 22), (
            f"SSH on VIP {VIRTUAL_IP}:22 is unreachable from {probe}."
        )


class TestFailover:
    def test_vip_moves_after_master_fails(self, ensure_all_running, restore_fw1):
        assert wait_for_vip_owner("fw1", timeout=20), "Precondition: fw1 must be MASTER"

        stop_container("fw1")
        new_owner = wait_for_vip(timeout=FAILOVER_TIMEOUT)

        assert new_owner is not None, "VIP did not move after stopping fw1."
        assert new_owner in ["fw2", "fw3"], f"VIP moved to unexpected node: {new_owner}"

    def test_fw2_takes_over_before_fw3(self, ensure_all_running, restore_fw1):
        assert wait_for_vip_owner("fw1", timeout=20)

        stop_container("fw1")
        new_owner = wait_for_vip(timeout=FAILOVER_TIMEOUT)

        assert new_owner == "fw2", (
            f"Expected fw2 to take over because it has priority 100, got {new_owner}."
        )

    def test_vip_pingable_after_failover(self, ensure_all_running, restore_fw1):
        stop_container("fw1")
        wait_for_vip(timeout=FAILOVER_TIMEOUT)

        probe = get_vip_probe_container()
        assert probe is not None
        assert ping(VIRTUAL_IP, from_container=probe), (
            f"VIP {VIRTUAL_IP} is not pingable from {probe} after failover."
        )

    def test_ssh_on_vip_after_failover(self, ensure_all_running, restore_fw1):
        stop_container("fw1")
        wait_for_vip(timeout=FAILOVER_TIMEOUT)
        time.sleep(2)

        probe = get_vip_probe_container()
        assert probe is not None
        assert tcp_connect_from_container(probe, VIRTUAL_IP, 22), (
            f"SSH on VIP is unreachable from {probe} after failover."
        )


class TestPreemption:
    def test_fw1_reclaims_vip_on_recovery(self, ensure_all_running, restore_fw1):
        stop_container("fw1")
        backup = wait_for_vip(timeout=FAILOVER_TIMEOUT)
        assert backup in ["fw2", "fw3"], "Failover must happen before recovery test"

        start_container("fw1")
        wait_for_healthy("fw1", timeout=60)

        assert wait_for_vip_owner("fw1", timeout=PREEMPT_TIMEOUT), (
            f"fw1 did not reclaim VIP after recovery. Current owner: {wait_for_vip(timeout=1)}"
        )


class TestDoubleFailure:
    def test_fw3_takes_over_when_fw1_and_fw2_fail(self, ensure_all_running, restore_fw1):
        try:
            stop_container("fw1")
            stop_container("fw2")
            owner = wait_for_vip(timeout=FAILOVER_TIMEOUT + 5)
            assert owner == "fw3", f"Expected fw3 to hold VIP when fw1 and fw2 fail, got {owner}"
        finally:
            start_container("fw1")
            start_container("fw2")
            wait_for_healthy("fw1", timeout=60)
            wait_for_healthy("fw2", timeout=60)
