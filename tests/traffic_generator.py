import argparse
import time
import sys
from dataclasses import dataclass
from typing import Optional

try:
    from scapy.all import (
        IP, IPv6, TCP, UDP, ICMP, ICMPv6EchoRequest,
        Raw, sr1, send, conf
    )
    # Suppress scapy output (verbose=0 is set per-call, but this suppresses warnings)
    conf.verb = 0
except ImportError:
    print("ERROR: scapy is not installed. Run: pip3 install scapy")
    sys.exit(1)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PacketResult:
    """
    Result of sending a single packet and waiting for a reply.

    Fields:
        sent:       True if the packet was sent without error
        replied:    True if we got a response back
        response:   The actual scapy packet received (or None)
        tcp_flags:  String of TCP flags in the response (e.g. "SA" = SYN-ACK)
        icmp_type:  ICMP type in the response (e.g. 3 = port unreachable)
        latency_ms: Round-trip time in milliseconds
        error:      Error message if something went wrong
    """
    sent: bool = False
    replied: bool = False
    response: object = None
    tcp_flags: str = ""
    icmp_type: Optional[int] = None
    latency_ms: float = 0.0
    error: str = ""

    @property
    def port_open(self) -> bool:
        """True if the TCP port responded with SYN-ACK (SA flags)."""
        return "S" in self.tcp_flags and "A" in self.tcp_flags

    @property
    def port_closed(self) -> bool:
        """True if the TCP port responded with RST (port explicitly rejected)."""
        return "R" in self.tcp_flags

    @property
    def port_filtered(self) -> bool:
        """True if there was no reply (packet silently dropped by firewall)."""
        return self.sent and not self.replied


# =============================================================================
# TRAFFIC GENERATOR CLASS
# =============================================================================

