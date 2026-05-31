import argparse
import json
import os
import sys
from datetime import datetime


# =============================================================================
# DATA LOADING
# =============================================================================

def load_pytest_results(path: str) -> dict:
    """
    Load pytest JSON results.
    Compatible with pytest-json-report plugin output format.
    """
    if not os.path.exists(path):
        print(f"WARNING: pytest JSON not found at {path}", file=sys.stderr)
        return {}
    with open(path) as f:
        return json.load(f)


def load_health_log(path: str) -> list:
    """Load health monitor snapshots from JSON log."""
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


# =============================================================================
# SUMMARY COMPUTATION
# =============================================================================

def compute_summary(pytest_data: dict) -> dict:
    """Extract pass/fail/skip counts and test list from pytest JSON."""
    if not pytest_data:
        return {
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "total": 1,
            "duration": 0,
            "success": False,
            "tests": [],
        }

    summary = pytest_data.get("summary", {})
    tests = list(pytest_data.get("tests", []))
    collector_failures = [
        collector
        for collector in pytest_data.get("collectors", [])
        if collector.get("outcome") == "failed"
    ]

    for collector in collector_failures:
        tests.append(
            {
                "nodeid": collector.get("nodeid", "collection"),
                "outcome": "failed",
                "duration": 0,
                "call": {"longrepr": collector.get("longrepr", "")},
            }
        )

    exitcode = pytest_data.get("exitcode", 0)
    passed = summary.get("passed", 0)
    skipped = summary.get("skipped", 0)
    failed = summary.get("failed", 0) + len(collector_failures)
    if exitcode != 0 and failed == 0:
        failed = 1
    total = summary.get("total", len(tests))
    if total == 0 and failed:
        total = failed
    duration = pytest_data.get("duration", 0)

    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": total,
        "duration": round(duration, 2),
        "success": exitcode == 0 and failed == 0,
        "tests": tests,
    }


def compute_health_summary(snapshots: list) -> dict:
    """Summarise health log: failover events, uptime %, etc."""
    if not snapshots:
        return {}

    events = [s for s in snapshots if s.get("event")]
    vip_owners = [s.get("vip_owner") for s in snapshots if s.get("vip_owner")]
    healthy_snaps = sum(1 for s in snapshots if s.get("all_healthy"))

    return {
        "total_snapshots": len(snapshots),
        "failover_events": [s["event"] for s in events],
        "failover_count": len(events),
        "cluster_uptime_pct": round(healthy_snaps / len(snapshots) * 100, 1) if snapshots else 0,
        "vip_owners": list(set(vip_owners)),
    }


# =============================================================================
# HTML GENERATION
# =============================================================================

def badge(passed: bool) -> str:
    if passed:
        return '<span style="background:#2d6a4f;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">PASS</span>'
    return '<span style="background:#9b2226;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">FAIL</span>'


