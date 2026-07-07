# Individual Report — Member 4: Monitoring and Diagnostics

**Name:** Aisana Sembek
**GitLab:** @asembek
**Project:** Cloud Computing Group 05 — Topic 5.2: Scalable Firewall with Debian 13 and nftables

---

## 1. My Responsibilities

As Member 4, I was responsible for the Monitoring and Diagnostics layer of the
project — making the firewall's activity observable and giving the team and the
reviewer visibility into what the firewall is actually doing at runtime:

- Collect and analyze firewall drop logs (blocked source IPs)
- Track active connections through the firewall
- Provide a web dashboard that shows the monitoring data live
- Add per-network bandwidth visibility
- Verify firewall rule integrity
- Send Telegram alerts for firewall events
- Make the monitoring data appear automatically, without manual steps

---

## 2. What I Implemented

### 2.1 Drop Logging Inside Docker (NFLOG + ulogd2)

The core problem in my part was that nftables drop logs were not visible inside
the containers. The standard nftables `log` statement writes to the kernel log,
which is not namespaced per container, so nothing appeared in the log file.

I solved this by switching the drop rule to **NFLOG** and running **ulogd2** to
capture it:

- the ruleset uses `log prefix "DROP-IN " group 1 counter drop` (NFLOG instead
  of the kernel log)
- `ulogd2` is installed in the firewall image and listens on that NFLOG group
- it writes the drops to `/var/log/firewall/dropped.log`, which the analyzer reads
- `ulogd2` is started automatically by supervisord

Verification:

```bash
docker exec fw1 nft list ruleset | grep group
docker exec fw1 cat /var/log/firewall/dropped.log
```

Output confirmed the NFLOG rule and real log lines with live source IPs, for
example:

```text
DROP-IN ... SRC=172.21.0.21 DST=172.21.0.11 PROTO=TCP ... DPT=9999 SYN
```

### 2.2 Log Analyzer — Blocked IPs

`monitoring/analyzers/log_analyzer.py` reads the drop log and counts how many
times each source IP was blocked. Verified on live traffic:

```text
{'total': 366, 'blocked_ips': {'172.21.0.2': 331, '172.22.0.1': 21, ...}}
```

### 2.3 Connection Analyzer

`monitoring/analyzers/conntrack_analyzer.py` parses `conntrack -L` and groups
active connections by protocol, state, and destination port. The first version
used `conntrack -L -o json`, but that JSON mode is not supported in our build,
so it silently returned zero even when the table was not empty. I found this by
comparing the output with the raw command, and rewrote it to parse the text
output. After the fix:

```text
{"by_protocol":{"tcp":1},"by_state":{"ESTABLISHED":1},"total":1}
```

### 2.4 Web Dashboard

`monitoring/dashboard/app.py` is a Flask application that serves the monitoring
data as an HTML page and as JSON endpoints. It runs inside `fw1` (started by
supervisord) and is published on port 5000.

Endpoints:

| Endpoint | Data |
|---|---|
| `/api/blocked` | Top blocked source IPs |
| `/api/connections` | Connections by protocol / state / port |
| `/api/bandwidth` | Per-interface bandwidth |
| `/api/health` | Service status |

The page (`templates/index.html`) shows the data as tables and live bars,
updating every two seconds, instead of raw JSON. I also had to allow port 5000
in the firewall ruleset, because the node was otherwise dropping its own
dashboard traffic.

### 2.5 Network Bandwidth (requested in the review)

In the review the professor asked me to show per-network bandwidth, like `iftop`
and `cbm`. `monitoring/analyzers/bandwidth_analyzer.py` reads the per-interface
byte counters from `/proc/net/dev` (the same kernel source those tools use),
takes two samples one second apart, and reports throughput in bytes per second.
The dashboard shows this as live bars labelled by network (Frontend, Backend,
Management). Verified under a flood ping:

```text
eth1: down 5.2 MB/s  up 5.2 MB/s
```

### 2.6 Rule Integrity Check

`monitoring/scripts/integrity_check.py` hashes the deployed `/etc/nftables.conf`
and reports when the ruleset changes. It was originally hashing an unused
prototype file; I changed the default to the real deployed file. Verified across
three states — first run stores the hash, unchanged run passes, and a modified
ruleset is detected:

```text
[PASS] First run: hash saved
[PASS] Rules unchanged
[FAIL] Rules have changed
```

### 2.7 Automatic Live Data (traffic-gen)

So the dashboard is not empty when someone opens it, I added a `traffic-gen`
service to `docker-compose.yml`. It runs in the frontend network and continuously
sends allowed and blocked traffic to the firewall, so blocked IPs and bandwidth
bars appear on the dashboard automatically after `docker compose up`, without any
manual command.

### 2.8 Telegram Alerts

`monitoring/alerts/telegram_bot.py` sends a message via the Telegram API, and
`monitoring/alerts/alert_monitor.py` watches the drop log and sends an alert when
a source IP is blocked many times. The alert monitor runs **on the host**, not
inside the firewall, because the firewall containers have no internet access and
cannot reach `api.telegram.org`. The bot token and chat id are passed through
environment variables and are never committed to git. Verified with a live alert:

```text
⚠️ Firewall alert: 172.21.0.2 blocked 375 times
```

---

## 3. Testing and Verification

All monitoring components were verified on the running Docker stack, not only in
theory:

| Component | Verification |
|---|---|
| Drop logging | Generated blocked traffic, confirmed real `SRC=` lines in the log |
| Log analyzer | Confirmed correct blocked-IP counts on live data |
| Connection analyzer | Confirmed real connections after the text-parsing fix |
| Dashboard | Opened `http://localhost:5000`, confirmed all endpoints return live data |
| Bandwidth | Confirmed correct MB/s under flood ping, zero on idle interfaces |
| Integrity check | Confirmed first-run / unchanged / changed detection |
| Telegram alert | Confirmed the alert arrived in Telegram |
| Reproducibility | Confirmed everything starts automatically after `--force-recreate` |

---

## 4. Git Commit History

| Commit | Description |
|---|---|
| `c36e054` | feat(monitoring): fix dashboard to show real logs, add rsyslog and log rule to nftables |
| `84f8d56` | fix(monitoring): remove demo data from conntrack analyzer, show real conntrack state |
| `46cfd1e` | fix(monitoring): fix indentation in conntrack_analyzer.py, remove demo data |
| `9721a24` | monitoring: log firewall drops via NFLOG group 1 + ulogd2 (works inside Docker) |
| `d4fa2f4` | monitoring: always write nftables default with NFLOG (package ships empty stub) |
| `202e465` | monitoring: check integrity of deployed /etc/nftables.conf instead of stale prototype |
| `252196a` | monitoring: add flask, fix dashboard paths, parse conntrack text output |
| `31a8206` | monitoring: add network bandwidth (per interface) to dashboard with visual bars |
| `6c197b9` | monitoring: add traffic-gen service so dashboard shows live data on startup |
| (later) | monitoring: add telegram alert monitor for blocked IPs (runs on host) |

---

## 5. Files I Created

```text
monitoring/dashboard/app.py                    Flask dashboard and JSON API (port 5000)
monitoring/dashboard/templates/index.html      Dashboard page (tables + bandwidth bars)
monitoring/analyzers/log_analyzer.py           Counts blocked source IPs from the drop log
monitoring/analyzers/conntrack_analyzer.py     Parses conntrack -L into protocol/state/port stats
monitoring/analyzers/bandwidth_analyzer.py     Per-interface bandwidth from /proc/net/dev
monitoring/scripts/integrity_check.py          Detects changes to the deployed nftables ruleset
monitoring/scripts/collect_metrics.py          Collects rule/connection metrics over time
monitoring/alerts/telegram_bot.py              Sends a single Telegram message (env-based secrets)
monitoring/alerts/alert_monitor.py             Host-side watcher that alerts on blocked-IP events
```

I also modified `docker/entrypoint.sh`, `docker/DockerFile`,
`docker/supervisord.conf`, and `docker-compose.yml` to install and start
ulogd2 and the dashboard, write the NFLOG default ruleset, allow the dashboard
port, mount the monitoring code, and add the traffic generator.

---

## 6. Challenges and Solutions

| Challenge | Solution |
|---|---|
| nftables drops not visible inside Docker | Switched from kernel `log` to NFLOG + ulogd2 |
| NFLOG rule lost on container restart | Moved the rule into the entrypoint / image instead of applying it manually |
| Empty nftables stub blocked the default | Made the entrypoint always write the ruleset |
| Connection analyzer returned zero | `conntrack -L -o json` unsupported; rewrote to parse text output |
| Integrity check watched the wrong file | Pointed it at the deployed `/etc/nftables.conf` |
| Firewall blocked its own dashboard | Added `tcp dport 5000 accept` to the ruleset |
| Dashboard empty on startup | Added a traffic-gen container for continuous live traffic |
| Bot could not reach Telegram from the firewall | Ran the alert monitor on the host, reading the log via a Docker volume |
| Git push rejected due to teammate commits | Used `git pull --no-rebase` before pushing |

---

## 7. AI Usage

I used Claude (Anthropic) as an explainer, code reviewer, and debugging partner.
It was not used to generate complete solutions without review. Every AI output
was applied to the live Docker stack and verified before being accepted, and
corrected when it did not match the real environment. The most valuable cases
were the ones where the AI's assumption was wrong and I found it through testing:
the unsupported conntrack JSON mode, the ruleset being lost on restart, and the
empty nftables stub overriding the default. My full AI documentation is in the
team AI-usage document.

---

## 8. Summary

I implemented the Monitoring and Diagnostics layer of the project. All assigned
work is complete and verified on the running stack:

- Firewall drop logging inside Docker via NFLOG + ulogd2 
- Blocked-IP analysis on live log data 
- Connection tracking analyzer (real conntrack output) 
- Web dashboard with tables and live bandwidth bars on port 5000 
- Per-network bandwidth from `/proc/net/dev`, as requested in the review 
- Rule integrity check on the deployed ruleset 
- Automatic live data via a traffic-generator container 
- Telegram alerts for blocked-IP events (host-side) 
