# Team Integration Notes

## Purpose

This document records how teammate updates were integrated into the Member 5 Ansible work and which parts still need coordination.

The main rule for integration is simple: Ansible remains the canonical rollout layer. Teammate files can provide topology, tests, rule ideas, and service behavior, but final deployment should flow through `ansible/playbooks/site.yml` and the roles under `ansible/roles/`.

## Branches Reviewed

| Branch | Main Content | Integration Decision |
|---|---|---|
| `origin/said-testing` | Docker Compose topology, firewall/client images, pytest tests, helper scripts | Imported selectively and adapted to the Ansible inventory contract |
| `origin/iliyas-nftables` | nftables prototype, two-node Keepalived/conntrackd configs, shell tests, Kubernetes examples | Reviewed read-only; not merged directly because it would delete the Member 5 Ansible structure |
| `origin/monitoring-aisana` | Monitoring dashboard, metrics scripts, integrity check, Telegram alert prototype | Sanitized and imported only source code; excluded virtualenv, pycache, and hardcoded Telegram credentials |
| `origin/ci/cd-setup` and related DevOps branches | CI/CD and deployment material | Reviewed; existing GitLab validation kept because it matches the current Ansible/Docker baseline |

## Integrated From Member 2

The Docker Compose topology was imported and normalized:

- three firewall containers: `fw1`, `fw2`, `fw3`
- management network: `172.20.0.0/24`
- frontend network: `172.21.0.0/24`
- backend network: `172.22.0.0/24`
- frontend clients: `client1`, `client2`, `client3`
- backend web servers: `server1`, `server2`
- optional `test_runner` profile

The Ansible inventory now matches this topology in `ansible/inventory/hosts.yml`.

For the Docker lab, firewall hosts use the `community.docker.docker` Ansible connection plugin. This avoids relying on Docker bridge IPs being directly reachable from the WSL host. The inventory still stores static IPv4 and IPv6 fields such as `ipv4_addr` and `ipv6_addr`; those values remain the source of truth for firewall rule generation.

Inside the current Docker firewall containers the interface mapping is:

- `eth2`: management/HA peer network `172.20.0.0/24`
- `eth1`: frontend network `172.21.0.0/24`
- `eth0`: backend network `172.22.0.0/24`

Keepalived and conntrackd are therefore bound to `eth2` in the Docker group variables.

For VM or physical deployment, use a separate inventory that points `ansible_host` to real host addresses and uses SSH instead of the Docker connection plugin. The roles themselves stay free of Docker-specific commands.

## Reviewed From Member 1

The Member 1 branch contains useful prototype ideas:

- nftables IPv4 and IPv6 templates
- VRRP configuration examples
- conntrackd synchronization examples
- failover shell test ideas

However, it should not be merged directly in its current form because:

- it removes the current `ansible/` structure from Member 5
- it contains two-node Keepalived and conntrackd examples instead of the required three-node cluster
- it uses static files under root folders rather than Ansible role templates
- it has older Docker and script assumptions such as `node1` and `node2` instead of `fw1`, `fw2`, `fw3`
- it stores prototype secrets such as `secret123` directly in static config files

The correct integration path is to move the useful logic into:

- `ansible/group_vars/all.yml` for inventory-driven firewall objects and rules
- `ansible/roles/firewall/templates/nftables.conf.j2` for final nftables rendering
- `ansible/roles/keepalived/templates/keepalived.conf.j2` for VRRP config generation
- `ansible/roles/conntrackd/templates/conntrackd.conf.j2` for connection sync config generation
- `tests/` for updated three-node failover and conntrackd validation

## Current Connected State

Member 5 has connected and validated the Docker/WSL integration layer:

- Ansible inventory now targets the Docker topology.
- Firewall rule objects include management, frontend, backend, peer, VIP, and backend server networks.
- Keepalived data is now cluster-scoped through `keepalived_cluster`.
- conntrackd peer IPs are stored per firewall host in inventory.
- Docker Compose config validates syntactically.
- pytest test scaffolding and report helpers are present.
- CI has basic Python syntax and Compose config checks.
- The full Ansible site playbook deploys to `fw1`, `fw2`, and `fw3`.
- The integration test playbook passes with `79 passed`, `0 failed`, and `11 skipped`.
- Keepalived failover, conntrackd runtime checks, nftables ruleset checks, and report generation are covered by pytest.

## Still Needed

Member 1 and Member 5 should finish:

- final review of nftables rule policy for allowed and blocked flows
- anti-spoofing rules if they are required by the final rubric
- final review of VRRP and conntrackd behavior before merge
- optional VM/physical-host proof if required by the professor

Member 2 and Member 5 should finish:

- keep Docker image build validation reproducible
- keep `docker compose up` runtime validation documented
- review whether client routing/gateway setup needs to become more realistic for the final demo
- preserve the passing pytest execution against the live topology

Member 3 and Member 5 should finish:

- final CI/CD pipeline stages
- image build/push flow
- Kubernetes or Helm deployment validation if still required by the final scope

Member 4 and Member 5 should finish:

- monitoring role or playbook integration if the dashboard must be deployed automatically
- rsyslog/log parser deployment
- tcpdump capture rotation
- validation that allowed and blocked traffic appears in logs and reports
- optional Telegram alert setup using environment variables, not committed secrets

## Imported After Main Baseline

After the green `main` baseline was uploaded, new teammate updates were fetched again. They were not raw-merged because the branches still replaced the working role structure with prototype files. The following safe pieces were integrated selectively:

- optional Helm chart under `helm/firewall-chart/`
- optional static Kubernetes manifests under `k8s/`
- Kubernetes check helpers under `scripts/check_*.py`
- sanitized monitoring dashboard and metrics scripts under `monitoring/`
- Makefile targets for optional Kubernetes and monitoring workflows

The Docker/Ansible path remains the canonical tested deployment path.

## Validation Commands

Run from WSL or Linux:

```bash
bash run_wsl_checks.sh
cd ansible/roles/firewall
molecule test
```

When Docker Desktop or Linux Docker is available:

```bash
docker compose config --quiet
docker compose build
docker compose up -d
ansible-playbook ansible/playbooks/site.yml
ansible-playbook ansible/playbooks/run_tests.yml
```

Latest recorded result:

```text
79 passed, 0 failed, 11 skipped, 90 total
pytest exit: 0
```

## Integration Principle

Do not adapt the Ansible architecture around outdated prototype files. Instead, adapt teammate contributions into the shared inventory, role, template, and test structure when that produces a cleaner final project.
