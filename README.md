# Scalable High-Availability Firewall

Cloud Computing group project, Topic 5.2: Scalable Firewall with Debian 13 and nftables.

## Project Goal

The final project should provide a flexible, high-availability firewall platform that can be deployed in Docker containers, virtual machines, LXC/OCI containers, or on real physical Debian hosts.

The firewall cluster must consist of three firewall nodes. One node owns the virtual cluster IP at a time, and the other two nodes are standby nodes. If the active node fails, Keepalived must move the virtual IP to another firewall node automatically. To reduce broken TCP sessions during failover, conntrackd should synchronize connection tracking state between the firewall nodes.

Ansible is the central rollout mechanism. The same Ansible roles should configure the firewall in the test environment and on real Debian 13 systems without Docker-specific commands inside the roles.

## Final Target Architecture

In the final version, the project should include:

- Three Debian 13 firewall nodes: `fw1`, `fw2`, and `fw3`.
- nftables firewall rules for both IPv4 and IPv6.
- Static hostname, IPv4, and IPv6 data stored in Ansible inventory.
- Docker lab targets use Ansible's Docker connection plugin; VM or physical targets should use a separate SSH-based inventory.
- Keepalived VRRP failover with a shared cluster IP.
- conntrackd connection state synchronization between firewall nodes.
- Docker Compose test infrastructure with two or three isolated networks and test clients.
- Diagnostic packages on firewall nodes, including `tcpdump`, `iftop`, and `cbm`.
- Automated traffic tests for allowed and blocked packets.
- Monitoring, logging, and diagnostic scripts.
- CI/CD pipeline for building, testing, and deploying the solution.
- Optional Kubernetes or Helm deployment path for cloud-native testing.

## Design Rules

- Debian 13 is the target operating system.
- nftables is the firewall backend.
- Ansible is the source of truth for system configuration and firewall deployment.
- Firewall rules should be configurable through inventory and variables.
- Hostname-based configuration must use static inventory data, not runtime DNS lookups.
- IPv4 and IPv6 rules must be generated together.
- Roles must stay portable to containers, VMs, and physical machines.
- Docker Compose is used for the lab and testing environment, not as a hard dependency inside Ansible roles.

## Team Responsibilities

| Member | Area | Main Responsibilities | Final Validation |
|---|---|---|---|
| Member 1 | Firewall Core and High Availability | Implement nftables rules, Keepalived VRRP, conntrackd synchronization, and failover behavior. Integrate or support custom firewall apply logic. | `nft -c -f`, failover tests, conntrack state comparison before and after failover. |
| Member 2 | Test Environment and Automated QA | Build Docker Compose topology with three firewall nodes and test clients across isolated networks. Create pytest and Scapy traffic tests. | `docker compose config`, `docker compose up`, `pytest`, allowed/blocked traffic validation. |
| Member 3 | CI/CD and Kubernetes Orchestration | Build CI/CD pipeline, local Kubernetes setup, OCI image flow, and Helm/Kubernetes deployment assets. | Pipeline run, image build, Helm lint/template, kind or minikube deployment. |
| Member 4 | Monitoring, Logging, and Diagnostics | Configure rsyslog, nftables log parsing, tcpdump rotation, conntrack analysis, dashboard, and alerts. | Generated test traffic appears correctly in logs, captures, dashboard, and alerts. |
| Member 5 | Ansible Orchestration and Integration | Build the Ansible structure, inventory contract, roles, templates, custom validation/apply modules, Molecule tests, and requirement validation documentation. | `bash run_wsl_checks.sh`, `molecule test`, inventory validation, syntax checks, ansible-lint. |

## Current Project Status

The project has moved beyond the isolated Member 5 Stage 1 foundation. The Ansible integration layer now uses the Docker test topology from teammate updates as its target environment.

The core Docker/WSL integration path is now passing. Ansible deploys the three firewall nodes in the Docker Compose topology, and the integration test playbook validates nftables rules, Keepalived failover, conntrackd behavior, IPv6 rule rendering, and report generation.

The full project still needs final cross-member polish: monitoring integration, CI/CD/Kubernetes completion, secrets handling with Ansible Vault, and optional VM or physical-host validation if required by the professor.

## Member 5 Work: Done And Pending

### Done

