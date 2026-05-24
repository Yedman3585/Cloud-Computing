import time
import pytest
from conftest import (
    run_in_container, tcp_connect, ping,
    get_vip_owner, wait_for_vip,
    stop_container, start_container, wait_for_healthy,
    VIRTUAL_IP, FW_CONTAINERS,
    ensure_all_running, restore_fw1,
)

# Maximum seconds allowed for VIP to move after a failure
FAILOVER_TIMEOUT = 15

# Maximum seconds allowed for fw1 to reclaim VIP after restart
PREEMPT_TIMEOUT  = 20


class TestInitialState:
    """Cluster must start in a clean, correct state before failover tests run."""

    def test_exactly_one_vip_owner(self, ensure_all_running):
        """
        Count how many nodes hold the VIP. Must be exactly 1.
        0 owners = Keepalived not running.
        2+ owners = split-brain (very bad — both nodes think they're MASTER).
        """
        owners = [
            c for c in FW_CONTAINERS
            if run_in_container(c, f"ip addr show | grep {VIRTUAL_IP}")[0] == 0
            and VIRTUAL_IP in run_in_container(c, f"ip addr show | grep {VIRTUAL_IP}")[1]
        ]
        assert len(owners) == 1, (
            f"Expected 1 VIP owner, got {len(owners)}: {owners}\n"
            f"{'Keepalived not running?' if not owners else 'Split-brain detected!'}"
        )

    def test_fw1_is_master(self, ensure_all_running):
        """
        fw1 has highest priority (110) and must be MASTER at startup.
        If fw2 or fw3 is MASTER, the priority configuration is wrong.
        """
        owner = wait_for_vip(timeout=20)
        assert owner == "fw1", (
            f"Expected fw1 as MASTER, got '{owner}'.\n"
            f"Check KEEPALIVED_PRIORITY env vars in docker-compose.yml."
        )

    def test_vip_is_pingable(self, ensure_all_running):
        """The VIP itself must respond to ping — proves it's actually assigned."""
        assert ping(VIRTUAL_IP), (
            f"VIP {VIRTUAL_IP} does not respond to ping.\n"
            f"Is Keepalived running? Run: docker exec fw1 pgrep keepalived"
        )

    def test_vip_ssh_reachable(self, ensure_all_running):
        """SSH on the VIP must work — Ansible uses it to reach the active node."""
        assert tcp_connect(VIRTUAL_IP, 22), (
            f"SSH on VIP {VIRTUAL_IP}:22 unreachable."
        )


class TestFailover:
    """Stop fw1 and verify VIP moves to a backup node automatically."""

    def test_vip_moves_after_master_fails(self, ensure_all_running, restore_fw1):
        """
        MAIN FAILOVER TEST — step by step:
          1. Confirm fw1 holds the VIP (initial state)
          2. Stop fw1 (docker stop = simulated crash)
          3. Wait up to FAILOVER_TIMEOUT seconds
          4. Assert VIP is now on fw2 or fw3

        'restore_fw1' is a fixture (in conftest.py) that restarts fw1 in
        teardown — runs even if this test fails, keeping the environment clean.
        """
        # Step 1
        assert wait_for_vip(timeout=20) == "fw1", "Precondition: fw1 must be MASTER"

        # Step 2
        stop_container("fw1")

        # Step 3 + 4
        new_owner = wait_for_vip(timeout=FAILOVER_TIMEOUT)
        assert new_owner is not None, (
            f"VIP did not move after stopping fw1!\n"
            f"Check Keepalived on fw2: docker exec fw2 journalctl -u keepalived"
        )
        assert new_owner in ["fw2", "fw3"], (
            f"VIP moved to unexpected node: {new_owner}"
        )

    def test_fw2_takes_over_before_fw3(self, ensure_all_running, restore_fw1):
        """
        fw2 has priority 100, fw3 has priority 90.
        When fw1 fails, fw2 must win the election (higher priority wins).
        """
        assert wait_for_vip(timeout=20) == "fw1"
        stop_container("fw1")
        new_owner = wait_for_vip(timeout=FAILOVER_TIMEOUT)
        assert new_owner == "fw2", (
            f"Expected fw2 (priority 100) to take over, got: {new_owner}.\n"
            f"Check KEEPALIVED_PRIORITY in docker-compose.yml for fw2 and fw3."
        )

    def test_vip_pingable_after_failover(self, ensure_all_running, restore_fw1):
        """
        After failover, the VIP must still respond to ping.
        This proves HA is working — the service continues with minimal downtime.
        """
        stop_container("fw1")
        wait_for_vip(timeout=FAILOVER_TIMEOUT)
        assert ping(VIRTUAL_IP), (
            f"VIP {VIRTUAL_IP} not pingable after failover — HA is broken!"
        )

    def test_ssh_on_vip_after_failover(self, ensure_all_running, restore_fw1):
        """SSH must still work on the VIP after failover."""
        stop_container("fw1")
        wait_for_vip(timeout=FAILOVER_TIMEOUT)
        time.sleep(2)  # brief settling
        assert tcp_connect(VIRTUAL_IP, 22), (
            f"SSH on VIP unreachable after failover."
        )


class TestPreemption:
    """When fw1 recovers, it must reclaim the VIP (preemption)."""

    def test_fw1_reclaims_vip_on_recovery(self, ensure_all_running, restore_fw1):
        """
        Full cycle:
          fw1 MASTER → fw1 crashes → fw2 takes over → fw1 restarts → fw1 reclaims VIP

        Keepalived preemption: when a higher-priority node comes back online,
        it takes the VIP back from the current MASTER.
        This only works if 'nopreempt' is NOT set in keepalived config.
        """
        # Crash fw1
        stop_container("fw1")
        backup = wait_for_vip(timeout=FAILOVER_TIMEOUT)
        assert backup in ["fw2", "fw3"], "Failover must happen before recovery test"

        # Recover fw1
        start_container("fw1")
        wait_for_healthy("fw1", timeout=60)
        time.sleep(5)  # allow VRRP election cycles to complete

        # fw1 must reclaim the VIP
        final = wait_for_vip(timeout=PREEMPT_TIMEOUT)
        assert final == "fw1", (
            f"fw1 did NOT reclaim VIP after recovery. Current owner: {final}\n"
            f"Check that 'nopreempt' is NOT in keepalived/fw1.conf"
        )


class TestDoubleFailure:
    """Two nodes fail simultaneously — the last one standing must hold the VIP."""

    def test_fw3_takes_over_when_fw1_and_fw2_fail(self, ensure_all_running):
        """
        Stop both fw1 and fw2. Only fw3 remains.
        fw3 must hold the VIP with no other candidates.
        Teardown manually restores both nodes.
        """
        try:
            stop_container("fw1")
            stop_container("fw2")
            owner = wait_for_vip(timeout=FAILOVER_TIMEOUT + 5)
            assert owner == "fw3", (
                f"Expected fw3 to hold VIP when fw1+fw2 fail. Got: {owner}"
            )
        finally:
            start_container("fw1")
            start_container("fw2")
            wait_for_healthy("fw1", timeout=60)
            wait_for_healthy("fw2", timeout=60)
