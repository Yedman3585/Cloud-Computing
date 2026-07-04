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
    held_vips: list = field(default_factory=list)
    keepalived_running: bool = False
    conntrackd_running: bool = False
    ip_addresses: list = field(default_factory=list)
    ruleset_tables: list = field(default_factory=list)
    error: str = ""

    @property
    def healthy(self) -> bool:
        return self.running and self.nftables_loaded and self.ssh_reachable

    def status_line(self) -> str:
        """One-line summary for terminal output."""
        status = "HEALTHY" if self.healthy else "UNHEALTHY"
        vip = f" [VIPS: {', '.join(self.held_vips)}]" if self.held_vips else ""
        return f"  {self.container}: {status}{vip}"


@dataclass
class ClusterSnapshot:
    """Full cluster health snapshot at one point in time."""
    timestamp: str
    nodes: list = field(default_factory=list)
    vip_owners: dict = field(default_factory=dict)   # {"mgmt": "fw1", "frontend": "fw1", ...}
    split_brain_vips: list = field(default_factory=list)  # VIPs owned by 2+ nodes in repeated snapshots
    transient_split_brain_vips: list = field(default_factory=list)  # one-snapshot overlap during failover/preemption
    missing_vips: list = field(default_factory=list)  # VIPs temporarily owned by no node
    all_healthy: bool = False
    all_vips_consistent: bool = False  # all VIPs owned by the exact same single node
    event: str = ""   # e.g. "FAILOVER: fw1 -> fw2" or "SPLIT-BRAIN: frontend"


# =============================================================================
# MONITOR CLASS
# =============================================================================

class FirewallMonitor:
    """
    Polls Docker containers and checks their health.

    Tracks all three cluster VIPs (mgmt, frontend, backend) so a split-brain
    on any single network is detected, not just on the management VIP.
    """

    VIPS = {
        "mgmt": os.environ.get("VIRTUAL_IP", "172.20.0.100"),
        "frontend": os.environ.get("FRONTEND_VIP", "172.21.0.100"),
        "backend": os.environ.get("BACKEND_VIP", "172.22.0.100"),
    }
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
        self._last_vip_owners: dict = {}
        self._split_brain_streaks: dict[str, int] = {name: 0 for name in self.VIPS}
        self._split_brain_confirm_after = 2
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

    def _check_vip(self, container: str, vip_ip: str) -> bool:
        """Returns True if this container currently holds the given VIP."""
        rc, out = self._run(container, f"ip addr show | grep {vip_ip}")
        return rc == 0 and vip_ip in out

    def _check_keepalived(self, container: str) -> bool:
        """Returns True if keepalived process is running."""
        rc, _ = self._run(container, "pgrep -x keepalived")
        return rc == 0

    def _check_conntrackd(self, container: str) -> bool:
        """Returns True if conntrackd process is running."""
        rc, _ = self._run(container, "pgrep -x conntrackd")
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

        status.nftables_loaded, status.ruleset_tables = self._check_nftables(container)
        status.ssh_reachable = self._check_ssh(container)
        status.keepalived_running = self._check_keepalived(container)
        status.conntrackd_running = self._check_conntrackd(container)
        status.ip_addresses = self._get_ip_addresses(container)

        for vip_name, vip_ip in self.VIPS.items():
            if self._check_vip(container, vip_ip):
                status.held_vips.append(vip_name)

        return status

    def take_snapshot(self) -> ClusterSnapshot:
        """Poll all nodes and return a full cluster snapshot."""
        ts = datetime.now(timezone.utc).isoformat()
        snap = ClusterSnapshot(timestamp=ts)

        node_statuses = [self.check_node(c) for c in self.containers]
        snap.nodes = node_statuses

        # Determine owner(s) of each VIP independently.
        owners_by_vip: dict[str, list] = {name: [] for name in self.VIPS}
        for node in node_statuses:
            for vip_name in node.held_vips:
                owners_by_vip[vip_name].append(node.container)

        snap.vip_owners = {
            name: owners[0] if len(owners) == 1 else (owners or None)
            for name, owners in owners_by_vip.items()
        }
        current_split_brain_vips = [
            name for name, owners in owners_by_vip.items() if len(owners) > 1
        ]
        snap.missing_vips = [
            name for name, owners in owners_by_vip.items() if len(owners) == 0
        ]

        snap.split_brain_vips = []
        snap.transient_split_brain_vips = []
        for vip_name in self.VIPS:
            if vip_name in current_split_brain_vips:
                self._split_brain_streaks[vip_name] += 1
                if self._split_brain_streaks[vip_name] >= self._split_brain_confirm_after:
                    snap.split_brain_vips.append(vip_name)
                else:
                    snap.transient_split_brain_vips.append(vip_name)
            else:
                self._split_brain_streaks[vip_name] = 0

        single_owners = {
            name: owners[0] for name, owners in owners_by_vip.items() if len(owners) == 1
        }
        snap.all_vips_consistent = (
            not current_split_brain_vips
            and not snap.missing_vips
            and len(set(single_owners.values())) == 1
        )

        snap.all_healthy = all(n.healthy for n in node_statuses) and snap.all_vips_consistent

        # Detect failover / split-brain events relative to the previous snapshot.
        events = []
        for vip_name, owner in snap.vip_owners.items():
            previous = self._last_vip_owners.get(vip_name)
            if isinstance(owner, str) and owner != previous:
                if isinstance(previous, str):
                    events.append(f"FAILOVER[{vip_name}]: {previous} -> {owner}")
                self._last_vip_owners[vip_name] = owner
        if snap.split_brain_vips:
            events.append(f"CONFIRMED SPLIT-BRAIN detected on: {', '.join(snap.split_brain_vips)}")
        if snap.missing_vips:
            events.append(f"VIP owner temporarily missing on: {', '.join(snap.missing_vips)}")
        snap.event = "; ".join(events)

        return snap

    # -------------------------------------------------------------------------
    # Output
    # -------------------------------------------------------------------------

    def _print_snapshot(self, snap: ClusterSnapshot) -> None:
        """Print a formatted snapshot to stdout."""
        ts = datetime.now().strftime("%H:%M:%S")
        overall = "ALL HEALTHY" if snap.all_healthy else "DEGRADED"
        vips_str = ", ".join(f"{k}={v or 'NONE'}" for k, v in snap.vip_owners.items())
        print(f"\n[{ts}] Cluster: {overall}  |  VIPs: {vips_str}")
        for node in snap.nodes:
            print(node.status_line())
        if snap.split_brain_vips:
            print(f"\n  *** WARNING: CONFIRMED SPLIT-BRAIN on {', '.join(snap.split_brain_vips)} ***")
        if snap.transient_split_brain_vips:
            print(f"\n  *** TRANSIENT VIP overlap on {', '.join(snap.transient_split_brain_vips)} ***")
        if snap.missing_vips:
            print(f"\n  *** VIP owner temporarily missing on {', '.join(snap.missing_vips)} ***")
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
        print(f"Tracking VIPs: {self.VIPS}")
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
        description="Firewall cluster health monitor (mgmt/frontend/backend VIPs)"
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