- Added repository hygiene through `.gitignore`.
- Made `ansible/inventory/hosts.yml` the canonical inventory.
- Updated `ansible/ansible.cfg` to use the YAML inventory.
- Added `remote_tmp = /tmp/ansible` to avoid Ansible temporary directory issues.
- Defined three firewall nodes: `fw1`, `fw2`, and `fw3`.
- Stored static IPv4, IPv6, and Keepalived priority data in inventory.
- Added shared variables in `ansible/group_vars/all.yml`.
- Added firewall-specific variables in `ansible/group_vars/firewalls.yml`.
- Created the main playbook at `ansible/playbooks/site.yml`.
- Implemented the `common` role for base and diagnostic packages.
- Implemented the `firewall` role for nftables template rendering.
- Implemented the `keepalived` role structure and template.
- Implemented the `conntrackd` role structure and template.
- Moved nftables templates into the firewall role.
- Added `inventory_validate.py` custom Ansible module.
- Added `nftables_apply.py` custom Ansible module.
- Added safe role switches for Molecule: validation, apply, and service management can be disabled.
- Fixed the Molecule Docker lifecycle for the firewall role.
- Added Molecule test variables for IPv4 and IPv6 rule rendering.
- Added `run_wsl_checks.sh` for repeatable WSL validation.
- Added `.ansible-lint` and cleaned lint issues.
- Added `ansible/requirements.yml` and Molecule collection requirements.
- Added `docs/requirements-validation.md`.
- Added `docs/member-5-status.md`.
- Added `docs/team-integration-notes.md`.
- Imported Docker Compose infrastructure for `fw1`, `fw2`, `fw3`, test clients, backend servers, and a test runner.
- Updated Ansible inventory to match the Docker network topology.
- Moved VRRP settings into a cluster-scoped `keepalived_cluster` structure.
- Added pytest-based integration tests and report helper scripts.
- Added a basic CI validation pipeline.

### Verified

- Inventory graph shows `fw1`, `fw2`, and `fw3`.
- `ansible/playbooks/site.yml` passes syntax check.
- `ansible-lint` passes with zero failures and zero warnings.
- Firewall role Molecule scenario passes on a Debian 13 Docker container.
- Molecule idempotence check passes.
- Molecule verifies rendered mock IPv4 and IPv6 nftables rules.
- Docker Compose builds the firewall and client images.
- Docker Compose starts the three firewall containers, three clients, and two backend servers.
- The rendered nftables ruleset passes `nft -c` syntax validation inside `fw1`.
- `ansible/playbooks/site.yml` deploys common packages, nftables, Keepalived, and conntrackd to `fw1`, `fw2`, and `fw3`.
- Keepalived runs on all three firewall nodes and moves the VIP during failover tests.
- conntrackd runtime checks pass after stale Docker lock/socket recovery was added to the test setup.
- `ansible/playbooks/run_tests.yml` passes with `79 passed`, `0 failed`, and `11 skipped`.
- Optional Helm/Kubernetes support files have been imported under `helm/` and `k8s/`.
- Sanitized monitoring dashboard and metric scripts have been imported under `monitoring/`.

### Still Needed

- Add Ansible Vault for real secrets, especially Keepalived authentication data.
- Add or finalize a dynamic inventory plugin if the final scope requires Docker/Kubernetes/physical inventory discovery.
- Run the full playbook against a Debian 13 VM or real host to prove portability.
- Final-review nftables rules from Member 1.
- Validate optional Helm/Kubernetes deployment if it remains in the final scope.
- Validate the final monitoring dashboard, metrics, logs, and alerts with Member 4.
- Update the requirement matrix after every teammate's final implementation is merged.
- Prepare final commit, push, and merge workflow with the team.

## Member 5 Step Progress

| Step | Description | Status |
|---|---|---|
| 1 | Repository hygiene | Done |
| 2 | Canonical inventory design | Done |
| 3 | Ansible role structure | Done |
| 4 | nftables role integration | Done |
| 5 | Custom validation and apply modules | Done |
| 6 | Local quality validation | Done |
| 7 | Documentation and requirement mapping | Done |
| 8 | Final integration with other members' parts | Done for Docker/WSL lab |


Stage 1 is complete. Stage 2 core integration is complete for the Docker/WSL lab: the Docker topology, pytest tests, report helpers, Ansible deployment, Keepalived failover checks, and conntrackd checks are connected and passing.

## Project Structure

Current repository structure:

