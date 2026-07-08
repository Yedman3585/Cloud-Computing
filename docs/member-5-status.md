# Member 5 Status Report: Ansible Orchestration and Integration

## Overview

Member 5 is responsible for the orchestration and integration layer of the scalable high-availability firewall project. This part connects the infrastructure, firewall rules, high-availability services, and validation workflow through Ansible.

This document describes Member 5 work across two phases:

- **Stage 1**: the independent Ansible foundation that can be completed without the final work of other members.
- **Stage 2**: integration with teammate updates, including Docker Compose topology, pytest tests, and runtime validation.

Current conclusion:

**Stage 1 is complete. Stage 2 core integration is complete in the Docker/WSL lab.**

The Ansible foundation is structured and tested. The teammate Docker topology, runtime deployment, Keepalived failover tests, conntrackd checks, nftables ruleset checks, and report generation are now connected and passing in the Docker/WSL lab.

## What Has Been Done

### Repository Hygiene

A `.gitignore` file was added to prevent local development artifacts from being committed.

Ignored examples:

- `.idea/`
- `.venv/`
- `.venv_linux/`
- `__pycache__/`
- generated nftables files
- logs
- packet captures

This keeps the project repository clean and avoids mixing local machine state with project code.

### Ansible Configuration

The main Ansible configuration is located at:

```text
ansible/ansible.cfg
```

Implemented:

- `hosts.yml` is used as the canonical inventory.
- Ansible role path is configured.
- Custom module path is configured.
- Module utils path is configured.
- Collections path is configured.
- SSH host key checking is disabled for the lab environment.
- `remote_tmp = /tmp/ansible` is configured to avoid temporary directory errors.
- Privilege escalation is configured with `become`.

### Inventory Contract

The main inventory is:

```text
ansible/inventory/hosts.yml
```

It defines the three required firewall nodes:

- `fw1`
- `fw2`
- `fw3`

Each firewall node has:

- hostname
- `ansible_host`
- static IPv4 address
- static IPv6 address
- Keepalived priority

This follows the professor's feedback: name-based firewall configuration should use static hostname, IPv4, and IPv6 data from the Ansible inventory instead of runtime DNS resolution.

The inventory has now been aligned with the Docker test topology:

- management network: `172.20.0.0/24`
- frontend network: `172.21.0.0/24`
- backend network: `172.22.0.0/24`
- cluster VIP: `172.20.0.100`

This lets the same Ansible roles use static host data in both the Docker lab and future Debian VM or physical-host deployments.

In the Docker lab, Ansible uses the `community.docker.docker` connection plugin because Docker bridge IPs are not always reachable directly from WSL. VM and physical deployments should use a separate SSH-based inventory while keeping the same roles.

### Ansible Role Structure

The following roles have been created or completed:

- `common`
- `firewall`
- `keepalived`
- `conntrackd`

The `common` role installs base packages and diagnostic tools.

The `firewall` role renders nftables rules from inventory/group variables.

The `keepalived` role renders VRRP configuration for failover.

The `conntrackd` role renders connection state synchronization configuration.

Keepalived cluster-level settings are stored in `keepalived_cluster` instead of being loose global variables.

### nftables Integration

The nftables templates were moved into the firewall role.

Main template:

```text
ansible/roles/firewall/templates/nftables.conf.j2
```

The template renders an `inet` nftables ruleset and supports both IPv4 and IPv6 rule generation through inventory-driven objects.

The firewall role supports safe testing through these variables:

- `firewall_nftables_validate_rules`
- `firewall_nftables_apply_rules`
- `firewall_nftables_manage_service`

This allows Molecule to test rendering and idempotence without applying real kernel firewall rules inside a simple test container.

### Custom Python Ansible Modules

Two custom modules were added:

```text
ansible/library/inventory_validate.py
ansible/library/nftables_apply.py
```

`inventory_validate.py` checks:

- exactly three firewall nodes exist
- required IPv4 and IPv6 fields exist
- Keepalived priorities are valid
- firewall rule references point to known objects
- ports and protocols are valid

`nftables_apply.py` is responsible for:

- checking that the rendered nftables file exists
- validating nftables syntax with `nft -c -f`
- applying rules with `nft -f` when enabled

### Molecule Testing

The Molecule scenario for the firewall role has been repaired and now passes.

The scenario:

- creates a real `debian:13` Docker container
- bootstraps Python and nftables packages
- runs the firewall role
- renders `/etc/nftables.conf`
- verifies mock IPv4 and IPv6 rules
- checks idempotence
- cleans up and destroys the container

Current successful result:

```text
Molecule executed 1 scenario (1 successful)
```

### WSL Validation Helper

A helper script was added:

```text
run_wsl_checks.sh
```

It runs:

- `ansible-inventory --graph`
- `ansible-playbook ansible/playbooks/site.yml --syntax-check`
- `ansible-lint ansible/`

Current successful result:

```text
Passed: 0 failure(s), 0 warning(s)
```

