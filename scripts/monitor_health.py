import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class NodeStatus:
    """Health status snapshot for a single firewall node."""
    container: str
    timestamp: str
    running: bool = False
    nftables_loaded: bool = False
    ssh_reachable: bool = False
    holds_vip: bool = False
    keepalived_running: bool = False
    ip_addresses: list = field(default_factory=list)
    ruleset_tables: list = field(default_factory=list)
    error: str = ""

    @property
    def healthy(self) -> bool:
        return self.running and self.nftables_loaded and self.ssh_reachable

    def status_line(self) -> str:
        """One-line summary for terminal output."""
        status = "HEALTHY" if self.healthy else "UNHEALTHY"
        vip = " [VIP MASTER]" if self.holds_vip else ""
        return f"  {self.container}: {status}{vip}"


@dataclass
class ClusterSnapshot:
    """Full cluster health snapshot at one point in time."""
    timestamp: str
    nodes: list = field(default_factory=list)
    vip_owner: Optional[str] = None
    all_healthy: bool = False
    event: str = ""   # e.g. "FAILOVER: fw1 -> fw2"


# =============================================================================
# MONITOR CLASS
# =============================================================================

class FirewallMonitor:
    """
    Polls Docker containers and checks their health.

    Args:
        fw_containers:  List of container names to monitor
        virtual_ip:     The Keepalived VIP to watch
        mgmt_ips:       Dict mapping container name to management IP
        output_file:    Optional path to write JSON log
    """

    VIRTUAL_IP = os.environ.get("VIRTUAL_IP", "172.20.0.100")
    FW_MGMT_IPS = {
        "fw1": os.environ.get("FW1_MGMT_IP", "172.20.0.11"),
        "fw2": os.environ.get("FW2_MGMT_IP", "172.20.0.12"),
        "fw3": os.environ.get("FW3_MGMT_IP", "172.20.0.13"),
    }

    def __init__(
        self,
        fw_containers: list = None,
        output_file: str = None,
    ):
        self.containers = fw_containers or ["fw1", "fw2", "fw3"]
        self.output_file = output_file
        self._history: list[ClusterSnapshot] = []
        self._last_vip_owner: Optional[str] = None

    # -------------------------------------------------------------------------
    # Low-level checks
    # -------------------------------------------------------------------------

    def _run(self, container: str, command: str) -> tuple[int, str]:
        """Run a command inside a container. Returns (returncode, output)."""
        try:
            result = subprocess.run(
                ["docker", "exec", container, "bash", "-c", command],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return -1, "TIMEOUT"
        except Exception as e:
            return -1, str(e)

    def _is_running(self, container: str) -> bool:
        """Check if the Docker container is currently running."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Running}}", container],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() == "true"
        except Exception:
            return False

    def _check_nftables(self, container: str) -> tuple[bool, list]:
        """Returns (is_loaded, list_of_table_names)."""
        rc, out = self._run(container, "nft list ruleset")
        if rc != 0:
            return False, []
        tables = [
            line.strip()
            for line in out.splitlines()
            if line.strip().startswith("table")
        ]
        return bool(tables), tables

    def _check_ssh(self, container: str) -> bool:
        """Return True if sshd is running inside the container."""
        rc, _ = self._run(container, "pgrep sshd")
        return rc == 0

    def _check_vip(self, container: str) -> bool:
        """Returns True if this container holds the VIP."""
        rc, out = self._run(container, f"ip addr show | grep {self.VIRTUAL_IP}")
        return rc == 0 and self.VIRTUAL_IP in out

    def _check_keepalived(self, container: str) -> bool:
        """Returns True if keepalived process is running."""
        rc, out = self._run(container, "pgrep keepalived")
        return rc == 0

    def _get_ip_addresses(self, container: str) -> list:
        """Return list of non-loopback IPv4 addresses on this container."""
        rc, out = self._run(container, "ip -4 addr show | grep inet | grep -v '127.0.0.1'")
        ips = []
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                ips.append(parts[1])   # e.g. "172.20.0.11/24"
        return ips

    # -------------------------------------------------------------------------
    # Snapshot collection
    # -------------------------------------------------------------------------

    def check_node(self, container: str) -> NodeStatus:
        """Collect a full health status for one node."""
        ts = datetime.now(timezone.utc).isoformat()
        status = NodeStatus(container=container, timestamp=ts)

        status.running = self._is_running(container)
        if not status.running:
            status.error = "Container not running"
            return status

        # nftables
        status.nftables_loaded, status.ruleset_tables = self._check_nftables(container)

        # SSH
        status.ssh_reachable = self._check_ssh(container)

        # VIP
        status.holds_vip = self._check_vip(container)

        # Keepalived
        status.keepalived_running = self._check_keepalived(container)

        # IP addresses
        status.ip_addresses = self._get_ip_addresses(container)

        return status

    def take_snapshot(self) -> ClusterSnapshot:
        """Poll all nodes and return a full cluster snapshot."""
        ts = datetime.now(timezone.utc).isoformat()
        snap = ClusterSnapshot(timestamp=ts)

        for container in self.containers:
            node_status = self.check_node(container)
            snap.nodes.append(node_status)
            if node_status.holds_vip:
                snap.vip_owner = container

        snap.all_healthy = all(n.healthy for n in snap.nodes)

        # Detect failover event
        if snap.vip_owner != self._last_vip_owner:
            if self._last_vip_owner is not None:
                snap.event = f"FAILOVER: {self._last_vip_owner} -> {snap.vip_owner}"
            self._last_vip_owner = snap.vip_owner

        return snap

    # -------------------------------------------------------------------------
    # Output
    # -------------------------------------------------------------------------

    def _print_snapshot(self, snap: ClusterSnapshot) -> None:
        """Print a formatted snapshot to stdout."""
        ts = datetime.now().strftime("%H:%M:%S")
        overall = "ALL HEALTHY" if snap.all_healthy else "DEGRADED"
        vip = snap.vip_owner or "NONE"
        print(f"\n[{ts}] Cluster: {overall}  |  VIP owner: {vip}")
        for node in snap.nodes:
            print(node.status_line())
        if snap.event:
            print(f"\n  *** EVENT: {snap.event} ***")

    def _save_snapshot(self, snap: ClusterSnapshot) -> None:
        """Append snapshot to the JSON output file."""
        if not self.output_file:
            return
        self._history.append(snap)
        try:
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            data = [asdict(s) for s in self._history]
            with open(self.output_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"  WARNING: Could not write health log: {e}", file=sys.stderr)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def check_once(self) -> ClusterSnapshot:
        """Take one snapshot, print it, save it. Returns the snapshot."""
        snap = self.take_snapshot()
        self._print_snapshot(snap)
        self._save_snapshot(snap)
        return snap

    def run_continuous(self, interval: float = 5.0) -> None:
        """
        Poll indefinitely every `interval` seconds.
        Press Ctrl+C to stop.
        """
        print(f"Starting health monitor (interval={interval}s)")
        print(f"Watching: {', '.join(self.containers)}")
        if self.output_file:
            print(f"Logging to: {self.output_file}")
        print("Press Ctrl+C to stop.\n")

        try:
            while True:
                self.check_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitor stopped.")


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Firewall node health monitor"
    )
    parser.add_argument(
        "--interval", type=float, default=5.0,
        help="Polling interval in seconds (default: 5)"
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Take one snapshot and exit"
    )
    parser.add_argument(
        "--output",
        default=os.environ.get("REPORT_DIR", "/test_results") + "/health.json",
        help="JSON output file path"
    )
    args = parser.parse_args()

    monitor = FirewallMonitor(output_file=args.output)

    if args.once:
        snap = monitor.check_once()
        sys.exit(0 if snap.all_healthy else 1)
    else:
        monitor.run_continuous(interval=args.interval)
