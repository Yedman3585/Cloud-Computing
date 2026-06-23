# Scalable High-Availability Firewall

Cloud Computing group project, Topic 5.2: Scalable Firewall with Debian 13 and nftables.

## Project Goal

This project implements a high-availability firewall lab that can run in Docker containers and can be adapted for virtual machines, LXC/OCI containers, or physical Debian hosts.

The firewall cluster must consist of three firewall nodes. One node owns the virtual cluster IP at a time, and the other two nodes are standby nodes. If the active node fails, Keepalived must move the virtual IP to another firewall node automatically. To reduce broken TCP sessions during failover, conntrackd should synchronize connection tracking state between the firewall nodes.

Ansible is the main deployment tool. The same Ansible roles should configure the firewall in the test environment and on real Debian 13 systems without Docker-specific commands inside the roles.

## Target Architecture

The project includes:

- Three Debian 13 firewall nodes: `fw1`, `fw2`, and `fw3`.
- nftables firewall rules for both IPv4 and IPv6.
- Static hostname, IPv4, and IPv6 data stored in Ansible inventory.
- Docker lab targets use Ansible's Docker connection plugin; VM or physical targets should use a separate SSH-based inventory.
- Keepalived VRRP failover with one active firewall owning the management, frontend, and backend cluster VIPs.
- conntrackd connection state synchronization between firewall nodes.
- Docker Compose test infrastructure with two or three isolated networks and test clients.
- Diagnostic packages on firewall nodes, including `tcpdump`, `iftop`, and `cbm`.
- Automated traffic tests for allowed and blocked packets.
- Monitoring, logging, and diagnostic scripts.
- CI/CD validation for syntax and configuration checks where a compatible runner is available.
- Optional Kubernetes, Helm, or Gitea workflow material for extra deployment examples.

## Design Rules

- Debian 13 is the target operating system.
- nftables is the firewall backend.
- Ansible is where the system configuration and firewall deployment are defined.
- Firewall rules should be configurable through inventory and variables.
- Hostname-based configuration must use static inventory data, not runtime DNS lookups.
- IPv4 and IPv6 rules must be generated together.
- Roles must stay portable to containers, VMs, and physical machines.
- Docker Compose is used for the lab and testing environment, not as a hard dependency inside Ansible roles.

## Team Responsibilities

| Member | Name | Area | Main Responsibilities | Final Validation |
|---|---|---|---|---|
| Member 1 | Iliyas | Firewall Core and High Availability | Define the firewall behavior: nftables rules, Keepalived VRRP failover, conntrackd synchronization, and firewall runtime behavior during node failure. | `nft -c -f`, failover tests, conntrack state comparison before and after failover. |
| Member 2 | Said | Test Environment and Automated QA | Build the Docker Compose lab with firewall nodes, test clients, backend servers, isolated networks, and pytest/traffic tests for allowed and blocked flows. | `docker compose config`, `docker compose up`, `pytest`, allowed/blocked traffic validation. |
| Member 3 | Shahzod | CI/CD and Kubernetes Orchestration | Provide CI/CD validation, image build flow, and optional Kubernetes/Helm deployment files. | GitLab/Gitea pipeline checks, Docker image build, Helm lint/template, optional kind or minikube deployment. |
| Member 4 | Aisana | Monitoring, Logging, and Diagnostics | Add logging, metrics, packet capture, conntrack analysis, dashboard material, and optional alerting around firewall activity. | Generated test traffic appears correctly in logs, captures, dashboard, metrics, and alerts. |
| Member 5 | Yedige Mussabayev | Ansible Orchestration and Integration | Build and maintain the Ansible control layer: inventory structure, group variables, roles, templates, custom validation/apply modules, deployment playbooks, WSL validation script, integration documentation, and connection between the member parts. This part is broad because Ansible connects the firewall behavior, Docker topology, HA configuration, tests, and validation results. | `bash run_wsl_checks.sh`, `ansible-playbook ansible/playbooks/site.yml`, `ansible-playbook ansible/playbooks/run_tests.yml`, inventory validation, syntax checks, ansible-lint, Molecule role checks where applicable. |

The member parts are connected through the Ansible/Docker run path:

- Member 1's firewall and HA behavior is rendered and deployed by Ansible.
- Member 2's Docker topology is the live environment for deployment and tests.
- Member 3's CI/CD and Kubernetes material validates or demonstrates the project outside the local run path.
- Member 4's monitoring components observe the deployed firewall behavior.
- Member 5's Ansible layer turns the shared inventory into repeatable configuration across `fw1`, `fw2`, `fw3`, clients, and backend servers.

## Current Project Status

The project now uses the Docker test topology from teammate updates as the Ansible deployment environment.

The core Docker/WSL integration path is now passing. Ansible deploys the three firewall nodes in the Docker Compose topology, and the integration test playbook validates nftables rules, Keepalived failover, conntrackd behavior, IPv6 rule rendering, and report generation.

The Docker/Ansible firewall path is connected and passing. Kubernetes, Helm, GitLab runner execution, Gitea runner execution, Ansible Vault, and VM or physical-host validation remain optional extensions unless the professor explicitly asks for them.

## Member 5 Work: Ansible Integration

Member 5 is responsible for more than a single role. The Ansible part is the main integration layer of the project. It defines the inventory structure, renders firewall and HA configuration, applies services to the running firewall nodes, configures routes for the test topology, and provides repeatable validation commands.

The Ansible layer is split into these main parts:

- `ansible/inventory/hosts.yml`: main inventory for the Docker lab, including firewall nodes, backend servers, clients, and static network data.
- `ansible/inventory/hosts.ini`: fallback inventory for simple Ansible commands and professor/demo readability.
- `ansible/group_vars/all.yml`: shared firewall objects, network objects, VIPs, allowed services, and rule references.
- `ansible/group_vars/firewalls.yml`: firewall-cluster settings such as priorities, peer data, Keepalived instances, and conntrackd sync addresses.
- `ansible/playbooks/site.yml`: main deployment playbook. It validates inventory, configures firewalls, and configures client/server routing through the firewall VIPs.
- `ansible/playbooks/run_tests.yml`: post-deployment integration test runner. It waits for healthy firewalls, starts monitoring, runs pytest, stores logs, and generates reports.
- `ansible/roles/common`: installs base packages, diagnostics, and detects the correct Docker network interfaces.
- `ansible/roles/firewall`: renders and applies the nftables ruleset.
- `ansible/roles/keepalived`: renders and manages VRRP configuration for management, frontend, and backend VIP failover.
- `ansible/roles/conntrackd`: renders and manages connection-state synchronization.
- `ansible/roles/routing`: configures frontend/backend routes so test traffic actually crosses the firewall cluster.
- `ansible/library/inventory_validate.py`: fails early when inventory objects or firewall rule references are inconsistent.
- `ansible/library/nftables_apply.py`: validates nftables syntax before applying firewall rules.
- `run_wsl_checks.sh`: repeatable WSL validation wrapper for inventory graph, syntax check, and ansible-lint.

## Member 5 Work: Done And Pending

### Done

- Added repository hygiene through `.gitignore`.
- Made `ansible/inventory/hosts.yml` the main inventory.
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
- Added an expanded CI validation pipeline for Python syntax, Ansible syntax, Compose config, Kubernetes YAML, Helm template, and monitoring syntax.

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
- Keepalived runs on all three firewall nodes and keeps the management, frontend, and backend VIPs on exactly one active firewall.
- Added routing through the frontend/backend VIPs so client-to-server traffic crosses the firewall cluster.
- Added port-isolation validation: `server2` serves ports `80` and `8080` locally, but only port `80` is reachable through the firewall.
- conntrackd runtime checks pass after stale Docker lock/socket recovery was added to the test setup.
- `ansible/playbooks/run_tests.yml` passes with `86 passed`, `0 failed`, and `11 skipped`.
- Optional Helm/Kubernetes support files have been imported under `helm/` and `k8s/`.
- Sanitized monitoring dashboard and metric scripts have been imported under `monitoring/`.

### Still Needed

- Add Ansible Vault for real secrets before using production credentials.
- Run the full playbook against a Debian 13 VM or real host if portability validation is required.
- Validate optional Helm/Kubernetes/Gitea deployment only if it remains in the course scope.
- Validate the final monitoring dashboard, metrics, logs, and alerts with Member 4 if dashboard validation is required.
- Update the requirement matrix after every teammate's final implementation is merged.
- Prepare final commit, push, and merge workflow with the team.

## Member 5 Step Progress

| Step | Description | Status |
|---|---|---|
| 1 | Repository hygiene | Done |
| 2 | Main inventory design | Done |
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
|       |-- server2.html
|       `-- server2-multiport.conf
|-- tests/
|   |-- conftest.py
|   |-- test_conntrackd.py
|   |-- test_failover.py
|   |-- test_ipv6.py
|   |-- test_nftables_rules.py
|   |-- test_port_isolation.py
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
        |-- conntrackd/
        `-- routing/
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
    |-- conntrackd/
    |   |-- defaults/main.yml
    |   |-- handlers/main.yml
    |   |-- tasks/main.yml
    |   `-- templates/conntrackd.conf.j2
    `-- routing/
        |-- defaults/main.yml
        `-- tasks/main.yml
```

## Current Validation Commands

Run from WSL or another Linux environment. Native Windows is not reliable for Ansible and Molecule in this project.

From the repository root:

```bash
bash run_wsl_checks.sh
```

The script prefers the active `VIRTUAL_ENV`; if no environment is active, it uses the project `.venv_linux` environment when it exists. If Ansible is missing in WSL, deactivate any virtualenv from another project, then recreate or activate this project's environment:

```bash
python3 -m venv .venv_linux
source .venv_linux/bin/activate
python -m pip install -r requirements.txt molecule molecule-plugins[docker]
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
- `.gitlab-ci.yml` contains expanded validation jobs, but GitLab runner eligibility/tag settings are an environment issue if jobs appear stuck without traces.
- Kubernetes, Helm, and Gitea workflow files are optional extensions; the professor's core Topic 5.2 path is Docker Compose plus Ansible plus nftables/HA tests.
- Monitoring scripts, dashboard, and Ansible NFLOG drop rules exist; final dashboard/log/alert validation is optional unless required for the demo.
- Real nftables application, Keepalived failover, and conntrackd synchronization have passed privileged Docker integration tests.
- The current Molecule test validates role rendering and idempotence, not full kernel-level firewall behavior.

## Acceptance Criteria

The project can be considered complete when:

- Ansible deploys all firewall nodes successfully.
- All three firewall nodes are configured from the same inventory structure.
- nftables rules are generated for both IPv4 and IPv6.
- `nft -c -f` validates the rendered ruleset.
- Keepalived failover moves the cluster IP automatically.
- conntrackd synchronizes connection state between firewall nodes.
- Docker Compose provides realistic test networks and clients.
- Automated traffic tests prove allowed and blocked flows.
- Monitoring and logging show firewall activity and failover events when the optional dashboard path is demonstrated.
- CI/CD validation runs where a compatible GitLab/Gitea runner is available.
- Documentation lists each requirement, implementation, and validation result.