### Full Docker Integration Testing

The full Docker/WSL integration path now passes:

- Docker Compose builds and starts the firewall, client, and backend containers.
- `ansible/playbooks/site.yml` deploys common packages, nftables, Keepalived, and conntrackd to `fw1`, `fw2`, and `fw3`.
- Keepalived runs on all three firewalls.
- The IPv4 VIP `172.20.0.100` is assigned to the active firewall.
- conntrackd runs and recovers from stale Docker runtime lock files during restart tests.
- `ansible/playbooks/run_tests.yml` runs the pytest suite and generates HTML/JSON reports.

Current successful integration result:

```text
79 passed, 0 failed, 11 skipped, 90 total
pytest exit: 0
```

The skipped tests are IPv6 connectivity checks skipped because Docker IPv6 is not fully enabled in the local Docker Compose runtime. IPv6 rule rendering is still validated by nftables ruleset tests.

## Main Tools Used

### Ansible

Ansible is the main orchestration tool.

Used for:

- inventory management
- package installation
- configuration rendering
- firewall deployment
- Keepalived configuration
- conntrackd configuration

### Jinja2

Jinja2 is used for configuration templates.

Used for:

- nftables rules
- Keepalived configuration
- conntrackd configuration

### Python

Python is used for custom Ansible modules.

Used for:

- inventory validation
- firewall rule validation
- nftables apply logic

### nftables

nftables is the firewall backend for Topic 5.2.

Used for:

- IPv4 firewall rules
- IPv6 firewall rules
- `inet` table rule generation

### Keepalived

Keepalived is used for high availability.

Used for:

- VRRP failover
- virtual cluster IP movement between firewall nodes

### conntrackd

conntrackd is used for connection state synchronization.

Used for:

- synchronizing connection tracking state between firewall nodes
- reducing connection loss during failover

### Molecule

Molecule is used for Ansible role testing.

Used for:

- testing the firewall role in a clean Debian 13 container
- checking role idempotence
- verifying rendered IPv4 and IPv6 nftables rules

### Docker

Docker is used by Molecule and by the project integration lab.

Used for:

- running Debian 13 test instances
- validating role behavior without depending on a physical machine
- running the three-firewall topology with frontend clients and backend servers

### Docker Compose

Docker Compose defines the integration topology.

Used for:

- three privileged firewall containers: `fw1`, `fw2`, `fw3`
- frontend test clients
- backend web servers
- management, frontend, and backend networks
- optional test runner container

### Kubernetes and Helm

Kubernetes and Helm are optional deployment/demo tooling imported from teammate updates.

Used for:

- static Kubernetes manifests under `k8s/`
- Helm chart under `helm/firewall-chart/`
- rollout helper `k8s/rollout.sh`
- resource check helpers in `scripts/check_*.py`

These files do not replace the tested Ansible/Docker deployment path.

### pytest and Scapy

pytest is used for automated integration checks. Scapy is available for synthetic traffic generation.

Used for:

- firewall rule checks
- failover checks
- conntrackd checks
- IPv6 checks
- traffic generation during later integration testing

### ansible-lint

ansible-lint is used for quality checks.

Used for:

- validating Ansible best practices
- enforcing variable naming style
- checking YAML formatting
- keeping roles maintainable

## Project Structure For Member 5

The most important Member 5 files are shown below.

```text
.
|-- .ansible-lint
|-- .gitignore
|-- run_wsl_checks.sh
|-- docs/
|   |-- member-5-status.md
|   |-- requirements-validation.md
|   `-- team-integration-notes.md
|-- docker-compose.yml
|-- Makefile
|-- pytest.ini
|-- requirements.txt
|-- docker/
|   |-- DockerFile
|   |-- Dockerfile.client
|   |-- entrypoint.sh
|   |-- supervisord.conf
|   `-- nginx/
|       |-- server1.html
|       `-- server2.html
|-- tests/
|   |-- conftest.py
|   |-- test_conntrackd.py
|   |-- test_failover.py
|   |-- test_ipv6.py
|   |-- test_nftables_rules.py
|   `-- traffic_generator.py
|-- scripts/
|   |-- generate_report.py
|   `-- monitor_health.py
`-- ansible/
    |-- ansible.cfg
    |-- requirements.yml
    |-- group_vars/
    |   |-- all.yml
    |   `-- firewalls.yml
    |-- inventory/
    |   |-- hosts.ini
    |   `-- hosts.yml
    |-- library/
    |   |-- inventory_validate.py
    |   `-- nftables_apply.py
    |-- module_utils/
    |-- playbooks/
    |   |-- site.yml
    |   `-- run_tests.yml
    `-- roles/
        |-- common/
        |   |-- defaults/
        |   |   `-- main.yml
        |   |-- handlers/
        |   |   `-- main.yml
        |   `-- tasks/
        |       `-- main.yml
        |-- firewall/
        |   |-- collections.yml
        |   |-- requirements.yml
        |   |-- defaults/
        |   |   `-- main.yml
        |   |-- handlers/
        |   |   `-- main.yml
        |   |-- tasks/
        |   |   `-- main.yml
        |   |-- templates/
        |   |   |-- nftables.conf.j2
        |   |   |-- nftables_ipv4.j2
        |   |   `-- nftables_ipv6.j2
        |   `-- molecule/
        |       `-- default/
        |           |-- cleanup.yml
        |           |-- collections.yml
        |           |-- converge.yml
        |           |-- create.yml
        |           |-- destroy.yml
        |           |-- molecule.yml
        |           |-- prepare.yml
        |           |-- requirements.yml
        |           `-- verify.yml
        |-- keepalived/
        |   |-- defaults/
        |   |   `-- main.yml
        |   |-- handlers/
        |   |   `-- main.yml
        |   |-- tasks/
        |   |   `-- main.yml
        |   `-- templates/
        |       `-- keepalived.conf.j2
        `-- conntrackd/
            |-- defaults/
            |   `-- main.yml
            |-- handlers/
            |   `-- main.yml
            |-- tasks/
            |   `-- main.yml
            `-- templates/
                `-- conntrackd.conf.j2
