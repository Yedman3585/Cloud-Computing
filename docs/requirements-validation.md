# Requirements Validation Matrix

This document is the shared quality contract for Topic 5.2. It maps each requirement to the current implementation path and the command that should prove it.

| Requirement | Owner | Implementation | Validation Command | Expected Result | Status |
|---|---|---|---|---|---|
| Three firewall nodes exist in inventory | Member 5 + Member 2 | `ansible/inventory/hosts.yml` | `ansible-inventory --graph` | `fw1`, `fw2`, `fw3` appear in `firewalls` | Integrated |
| Docker topology has 3 firewalls and test networks | Member 2 + Member 5 | `docker-compose.yml`, `docker/` | `docker compose up -d --build` | Firewall, client, and server containers start | Passed after entrypoint line-ending fix |
| Static hostname, IPv4, and IPv6 data | Member 5 | `ansible/inventory/hosts.yml` | `inventory_validate` via `site.yml` | Every firewall has static IPv4, IPv6, and priority data | Integrated |
| Docker Ansible connectivity | Member 5 + Member 2 | `ansible/inventory/hosts.yml` | `ansible-playbook ansible/playbooks/site.yml` | Ansible connects to `fw1`, `fw2`, `fw3` through Docker connection plugin | Passed |
| Ansible is canonical rollout mechanism | Member 5 | `ansible/playbooks/site.yml`, roles | `bash run_wsl_checks.sh` | Inventory graph, syntax check, and ansible-lint pass | Passed in WSL |
| nftables IPv4 and IPv6 rules | Member 1 + Member 5 | `ansible/roles/firewall/templates/nftables.conf.j2` | Render template, then `nft -c -f /tmp/rendered_fw1.nft` in `fw1` | `inet` ruleset contains IPv4/IPv6 sets and rules | Template syntax passed in Docker |
| Custom nftables apply module | Member 5 + Member 1 | `ansible/library/nftables_apply.py` | Run firewall role on Debian target | Module validates with `nft -c` before apply | Passed in Docker runtime |
| Inventory validation fails early | Member 5 | `ansible/library/inventory_validate.py` | Run `site.yml` with invalid data | Playbook fails before configuring nodes | Integrated |
| Keepalived failover | Member 1 + Member 5 | `ansible/roles/keepalived` | Stop `fw1` after deployment | VIP moves to `fw2`, then `fw3` on double failure | Passed in pytest integration suite |
| VRRP data is cluster-scoped | Member 5 | `keepalived_cluster` vars | Review inventory/group vars and template | Router ID/VIPs belong to `firewall_cluster_main`, not role defaults | Integrated |
| Docker HA interface mapping | Member 5 + Member 2 | `ansible/group_vars/firewalls.yml` | `ip -o -4 addr show` in `fw1`/`fw2`/`fw3` | Keepalived and conntrackd bind to management interface `eth2` | Integrated |
| conntrackd sync | Member 1 + Member 5 | `ansible/roles/conntrackd` | pytest conntrackd tests | Backup nodes receive connection tracking state | Passed in pytest integration suite |
| Automated QA tests | Member 2 + Member 5 | `tests/`, `pytest.ini`, `ansible/playbooks/run_tests.yml` | `pytest tests` or Ansible run-tests playbook | Rules, failover, conntrackd, IPv6 tests execute | Passed: 79 passed, 0 failed, 11 skipped |
| CI validation | Member 3 + Member 5 | `.gitlab-ci.yml` | Pipeline run | Python syntax and Compose config jobs pass | Basic validation added |
| Monitoring diagnostics | Member 4 | `monitoring/`, `scripts/monitor_health.py` | `make monitor` or run monitor script | Health snapshots show VIP owner and node health | Partial |
| Diagnostic packages installed | Member 4 + Member 5 | `common` role, `docker/DockerFile` | Run common role or inspect image | `tcpdump`, `iftop`, `cbm` available | Integrated |
| Debian 13 portability | Member 5 + all | Ansible roles without Docker-specific role logic | Run `site.yml` on Debian 13 VM/container | Playbook configures target | Passed in Debian Docker lab; VM/physical proof optional |
| Molecule role test | Member 5 | `ansible/roles/firewall/molecule/default` | `molecule test` from firewall role | Role renders nftables config idempotently | Passed in WSL with Docker |

## Current Known Gaps

- Docker is now reachable from the user's WSL environment, and Molecule passes there.
- `docker compose up -d --build` now builds the firewall/client images and starts the project containers.
- End-to-end Ansible deployment into the running Compose topology is recorded and passing.
- Native Windows Ansible still fails because of locale/path issues. Run Ansible checks from WSL or Linux.
- Docker IPv6 is still not fully enabled in Compose; Ansible renders IPv6 rules, but the Keepalived IPv6 VIP is disabled in Docker and IPv6 connectivity tests may skip.
- Real nftables apply, Keepalived failover, and conntrackd sync passed privileged Docker runtime validation.
- Monitoring dashboard/alerts from Aisana's branch still need cleanup before final integration, especially secrets and hardcoded paths.

## Recommended Validation Order

```bash
bash run_wsl_checks.sh
cd ansible/roles/firewall && molecule test
cd ../../..
docker compose config --quiet
docker compose up -d --build
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/site.yml
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/run_tests.yml
```

Latest recorded Docker/WSL integration result:

```text
79 passed, 0 failed, 11 skipped, 90 total
pytest exit: 0
```