def generate_html(summary: dict, health_summary: dict, generated_at: str) -> str:
    """Generate the full self-contained HTML report."""

    tests = summary.get("tests", [])
    pass_color = "#2d6a4f" if summary["success"] else "#9b2226"
    pass_label = "ALL PASSED" if summary["success"] else f"{summary['failed']} FAILED"

    # Build test rows
    test_rows = []
    for t in tests:
        name = t.get("nodeid", "unknown")
        outcome = t.get("outcome", "unknown")
        dur = round(t.get("duration", 0), 3)
        passed = outcome == "passed"
        row_bg = "#f0fff4" if passed else "#fff0f0"
        b = badge(passed)
        longrepr = ""
        if not passed and t.get("call", {}).get("longrepr"):
            msg = str(t["call"]["longrepr"])[:300].replace("<", "&lt;").replace(">", "&gt;")
            longrepr = f'<div style="color:#9b2226;font-size:11px;margin-top:4px;font-family:monospace">{msg}</div>'
        test_rows.append(
            f'<tr style="background:{row_bg}">'
            f'<td style="padding:6px 8px;font-family:monospace;font-size:12px">{name}</td>'
            f'<td style="padding:6px 8px;text-align:center">{b}</td>'
            f'<td style="padding:6px 8px;text-align:right;color:#555">{dur}s</td>'
            f'</tr>'
            + (f'<tr style="background:{row_bg}"><td colspan="3" style="padding:2px 8px 8px">{longrepr}</td></tr>' if longrepr else "")
        )

    test_table = "\n".join(test_rows) if test_rows else "<tr><td colspan='3'>No test data</td></tr>"

    # Failover events
    events_html = ""
    for ev in health_summary.get("failover_events", []):
        events_html += f'<div style="background:#fff3cd;border-left:4px solid #f0ad4e;padding:8px 12px;margin:4px 0;font-family:monospace">{ev}</div>'
    if not events_html:
        events_html = '<div style="color:#555;font-style:italic">No failover events recorded.</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Firewall Test Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          margin: 0; padding: 24px; background: #f8f9fa; color: #212529; }}
  h1   {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
  h2   {{ font-size: 16px; font-weight: 600; margin: 28px 0 12px; border-bottom: 1px solid #dee2e6; padding-bottom: 6px; }}
  .card {{ background: #fff; border: 1px solid #dee2e6; border-radius: 8px;
           padding: 20px; margin-bottom: 20px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px,1fr)); gap: 16px; }}
  .stat {{ text-align: center; }}
  .stat .value {{ font-size: 36px; font-weight: 700; }}
  .stat .label {{ font-size: 12px; color: #6c757d; margin-top: 2px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th    {{ background: #f1f3f5; padding: 8px; text-align: left; font-weight: 600;
           border-bottom: 2px solid #dee2e6; }}
  tr:hover {{ filter: brightness(0.97); }}
  .meta {{ color: #6c757d; font-size: 12px; margin-top: 4px; }}
</style>
</head>
<body>
<h1>Firewall Test Report</h1>
<div class="meta">Generated: {generated_at} &nbsp;-&nbsp; Duration: {summary.get('duration', 0)}s</div>

<div class="card" style="margin-top:20px">
  <div style="font-size:18px;font-weight:600;color:{pass_color};margin-bottom:16px">{pass_label}</div>
  <div class="grid">
    <div class="stat">
      <div class="value" style="color:#2d6a4f">{summary.get('passed', 0)}</div>
      <div class="label">Passed</div>
    </div>
    <div class="stat">
      <div class="value" style="color:#9b2226">{summary.get('failed', 0)}</div>
      <div class="label">Failed</div>
    </div>
    <div class="stat">
      <div class="value" style="color:#6c757d">{summary.get('skipped', 0)}</div>
      <div class="label">Skipped</div>
    </div>
    <div class="stat">
      <div class="value">{summary.get('total', 0)}</div>
      <div class="label">Total</div>
    </div>
    <div class="stat">
      <div class="value">{health_summary.get('cluster_uptime_pct', 'N/A')}%</div>
      <div class="label">Cluster uptime</div>
    </div>
    <div class="stat">
      <div class="value">{health_summary.get('failover_count', 0)}</div>
      <div class="label">Failover events</div>
    </div>
  </div>
</div>

<div class="card">
  <h2>Failover Events</h2>
  {events_html}
</div>

<div class="card">
  <h2>Test Results</h2>
  <table>
    <thead>
      <tr>
        <th>Test ID</th>
        <th style="text-align:center;width:80px">Result</th>
        <th style="text-align:right;width:80px">Duration</th>
      </tr>
    </thead>
    <tbody>
      {test_table}
    </tbody>
  </table>
</div>

</body>
</html>"""


# =============================================================================
# SUMMARY JSON
# =============================================================================

def write_summary_json(summary: dict, health_summary: dict, output_dir: str) -> None:
    """Write a machine-readable summary for CI systems to parse."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "test_summary": {k: v for k, v in summary.items() if k != "tests"},
        "health_summary": health_summary,
    }
    path = os.path.join(output_dir, "summary.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Summary JSON: {path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    report_dir = os.environ.get("REPORT_DIR", "/test_results")

    parser = argparse.ArgumentParser(description="Generate HTML test report")
    parser.add_argument(
        "--pytest-json",
        default=os.path.join(report_dir, "pytest.json"),
        help="Path to pytest JSON report (from pytest-json-report)"
    )
    parser.add_argument(
        "--health-json",
        default=os.path.join(report_dir, "health.json"),
        help="Path to health monitor JSON log"
    )
    parser.add_argument(
        "--output",
        default=os.path.join(report_dir, "report.html"),
        help="Output HTML file path"
    )
    args = parser.parse_args()

    print(f"Loading pytest results from: {args.pytest_json}")
    pytest_data = load_pytest_results(args.pytest_json)
    summary = compute_summary(pytest_data)

    print(f"Loading health log from: {args.health_json}")
    snapshots = load_health_log(args.health_json)
    health_summary = compute_health_summary(snapshots)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html = generate_html(summary, health_summary, generated_at)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        f.write(html)
    print(f"HTML report: {args.output}")

    write_summary_json(summary, health_summary, os.path.dirname(args.output))

    # Exit 1 if tests failed (useful for CI)
    sys.exit(0 if summary.get("success", False) else 1)


if __name__ == "__main__":
    main()