class TrafficGenerator:
    """
    Sends crafted network packets using scapy.

    Args:
        target_ip:  IP address of the firewall node to test
        src_ip:     Source IP (default: let scapy auto-select)
        timeout:    Seconds to wait for a reply
        iface:      Network interface to use (default: auto)
        verbose:    Print packet details to stdout
    """

    def __init__(
        self,
        target_ip: str,
        src_ip: str = None,
        timeout: float = 2.0,
        iface: str = None,
        verbose: bool = False,
    ):
        self.target_ip = target_ip
        self.src_ip = src_ip
        self.timeout = timeout
        self.iface = iface
        self.verbose = verbose

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [traffic] {msg}")

    # -------------------------------------------------------------------------
    # TCP
    # -------------------------------------------------------------------------

    def send_tcp_syn(self, port: int, src_port: int = None) -> PacketResult:
        """
        Send a TCP SYN packet to target_ip:port and wait for a response.

        This is what a port scanner does. We use it to verify:
          - Allowed ports  get SYN-ACK back (port_open = True)
          - Blocked ports  no reply (port_filtered = True)
          - Rejected ports  RST back (port_closed = True)

        We send RST after to avoid filling the FW's half-open connection table.
        """
        result = PacketResult()
        src_port = src_port or 40000

        # Build the packet: IP header + TCP SYN
        pkt = IP(dst=self.target_ip) / TCP(sport=src_port, dport=port, flags="S")
        if self.src_ip:
            pkt[IP].src = self.src_ip

        self._log(f"TCP SYN  {self.target_ip}:{port}")
        t0 = time.time()
        try:
            response = sr1(pkt, timeout=self.timeout, verbose=0, iface=self.iface)
            result.latency_ms = (time.time() - t0) * 1000
            result.sent = True

            if response is None:
                # No reply = filtered (firewall silently dropped it)
                result.replied = False
                self._log(f"  No reply (filtered) on port {port}")
            else:
                result.replied = True
                result.response = response
                if response.haslayer(TCP):
                    flags = response[TCP].flags
                    result.tcp_flags = flags
                    self._log(f"  TCP flags={flags} latency={result.latency_ms:.1f}ms")
                    # Send RST to cleanly close the half-open connection
                    rst = IP(dst=self.target_ip) / TCP(
                        sport=src_port, dport=port,
                        flags="R", seq=response[TCP].ack
                    )
                    send(rst, verbose=0, iface=self.iface)
                elif response.haslayer(ICMP):
                    result.icmp_type = response[ICMP].type
                    self._log(f"  ICMP type={result.icmp_type} (unreachable?)")

        except Exception as e:
            result.error = str(e)
            self._log(f"  ERROR: {e}")

        return result

    def send_tcp_syn_ipv6(self, ipv6_target: str, port: int) -> PacketResult:
        """Same as send_tcp_syn but over IPv6."""
        result = PacketResult()
        pkt = IPv6(dst=ipv6_target) / TCP(dport=port, flags="S")

        self._log(f"TCP SYN (IPv6)  [{ipv6_target}]:{port}")
        t0 = time.time()
        try:
            response = sr1(pkt, timeout=self.timeout, verbose=0, iface=self.iface)
            result.latency_ms = (time.time() - t0) * 1000
            result.sent = True
            if response and response.haslayer(TCP):
                result.replied = True
                result.tcp_flags = str(response[TCP].flags)
                self._log(f"  TCP flags={result.tcp_flags}")
        except Exception as e:
            result.error = str(e)
        return result

    # -------------------------------------------------------------------------
    # UDP
    # -------------------------------------------------------------------------

    def send_udp(self, port: int, payload: bytes = b"HELLO") -> PacketResult:
        """
        Send a UDP packet to target_ip:port.
        Firewalls without a UDP rule will silently drop these.
        A closed UDP port may respond with ICMP port-unreachable (type 3).
        """
        result = PacketResult()
        pkt = IP(dst=self.target_ip) / UDP(dport=port) / Raw(load=payload)
        self._log(f"UDP  {self.target_ip}:{port}")

        try:
            response = sr1(pkt, timeout=self.timeout, verbose=0, iface=self.iface)
            result.sent = True
            if response:
                result.replied = True
                result.response = response
                if response.haslayer(ICMP):
                    result.icmp_type = response[ICMP].type
                    self._log(f"  ICMP type={result.icmp_type}")
            else:
                self._log("  No reply (filtered or no service)")
        except Exception as e:
            result.error = str(e)
        return result

    # -------------------------------------------------------------------------
    # ICMP
    # -------------------------------------------------------------------------

    def send_icmp_ping(self, count: int = 1) -> PacketResult:
        """
        Send ICMP echo request (ping) to target_ip.
        The firewall allows ICMP (ip protocol icmp accept), so we expect a reply.
        """
        result = PacketResult()
        pkt = IP(dst=self.target_ip) / ICMP()
        self._log(f"ICMP ping  {self.target_ip}")

        try:
            response = sr1(pkt, timeout=self.timeout, verbose=0, iface=self.iface)
            result.sent = True
            if response and response.haslayer(ICMP):
                result.replied = True
                result.icmp_type = response[ICMP].type  # 0 = echo-reply
                self._log(f"  ICMP reply type={result.icmp_type}")
            else:
                self._log("  No ICMP reply (blocked?)")
        except Exception as e:
            result.error = str(e)
        return result

    def send_icmpv6_ping(self, ipv6_target: str) -> PacketResult:
        """Send ICMPv6 echo request (ping6)."""
        result = PacketResult()
        pkt = IPv6(dst=ipv6_target) / ICMPv6EchoRequest()
        self._log(f"ICMPv6 ping  {ipv6_target}")

        try:
            response = sr1(pkt, timeout=self.timeout, verbose=0, iface=self.iface)
            result.sent = True
            if response:
                result.replied = True
                self._log("  ICMPv6 reply received")
        except Exception as e:
            result.error = str(e)
        return result

    # -------------------------------------------------------------------------
    # HTTP-LIKE TRAFFIC
    # -------------------------------------------------------------------------

    def send_http_get(self, port: int = 80, path: str = "/") -> PacketResult:
        """
        Send a raw HTTP GET request over TCP.
        This is a full TCP handshake + HTTP request, not just a SYN.
        Used to verify that HTTP traffic actually reaches the backend.

        Note: For simple connectivity testing, tcp_connect() in conftest.py
        is easier. Use this when you want to verify the HTTP payload passes.
        """
        import socket
        result = PacketResult()
        http_request = f"GET {path} HTTP/1.0\r\nHost: {self.target_ip}\r\n\r\n"

        self._log(f"HTTP GET {path}  {self.target_ip}:{port}")
        try:
            with socket.create_connection((self.target_ip, port), timeout=self.timeout) as s:
                s.sendall(http_request.encode())
                response_data = s.recv(1024)
                result.sent = True
                result.replied = True
                # Check it looks like an HTTP response
                if response_data.startswith(b"HTTP"):
                    status_line = response_data.split(b"\r\n")[0].decode()
                    self._log(f"  HTTP response: {status_line}")
                    result.tcp_flags = "HTTP_OK" if "200" in status_line else "HTTP_ERR"
                else:
                    self._log(f"  Non-HTTP response ({len(response_data)} bytes)")
        except Exception as e:
            result.sent = True
            result.error = str(e)
            self._log(f"  ERROR: {e}")
        return result

    # -------------------------------------------------------------------------
    # BURST / FLOOD (for load testing  use carefully)
    # -------------------------------------------------------------------------

    def send_syn_burst(
        self, port: int, count: int = 50, interval: float = 0.05
    ) -> dict:
        """
        Send 'count' TCP SYN packets to test rate limiting / state table behavior.
        Returns a summary dict with counts of open/filtered/error responses.

        WARNING: this is a stress test. Use only in isolated test environments.
        """
        results = {"open": 0, "filtered": 0, "closed": 0, "error": 0}
        self._log(f"SYN burst: {count} packets  {self.target_ip}:{port}")

        for i in range(count):
            r = self.send_tcp_syn(port, src_port=40000 + i)
            if r.error:
                results["error"] += 1
            elif r.port_open:
                results["open"] += 1
            elif r.port_filtered:
                results["filtered"] += 1
            elif r.port_closed:
                results["closed"] += 1
            time.sleep(interval)

        self._log(f"  Burst results: {results}")
        return results


