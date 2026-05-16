# Requirements Validation Matrix

This document is the shared quality contract for Topic 5.2. It maps each project requirement to an owner, implementation location, validation command, expected result, and current status.

| Requirement | Owner | Implementation | Validation Command | Expected Result | Status |
|---|---|---|---|---|---|
| Three firewall nodes exist in inventory | Member 5 + Member 2 | `ansible/inventory/hosts.yml` | From `ansible/`: `ansible-inventory --graph` | `fw1`, `fw2`, and `fw3` are in group `firewalls` | Partial |
| Hostname entries include static IPv4 and IPv6 | Member 5 | `ansible/inventory/hosts.yml` | From `ansible/`: `ansible-playbook playbooks/site.yml --syntax-check` plus `inventory_validate` | Every firewall has `ipv4_addr`, `ipv6_addr`, and `keepalived_priority` | Partial |
| Ansible is the canonical rollout mechanism | Member 5 | `ansible/ansible.cfg`, `ansible/playbooks/site.yml`, roles | From `ansible/`: `ansible-playbook playbooks/site.yml --syntax-check` | Playbook loads inventory and roles without syntax errors | Partial |
| nftables supports IPv4 and IPv6 | Member 1 + Member 5 | `ansible/roles/firewall/templates/nftables.conf.j2` | `nft -c -f /etc/nftables.conf` on Debian firewall node | Ruleset validates for table `inet` and contains IPv4/IPv6 object sets | Partial |
| Custom Ansible module applies nftables rules | Member 1 + Member 5 | `ansible/library/nftables_apply.py` | Run firewall role on Debian node | Module validates with `nft -c` before applying with `nft -f` | Partial |
| Inventory validation fails early | Member 5 | `ansible/library/inventory_validate.py` | Run `ansible/playbooks/site.yml` with invalid inventory | Playbook fails before configuring nodes | Partial |
| Keepalived failover for cluster IP | Member 1 + Member 5 | `ansible/roles/keepalived` | Stop active firewall node | VIP moves to next highest-priority node | Missing real failover test |
| Conntrack state synchronization | Member 1 + Member 5 | `ansible/roles/conntrackd` | Compare conntrack state before and after failover | Existing TCP sessions continue or recover cleanly | Missing real traffic test |
| Docker Compose test topology | Member 2 | `docker-compose.yml`, `DockerFile` | `docker compose config` | Compose defines 3 firewalls and 2-3 test networks with clients | Missing |
| Automated QA traffic tests | Member 2 | `tests/` | `pytest` | Allowed traffic passes and blocked traffic fails | Missing |
| CI/CD pipeline | Member 3 | `.gitlab-ci.yml` or Gitea Actions workflow | Pipeline run | Build, test, and deploy stages execute | Missing |
| Kubernetes/Helm deployment | Member 3 | `kubernetes/` or `charts/` | `helm lint` and `helm template` | Chart renders valid Kubernetes manifests | Missing |
| Monitoring and diagnostics | Member 4 | `monitoring/`, rsyslog, tcpdump, dashboard | Generate allowed and blocked packets | Logs, captures, and dashboard reflect traffic and failover | Prototype |
| Diagnostic packages installed on firewall nodes | Member 4 + Member 5 | `ansible/group_vars/firewalls.yml`, `common` role | Run common role on Debian node | `tcpdump`, `iftop`, and `cbm` are installed | Partial |
| Debian 13 portability outside Docker | Member 5 + all | Ansible roles only, no Docker-specific commands | Run playbook against Debian 13 VM | Playbook completes without Docker assumptions | Partial |
| Molecule role test | Member 5 | `ansible/roles/firewall/molecule/default` | From `ansible/roles/firewall/`: `molecule test` | Docker lifecycle creates Debian 13 container, role converges, and `/etc/nftables.conf` renders mock IPv4/IPv6 rules | Partial; lifecycle fixed, real nftables apply still requires privileged integration test |

## Current Known Gaps

- `docker-compose.yml`, `DockerFile`, and `.gitlab-ci.yml` are still empty.
- Real nftables, Keepalived, and conntrackd behavior must be validated on Linux, not native Windows.
- The Keepalived password currently has a lab default and should be replaced with Ansible Vault before final submission.
- Molecule requires Linux because it depends on modules unavailable on native Windows.
- Use `bash run_wsl_checks.sh` from the repository root for inventory, syntax, and lint checks. The script sets `PYTHONNOUSERSITE=1` to reduce duplicate collection warnings from overlapping global and virtualenv Ansible paths.