```

## Member 5 Work Breakdown

Member 5 work can be divided into eight main steps.

### Step 1: Repository Hygiene

Status: Done

Implemented:

- `.gitignore`
- cleanup of local/editor artifact handling

### Step 2: Canonical Inventory Design

Status: Done

Implemented:

- `hosts.yml`
- three firewall nodes
- static hostname, IPv4, IPv6, and Keepalived priority data

### Step 3: Ansible Role Structure

Status: Done

Implemented roles:

- `common`
- `firewall`
- `keepalived`
- `conntrackd`

### Step 4: nftables Role Integration

Status: Done

Implemented:

- firewall role task flow
- nftables Jinja templates
- IPv4 and IPv6 object-based rendering
- safe test toggles for validation/apply/service management

### Step 5: Custom Validation and Apply Modules

Status: Done

Implemented:

- `inventory_validate.py`
- `nftables_apply.py`

### Step 6: Local Quality Validation

Status: Done

Verified:

- WSL inventory graph passes
- WSL playbook syntax check passes
- ansible-lint passes with zero failures and zero warnings
- Molecule firewall role test passes
- Docker Compose builds the firewall and client images
- Docker Compose starts the firewall, client, and backend server containers
- Rendered nftables syntax passes `nft -c` inside `fw1`

### Step 7: Documentation and Requirement Mapping

Status: Done

Implemented:

- `docs/requirements-validation.md`
- this Member 5 status report
- `docs/team-integration-notes.md`

The documents should still be reviewed again after the final team merge, but the Member 5 Docker/WSL runtime evidence is now recorded.

### Step 8: Final Integration Features

Status: Done for Member 5 Docker/WSL integration scope

Implemented:

- imported Docker Compose topology from teammate updates
- aligned Ansible inventory with Docker management, frontend, and backend networks
- moved VRRP values into the cluster-scoped `keepalived_cluster` variable
- connected pytest integration tests and report scripts
- added `ansible/playbooks/run_tests.yml`
- added basic CI validation jobs
- fixed Docker shell entrypoint line endings for Windows/WSL builds
- added `.gitattributes` to keep Linux-facing files LF-normalized
- deployed the full Ansible site playbook into the running Docker Compose topology
- verified Keepalived failover behavior through pytest
- verified conntrackd process, config, socket, stats, and sync-related checks through pytest
- verified nftables ruleset content, IPv4 management access, and IPv6 rule rendering through pytest
- generated HTML and JSON integration reports in `test_results/`
- selectively imported optional Kubernetes/Helm files from teammate updates
- selectively imported sanitized monitoring dashboard and metrics scripts

Still needed:

- Ansible Vault for secrets
- optional dynamic inventory plugin if required by the final grading scope
- final deployment proof against Debian 13 VM or physical hosts if required
- optional Kubernetes/Helm runtime proof if required by the final grading scope
- final monitoring dashboard/log/alert proof with Member 4
- final commit/push/merge workflow

## Progress Summary

Fully completed:

- Step 1
- Step 2
- Step 3
- Step 4
- Step 5
- Step 6
- Step 7
- Step 8

Current progress:

```text
8 / 8 major Member 5 steps complete for the Docker/WSL lab scope
```

## Current Conclusion

Stage 1 of Member 5 work is complete.

Stage 2 core integration is complete for the current Docker/WSL lab. The Ansible foundation now deploys into the Docker topology and the integration suite passes with `79 passed`, `0 failed`, and `11 skipped`.

The remaining work is mostly final project polish and cross-member integration:

- final nftables, Keepalived, and conntrackd behavior from Member 1
- CI/CD from Member 3
- monitoring and logging from Member 4
- optional VM/physical-host validation if required by the professor

Member 5's current work is stable enough to act as the integration base for the rest of the project, and the Docker/WSL runtime proof is now passing.
