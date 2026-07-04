import pytest

from conftest import (
    ensure_all_running,
    run_in_container,
    SERVER2_IP,
)

ALLOWED_PORT = 80
BLOCKED_PORT = 8080


def http_get_from_container(container: str, ip: str, port: int, timeout: int = 4) -> tuple[bool, str]:
    """Issue a real HTTP GET from inside a frontend client container.

    Returns (succeeded, body_snippet). A failed/timed-out connection means
    the firewall dropped the packets in transit, not that the service is down.
    """
    cmd = f"curl -s -m {timeout} -o - -w '\\nHTTP_STATUS:%{{http_code}}' http://{ip}:{port}/"
    rc, out, _ = run_in_container(container, cmd)
    return rc == 0 and "HTTP_STATUS:200" in out, out


class TestFirewallEnforcesPortIsolation:
    """
    Demonstrates that server2 has BOTH ports 80 and 8080 open and serving
    real content, but only port 80 is reachable from the frontend network.
    Port 8080 is reachable on the server itself (proving the service is not
    the reason for the failure) but is blocked centrally by the firewall's
    forward chain, which only allows 80/443.
    """

    def test_server2_serves_on_both_ports_locally(self, ensure_all_running):
        for port in (ALLOWED_PORT, BLOCKED_PORT):
            success = False
            err = ""

            for _ in range(5):
                rc, out, err = run_in_container(
                    "server2",
                    f"wget -qO- -T 3 http://localhost:{port}/"
                )

                if rc == 0 and "server2" in out:
                    success = True
                    break

            assert success, (
                f"server2 is not serving on its own port {port} locally: {err}"
            )

    def test_allowed_port_reaches_server_through_firewall(self, ensure_all_running):
        ok, out = http_get_from_container("client1", SERVER2_IP, ALLOWED_PORT)
        assert ok, (
            f"Expected HTTP 200 from {SERVER2_IP}:{ALLOWED_PORT} via the firewall "
            f"forward rule allowing port 80. Got: {out}"
        )

    def test_blocked_port_is_filtered_by_firewall_not_by_server(self, ensure_all_running):
        # server2 *is* listening on 8080 (proven above), so any failure here
        # is solely due to the firewall's forward-chain default-drop policy.
        ok, out = http_get_from_container("client1", SERVER2_IP, BLOCKED_PORT)

        assert not ok, (
            f"Port {BLOCKED_PORT} on {SERVER2_IP} unexpectedly succeeded through the "
            f"firewall. It should be silently dropped by the forward chain's "
            f"default-drop policy, since only ports 80/443 are explicitly allowed."
        )