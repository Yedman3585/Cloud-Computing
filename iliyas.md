# Individual Report — Member 1: Firewall Core and High Availability

**Name:** Iliyas Naizabek  
**GitLab:** @inaizabek  
**Branch:** `iliyas-nftables`  
**Project:** Cloud Computing Group 05 — Topic 5.2: Scalable Firewall with Debian 13 and nftables  
**Date:** July 2026

---

## 1. My Responsibilities

As Member 1, I was responsible for the Firewall Core and High Availability layer of the project:

- Implement nftables firewall rules for IPv4 and IPv6
- Automate rule generation using Jinja2 templates and Python
- Configure Keepalived VRRP for automatic failover
- Configure conntrackd for connection state synchronization
- Write a custom Ansible module for nftables rule management
- Test failover scenarios and verify correct behavior

---

## 2. What I Implemented

### 2.1 nftables Stateful Firewall

I implemented a stateful firewall using nftables on Debian 13. The firewall uses a default-drop policy, meaning all traffic is blocked unless explicitly allowed.

The base configuration includes:

- `table inet filter` with `input`, `forward`, and `output` chains
- `policy drop` on input and forward
- Explicit accept rules for: established/related connections, loopback, ICMP/ICMPv6, SSH (port 22), HTTP (port 80), HTTPS (port 443)

Validation command and expected output:

```bash
sudo nft list ruleset
```

```text
table ip filter {
    chain input {
        type filter hook input priority filter; policy drop;
        ct state established,related accept
        iif "lo" accept
        tcp dport 22 accept
        tcp dport 80 accept
        tcp dport 443 accept
        ip saddr 192.168.64.0/24 accept
        ip saddr 10.0.0.0/8 accept
        ip protocol icmp accept
    }
}
table ip6 filter {
    chain input {
        type filter hook input priority filter; policy drop;
        ct state established,related accept
        iif "lo" accept
        tcp dport 22 accept
        tcp dport 80 accept
        tcp dport 443 accept
        ip6 saddr ::1 accept
        ip6 saddr fd00::/8 accept
        ip6 nexthdr ipv6-icmp accept
    }
}
```

### 2.2 Jinja2 Templates and Python Automation

Instead of writing static nftables files, I implemented an Infrastructure as Code approach using Jinja2 templates.

**Files created:**

| File | Purpose |
|---|---|
| `templates/nftables_ipv4.j2` | Jinja2 template for IPv4 rules |
| `templates/nftables_ipv6.j2` | Jinja2 template for IPv6 rules |
| `vars.yml` | Variables: allowed ports, allowed IPs, hosts |
| `render.py` | Python script that renders templates and generates rule files |
| `generated_ipv4.nft` | Output: generated IPv4 nftables config |
| `generated_ipv6.nft` | Output: generated IPv6 nftables config |

The template uses Jinja2 loops and variables:

```jinja2
{% for port in allowed_ports %}
tcp dport {{ port }} accept
{% endfor %}

{% for ip in allowed_ips %}
ip saddr {{ ip }} accept
{% endfor %}
```

### 2.3 Hostname Resolution (Task 4)

I extended `render.py` to automatically resolve hostnames to IPv4 and IPv6 addresses at rule generation time using Python's `socket.getaddrinfo()`. Resolved addresses are inserted into the generated rules with comments for traceability.

```python
for hostname in data.get('hosts', []):
    entry = {'name': hostname, 'ipv4': None, 'ipv6': None}
    for res in socket.getaddrinfo(hostname, None):
        if res[0].name == 'AF_INET' and not entry['ipv4']:
            entry['ipv4'] = res[4][0]
        if res[0].name == 'AF_INET6' and not entry['ipv6']:
            entry['ipv6'] = res[4][0]
    resolved.append(entry)
```

Generated rule example:

```text
ip saddr 127.0.0.1 accept comment "localhost"
ip saddr 127.0.1.1 accept comment "debian"
```

### 2.4 Keepalived VRRP (Task 5)