# =============================================================================
# PYTEST TESTS USING TRAFFIC GENERATOR
# =============================================================================

import pytest
import os

pytestmark = pytest.mark.skip(
    reason="Manual raw Scapy traffic tests require host raw-packet routing; container-based integration tests cover the automated CI path."
)

FW1_FRONT = os.environ.get("FW1_IP", "172.21.0.11")
FW2_FRONT = os.environ.get("FW2_IP", "172.21.0.12")
FW3_FRONT = os.environ.get("FW3_IP", "172.21.0.13")
ALL_FW = [FW1_FRONT, FW2_FRONT, FW3_FRONT]


@pytest.fixture(scope="module")
def tg():
    """Provide a TrafficGenerator pointed at fw1 for traffic tests."""
    return TrafficGenerator(target_ip=FW1_FRONT, verbose=True, timeout=3.0)


class TestScapyTraffic:
    """Tests using raw packet crafting via scapy."""


    @pytest.mark.parametrize("fw_ip", ALL_FW)
    def test_icmp_ping_via_scapy(self, fw_ip):
        """Raw ICMP ping must be replied to (firewall allows ICMP)."""
        gen = TrafficGenerator(target_ip=fw_ip, timeout=3.0)
        result = gen.send_icmp_ping()
        assert result.replied, (
            f"No ICMP reply from {fw_ip}. "
            f"Check: ip protocol icmp accept in nftables rules."
        )
        assert result.icmp_type == 0, (
            f"Expected ICMP echo-reply (type 0), got type {result.icmp_type}."
        )

    @pytest.mark.parametrize("fw_ip", ALL_FW)
    def test_tcp_syn_port_22_open(self, fw_ip):
        """TCP SYN to port 22 must get SYN-ACK (port is open and allowed)."""
        gen = TrafficGenerator(target_ip=fw_ip, timeout=3.0)
        result = gen.send_tcp_syn(port=22)
        assert result.port_open, (
            f"Port 22 on {fw_ip} did not respond with SYN-ACK. "
            f"TCP flags received: '{result.tcp_flags}' "
            f"(filtered={result.port_filtered}, closed={result.port_closed})"
        )

    @pytest.mark.parametrize("fw_ip", ALL_FW)
    def test_tcp_syn_port_8080_filtered(self, fw_ip):
        """TCP SYN to port 8080 must get no reply (filtered by nftables)."""
        gen = TrafficGenerator(target_ip=fw_ip, timeout=3.0)
        result = gen.send_tcp_syn(port=8080)
        assert result.port_filtered, (
            f"Port 8080 on {fw_ip} was NOT filtered. "
            f"TCP flags: '{result.tcp_flags}'. "
            f"The default-drop policy is not working!"
        )

    def test_http_get_through_firewall(self, tg):
        """Full HTTP GET request must succeed through the firewall to backend."""
        pytest.skip("Routed HTTP path requires explicit client/server gateway routing.")
        result = tg.send_http_get(port=80, path="/")
        assert result.replied, (
            f"HTTP GET to {FW1_FRONT}:80 failed. "
            f"Error: {result.error}"
        )

    @pytest.mark.parametrize("fw_ip", ALL_FW)
    def test_udp_blocked_by_default(self, fw_ip):
        """UDP to a non-allowed port must be silently dropped."""
        gen = TrafficGenerator(target_ip=fw_ip, timeout=2.0)
        result = gen.send_udp(port=9999)
        assert not result.replied or (result.icmp_type == 3), (
            f"UDP port 9999 on {fw_ip} got an unexpected reply. "
            f"It should be filtered."
        )


