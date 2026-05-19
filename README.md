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

The project has a working Member 5 Stage 1 foundation. This means the Ansible integration layer can be checked independently before the rest of the team finishes Docker Compose, real traffic testing, monitoring, CI/CD, and Kubernetes work.

The full project is not finished yet. The main missing areas are still real Docker Compose infrastructure, real failover tests, real conntrackd synchronization tests, full monitoring integration, and CI/CD/Kubernetes assets.

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

### Verified

- Inventory graph shows `fw1`, `fw2`, and `fw3`.
- `ansible/playbooks/site.yml` passes syntax check.
- `ansible-lint` passes with zero failures and zero warnings.
- Firewall role Molecule scenario passes on a Debian 13 Docker container.
- Molecule idempotence check passes.
- Molecule verifies rendered mock IPv4 and IPv6 nftables rules.

### Still Needed

- Add Ansible Vault for real secrets, especially Keepalived authentication data.
- Add or finalize a dynamic inventory plugin if the final scope requires Docker/Kubernetes/physical inventory discovery.
- Run the full playbook against Member 2's final Docker Compose topology.
- Run the full playbook against a Debian 13 VM or real host to prove portability.
- Integrate final nftables rules from Member 1.
- Validate real nftables apply behavior on privileged Linux targets.
- Validate Keepalived VIP failover with three firewall nodes.
- Validate conntrackd connection state synchronization during failover.
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
| 7 | Documentation and requirement mapping | Partial |
| 8 | Final integration with other members' parts | Pending |


Stage 1 is complete. Stage 2 begins when the remaining team components are available for integration testing.

## Project Structure

Current repository structure:

```text
.
|-- README.md
|-- DockerFile
|-- docker-compose.yml
|-- nftables.conf
|-- render.py
|-- run_wsl_checks.sh
|-- vars.yml
|-- docs/
|   |-- member-5-status.md
|   `-- requirements-validation.md
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
    |   `-- site.yml
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

## Known Current Gaps

- `docker-compose.yml` and `DockerFile` still need the final Member 2 implementation.
- `.gitlab-ci.yml` or the chosen CI workflow still needs the final Member 3 implementation.
- Kubernetes or Helm deployment files still need the final Member 3 implementation.
- Monitoring scripts exist, but the final Member 4 dashboard, log flow, alerting, and packet capture integration are not complete.
- Real nftables application, Keepalived failover, and conntrackd synchronization still require privileged Linux integration tests.
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