```text
.
|-- README.md
|-- docker-compose.yml
|-- Makefile
|-- pytest.ini
|-- requirements.txt
|-- nftables.conf
|-- render.py
|-- run_wsl_checks.sh
|-- vars.yml
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
|-- docs/
|   |-- member-5-status.md
|   |-- requirements-validation.md
|   `-- team-integration-notes.md
|-- monitoring/
|   `-- analyzers/
|       |-- conntrack_analyzer.py
|       `-- log_analyzer.py
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
    |-- playbooks/
    |   |-- site.yml
    |   `-- run_tests.yml
    `-- roles/
        |-- common/
        |-- firewall/
        |-- keepalived/
        `-- conntrackd/
```

Member 5 Ansible structure in more detail:

```text
ansible/
|-- ansible.cfg
|-- requirements.yml
|-- inventory/
|   |-- hosts.yml
|   `-- hosts.ini
|-- group_vars/
|   |-- all.yml
|   `-- firewalls.yml
|-- library/
|   |-- inventory_validate.py
|   `-- nftables_apply.py
|-- playbooks/
|   `-- site.yml
`-- roles/
    |-- common/
    |   |-- defaults/main.yml
    |   |-- handlers/main.yml
    |   `-- tasks/main.yml
    |-- firewall/
    |   |-- defaults/main.yml
    |   |-- handlers/main.yml
    |   |-- tasks/main.yml
    |   |-- templates/
    |   |   |-- nftables.conf.j2
    |   |   |-- nftables_ipv4.j2
    |   |   `-- nftables_ipv6.j2
    |   `-- molecule/default/
    |       |-- cleanup.yml
    |       |-- collections.yml
    |       |-- converge.yml
    |       |-- create.yml
    |       |-- destroy.yml
    |       |-- molecule.yml
    |       |-- prepare.yml
    |       |-- requirements.yml
    |       `-- verify.yml
    |-- keepalived/
    |   |-- defaults/main.yml
    |   |-- handlers/main.yml
    |   |-- tasks/main.yml
    |   `-- templates/keepalived.conf.j2
    `-- conntrackd/
        |-- defaults/main.yml
        |-- handlers/main.yml
        |-- tasks/main.yml
        `-- templates/conntrackd.conf.j2
```

## Current Validation Commands

Run from WSL or another Linux environment. Native Windows is not reliable for Ansible and Molecule in this project.

From the repository root:

```bash
bash run_wsl_checks.sh
```

The script prefers the project `.venv_linux` environment when it exists. If Ansible is missing in WSL, recreate or activate the environment first:

```bash
python3 -m venv .venv_linux
source .venv_linux/bin/activate
python -m pip install -r requirements.txt molecule molecule-plugins[docker] ansible-lint
ansible-galaxy collection install -r ansible/requirements.yml
```

Expected result:

- Inventory graph contains `fw1`, `fw2`, and `fw3`.
- Playbook syntax check passes.
- ansible-lint passes with zero failures.

From the firewall role directory:

```bash
cd ansible/roles/firewall
molecule test
```

Expected result:

- A Debian 13 Docker container named `instance` is created.
- The firewall role converges.
- `/etc/nftables.conf` is rendered.
- Mock IPv4 and IPv6 rules are verified.
- Idempotence passes.
- The container is destroyed.

If Molecule reports that it cannot contact the Docker daemon, start Docker Desktop on Windows and enable WSL integration for the Linux distribution, then verify from WSL:

```bash
docker version
docker ps
```

## Known Current Gaps

- Docker Compose infrastructure builds and starts, and Ansible deployment, failover, and integration tests pass in WSL/Docker.
- `.gitlab-ci.yml` currently contains basic validation jobs only; Member 3 may still extend it.
- Kubernetes or Helm support files now exist, but runtime proof still depends on the final Member 3 scope.
- Monitoring scripts, dashboard, and Ansible NFLOG drop rules exist, but the final Member 4 log flow, alerting, and packet capture proof is not complete.
- Real nftables application, Keepalived failover, and conntrackd synchronization have passed privileged Docker integration tests.
- The current Molecule test validates role rendering and idempotence, not full kernel-level firewall behavior.

## Final Acceptance Criteria

The project can be considered complete when:

- Ansible deploys all firewall nodes successfully.
- All three firewall nodes are configured from the same inventory contract.
- nftables rules are generated for both IPv4 and IPv6.
- `nft -c -f` validates the rendered ruleset.
- Keepalived failover moves the cluster IP automatically.
- conntrackd synchronizes connection state between firewall nodes.
- Docker Compose provides realistic test networks and clients.
- Automated traffic tests prove allowed and blocked flows.
- Monitoring and logging show firewall activity and failover events.
- CI/CD runs linting, syntax checks, tests, and deployment steps.
- Documentation clearly maps every requirement to implementation and validation evidence.