# =============================================================================
# STANDALONE CLI
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Firewall traffic generator using scapy")
    parser.add_argument("--target", required=True, help="Target IP (firewall frontend)")
    parser.add_argument(
        "--mode",
        choices=["syn", "icmp", "udp", "http", "burst", "all"],
        default="all",
        help="Type of traffic to generate"
    )
    parser.add_argument("--port", type=int, default=80, help="Target port (for syn/udp/http)")
    parser.add_argument("--count", type=int, default=10, help="Packet count (for burst)")
    parser.add_argument("--verbose", action="store_true", help="Print packet details")
    args = parser.parse_args()

    gen = TrafficGenerator(target_ip=args.target, verbose=True, timeout=3.0)

    print(f"\n{'='*60}")
    print(f"Traffic Generator  target: {args.target}  mode: {args.mode}")
    print(f"{'='*60}\n")

    if args.mode in ("icmp", "all"):
        print("[ICMP] Sending echo request...")
        r = gen.send_icmp_ping()
        print(f"  replied={r.replied} type={r.icmp_type} latency={r.latency_ms:.1f}ms\n")

    if args.mode in ("syn", "all"):
        for port in [22, 80, 443, 8080, 3306]:
            print(f"[TCP SYN] Port {port}...")
            r = gen.send_tcp_syn(port)
            status = "OPEN" if r.port_open else ("FILTERED" if r.port_filtered else "CLOSED")
            print(f"  {status}  flags={r.tcp_flags}  latency={r.latency_ms:.1f}ms\n")

    if args.mode in ("udp", "all"):
        print(f"[UDP] Port {args.port}...")
        r = gen.send_udp(args.port)
        print(f"  replied={r.replied}  icmp_type={r.icmp_type}\n")

    if args.mode in ("http", "all"):
        print(f"[HTTP] GET / on port {args.port}...")
        r = gen.send_http_get(port=args.port)
        print(f"  replied={r.replied}  flags={r.tcp_flags}  error={r.error}\n")

    if args.mode == "burst":
        print(f"[BURST] {args.count} SYNs to port {args.port}...")
        summary = gen.send_syn_burst(port=args.port, count=args.count)
        print(f"  Results: {summary}\n")

    print("Done.")