I set up two Docker containers (`node1` and `node2`) on a dedicated Docker network (`ha-network`, subnet `172.20.0.0/24`) and configured Keepalived with VRRP unicast mode, because Docker does not support multicast.

**Configuration summary:**

| Parameter | node1 (MASTER) | node2 (BACKUP) |
|---|---|---|
| IP address | 172.20.0.2 | 172.20.0.3 |
| State | MASTER | BACKUP |
| Priority | 100 | 90 |
| Virtual IP (VIP) | 172.20.0.100 | — |

Unicast is used instead of multicast because Docker bridge networks do not forward multicast traffic between containers.

**Failover test result:**

```bash
sudo docker exec node1 pkill keepalived
sleep 4
sudo docker exec node2 ip addr show eth0 | grep 172.20.0.100
```

Output confirmed VIP moved to node2:

```text
inet 172.20.0.100/24 scope global secondary proto keepalived eth0
```

VIP returned to node1 after Keepalived was restarted on node1.

### 2.5 conntrackd Connection State Synchronization (Task 6)

I configured conntrackd on both nodes to synchronize the Linux connection tracking table over UDP port 3780. This ensures that established TCP sessions are not dropped when failover occurs and the backup node takes over.

**Sync verification:**

```bash
sudo docker exec node1 conntrackd -C /etc/conntrackd/conntrackd.conf -s
```

```text
UDP traffic (active device=eth0):
    11504 Bytes sent    11464 Bytes recv
     1438 Pckts sent    1433 Pckts recv
        0 Error send       0 Error recv
```

Both nodes showed non-zero sent and received packet counts with zero errors, confirming bidirectional synchronization.

### 2.6 Custom Ansible Module (Task 7)

I wrote a custom Python Ansible module `library/nftables_rule.py` that manages individual nftables rules in an idempotent way. The module supports `state: present` and `state: absent`.

**Key properties:**

- Checks whether the rule already exists before adding it
- Uses `nft list chain` to inspect current state
- Uses `nft add rule` to add new rules
- Uses `nft delete rule` with handle lookup to remove rules
- Returns `changed: true` only when the rule set actually changes

**Idempotence demonstration:**

First run:

```text
TASK [Allow port 8080]
changed: [localhost]
PLAY RECAP: ok=2 changed=1 failed=0
```

Second run (no changes):

```text
TASK [Allow port 8080]
ok: [localhost]
PLAY RECAP: ok=2 changed=0 failed=0
```

### 2.7 Sync Check Script (Task 8)

I wrote `check_sync.sh` to verify that conntrackd is actively synchronizing between nodes. The script queries both nodes, compares sent/received packet counts, and reports OK or WARN.

```bash
./check_sync.sh
```

```text
Node1: sent=2156 recv=2151
Node2: sent=2151 recv=2153
OK: nodes are syncing with each other
```

### 2.8 Integration Script (Task 9)

I wrote `integrate.sh` which runs all components in sequence and reports status for each step:

1. Generate nftables rules via `render.py`
2. Apply rules via `nft -f`
3. Start Keepalived and verify VIP ownership
4. Check conntrackd sync status

### 2.9 Ansible Inventory and Playbook

I created the Ansible inventory and playbook structure for deploying the firewall configuration to nodes:

- `ansible/inventory/hosts.yml` — YAML inventory with firewall nodes, roles, priorities, and shared variables
- `ansible/site.yml` — playbook that installs packages, deploys nftables templates, Keepalived config, and conntrackd config
- `ansible/templates/` — Jinja2 templates for keepalived.conf and conntrackd.conf adapted for multi-node deployment

The playbook installs required packages including `tcpdump`, `iftop`, and `cbm` as specified in the project requirements.

---

## 3. Failover Test Results (Task 10)

I wrote `test_failover.sh` covering three failure scenarios:

| Test | Scenario | Result |
|---|---|---|
| Test 1 | node1 Keepalived stops → VIP moves to node2 | **PASS** |
| Test 2 | nftables rules flushed → rules restored from generated files | **PASS** |
| Test 3 | conntrackd sync check after failover | **PASS** |

```text
===============================
  Results: PASS=3 FAIL=0
===============================
  ALL TESTS PASSED
```

---

## 4. Git Commit History

All my work was committed to the `iliyas-nftables` branch:

| Commit | Description |
|---|---|
| `1152b7c` | Created nftables base config |
| `3ce5cfc` | Fixed Jinja2 IPv4 template |
| `a8268e3` | Created and added Jinja2 IPv6 template |
| `165976a` | Hostname resolution added to render.py and IPv4 template |
| `1a41f8c` | Keepalived and conntrackd configs for node1 and node2 |
| `86aad76` | Separate configs for node1 and node2 |
| `c0dae09` | Custom Ansible module for nftables + test playbook |
| `b1381bd` | conntrackd sync check script |
| `21ba4ae` | Integration script for all components |
| `00373f8` | Integration and failover tests — All Passed |

---

## 5. Files I Created

```text
nftables.conf                        Base nftables config
templates/nftables_ipv4.j2           Jinja2 IPv4 template
templates/nftables_ipv6.j2           Jinja2 IPv6 template
vars.yml                             Variables for templates
render.py                            Python render script
generated_ipv4.nft                   Generated IPv4 rules
generated_ipv6.nft                   Generated IPv6 rules
keepalived/node1.conf                Keepalived config for MASTER
keepalived/node2.conf                Keepalived config for BACKUP
conntrackd/node1.conf                conntrackd config for node1
conntrackd/node2.conf                conntrackd config for node2
library/nftables_rule.py             Custom Ansible module
test_playbook.yml                    Ansible test playbook
check_sync.sh                        conntrackd sync verification
integrate.sh                         Full integration script
test_failover.sh                     Failover test script (3 scenarios)
ansible/inventory/hosts.yml          Ansible YAML inventory
ansible/site.yml                     Ansible deployment playbook
ansible/templates/keepalived.conf.j2 Keepalived Jinja2 template
ansible/templates/conntrackd.conf.j2 conntrackd Jinja2 template
```

---

## 6. Challenges and Solutions

| Challenge | Solution |
|---|---|
| Docker does not support VRRP multicast | Used Keepalived unicast mode with explicit peer IPs |
| nftables rules duplicated on each apply | Added `flush ruleset` to the top of the IPv4 template |
| IPv4 addresses used in IPv6 rules | Separated `vars.yml` into IPv4 and IPv6 address lists |
| Ansible could not connect to Docker containers | Added user to `docker` group with `usermod -aG docker` |
| `pkill` not available in containers | Installed `procps` package inside containers |
| Git push rejected due to teammate commits | Used `git pull` with `pull.rebase false` before pushing |

---

## 7. AI Usage

I used Claude (Anthropic) as an AI assistant during this project. The AI helped with:

- Explaining nftables syntax and stateful firewall concepts
- Debugging Jinja2 template errors
- Writing the custom Ansible module structure
- Identifying and fixing typos in Python code (e.g. `vars_data` vs `data`, `resolveg` vs `resolved`)
- Explaining Keepalived VRRP unicast configuration for Docker environments

All AI-generated code was reviewed, tested, and verified to work correctly before committing. The final validation was always done by running the actual commands and checking real output.

---

## 8. Summary

I successfully implemented the Firewall Core and High Availability layer for the project. All assigned tasks are complete and tested:

- Stateful nftables firewall with IPv4 and IPv6 rules ✅
- Jinja2 template-based rule generation (Infrastructure as Code) ✅
- Hostname to IP resolution in rule generation ✅
- Keepalived VRRP failover with VIP migration ✅
- conntrackd connection state synchronization ✅
- Custom idempotent Ansible module for nftables ✅
- Automated failover tests — PASS=3, FAIL=0 ✅
- Ansible inventory and playbook for multi-node deployment ✅
