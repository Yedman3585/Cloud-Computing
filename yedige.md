# Individual Report - Member 5: Ansible Orchestration and Final Integration

**Name:** Yedige Mussabayev  
**GitLab:** @yedman3585  
**Main branch:** `yedige-ansible`
**Final project branch:** `main`
**Project:** Cloud Computing Group 05 - Topic 5.2: Scalable Firewall with Debian 13 and nftables  
**Date:** July 2026

---

## 1. My Responsibilities

As Member 5, my main responsibility was the Ansible orchestration and integration layer of the project. The project was developed by several members in parallel, so my work was not limited to writing isolated Ansible files. A major part of my contribution was connecting the Docker infrastructure, firewall rules, high availability roles, routing, automated tests, monitoring output, and final documentation into one repeatable project workflow.

My main responsibilities were:

- Build and maintain the Ansible project structure
- Configure Ansible to work with Docker Compose containers
- Maintain the inventory and group variable structure used by the deployment
- Connect the firewall, common, keepalived, conntrackd, and routing roles into one deployment playbook
- Implement and finalize the routing role so traffic passes through the firewall cluster
- Create the Ansible playbook that runs the integration test suite and report generation
- Run WSL/Linux Ansible syntax, lint, deployment, and integration-test checks
- Help integrate teammate work into the final repository state
- Document the final installation, test workflow, acceptance criteria, and verification evidence in README
- Document transparent AI usage and references to course material

---

## 2. What I Implemented

### 2.1 Ansible Configuration and Project Structure

I worked on the Ansible configuration so that the project can be executed from the repository root without relying on hidden local settings.

Important files:

| File | Purpose |
|---|---|
| `ansible/ansible.cfg` | Main Ansible configuration with inventory, roles path and library path |
| `ansible/requirements.yml` | Required Ansible collections, especially Docker-related modules |
| `.ansible-lint` | Lint configuration adjusted for the Docker/container lab environment |
| `run_wsl_checks.sh` | Helper script for inventory graph, syntax check and ansible-lint |
| `requirements.txt` | Python dependencies for Ansible, pytest, reports and monitoring |
| `Makefile` | Common commands for build, deploy, test, status and monitoring |

This part is important because the professor or another user should be able to clone the repository and run the same commands without manually guessing paths or Ansible settings.

Validation command:

```bash
bash run_wsl_checks.sh
```

Observed final output:

```text
=== Running Inventory Graph ===
@all:
  |--@firewalls:
  |  |--@firewall_cluster_main:
  |  |  |--fw1
  |  |  |--fw2
  |  |  |--fw3
  |--@backend_servers:
  |  |--server1
  |  |--server2
  |--@test_clients:
  |  |--client1
  |  |--client2
  |  |--client3
=== Running Syntax Check ===
playbook: ansible/playbooks/site.yml
=== Running Ansible Lint ===
Passed: 0 failure(s), 0 warning(s)
```

### 2.2 Inventory and Group Variable Integration

The project uses Ansible inventory and group variables to describe the desired infrastructure state. I helped align this structure with the final Docker Compose topology and with the needs of the firewall, HA, and routing roles.

Important files:

| File | Purpose |
|---|---|
| `ansible/inventory/hosts.yml` | YAML inventory for firewalls, backend servers and test clients |
| `ansible/inventory/hosts.ini` | Inventory compatibility file |
| `ansible/group_vars/all.yml` | Shared lab topology, firewall objects, VIPs and firewall rules |
| `ansible/group_vars/firewalls.yml` | Firewall-specific package, nftables, keepalived and conntrackd variables |
| `ansible/library/inventory_validate.py` | Custom module that validates the inventory contract before deployment |

The goal was to avoid a hardcoded firewall configuration. The firewall policy is defined in variables and rendered into nftables rules by Ansible templates. This follows the desired-state approach from the course Ansible material.

### 2.3 Main Deployment Playbook

I worked on the main Ansible deployment playbook.

File:

```text
ansible/playbooks/site.yml
```

The playbook has three logical parts:

1. Validate the firewall inventory contract
2. Configure firewall nodes with the common, firewall, keepalived and conntrackd roles
3. Configure routes on backend servers and test clients

Run command:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/site.yml -i ansible/inventory/hosts.yml
```

This playbook is the central deployment entry point. It makes the firewall lab repeatable: after Docker Compose starts the containers, Ansible applies the actual firewall and HA configuration.

Observed final result:

```text
PLAY RECAP
fw1     failed=0
fw2     failed=0
fw3     failed=0
server1 failed=0
server2 failed=0
client1 failed=0
client2 failed=0
client3 failed=0
```

### 2.4 Routing Role

I implemented and finalized the routing role.

Files:

```text
ansible/roles/routing/defaults/main.yml
ansible/roles/routing/tasks/main.yml
```

The routing role is necessary because the project is not only about starting containers. Client-to-backend traffic must pass through the firewall cluster. The role configures routes so frontend clients and backend servers use the firewall cluster VIPs instead of bypassing the firewall path.

The routing role was also adjusted for container compatibility. In particular, Alpine-based backend containers needed additional handling because they do not always provide the same tools as Debian-based containers.

### 2.5 Integration Test Orchestration Playbook

I created and finalized the Ansible playbook that runs the automated integration tests.

File:

```text
ansible/playbooks/run_tests.yml
```

The playbook performs the following steps:

1. Detect the correct Python interpreter from the virtual environment
2. Create the test results directory
3. Verify that pytest is available
4. Wait for firewall containers to become healthy
5. Start the health monitor in the background
6. Wait for Keepalived election to settle
7. Run pytest with JSON and HTML report output
8. Save stdout and stderr logs
9. Stop the background health monitor
10. Generate the final HTML laboratory report
11. Fail the playbook if pytest failed

Run command:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/run_tests.yml
```

Observed final result:

```text
pytest exit: 0
PLAY RECAP
localhost ok=11 changed=0 failed=0 skipped=2
```

### 2.6 Final Integration of Teammate Parts

A large part of my work was integration. The separate parts from different members had to become one runnable system.

I helped connect:

| Area | Integration work |
|---|---|
| Docker infrastructure | Connected Docker Compose service names, networks and IPs to Ansible inventory |
| Firewall rules | Connected group variable rule definitions to the nftables role and verification output |
| High availability | Connected Keepalived and conntrackd roles to the deployment playbook and tests |
| Routing | Ensured clients and backend servers use firewall VIP routes |
| Tests | Connected pytest tests with Ansible execution and generated reports |
| Monitoring | Connected health monitoring and report generation to the test workflow |
| Documentation | Added practical commands and evidence for the professor to verify the system quickly |

This was necessary because the final grade depends on the complete system working together, not only on separate files existing in the repository.

### 2.7 Final README and Verification Documentation

I worked on the final README and project documentation so that the project can be reviewed and installed by another person.

Important documentation files:

```text
README.md
docs/member-5-status.md
docs/requirements-validation.md
docs/team-integration-notes.md
docs/gitea-setup.md
docs/ci-runner-notes.md
```

Important topics documented in README:

- installation requirements
- Docker Compose startup
- Ansible deployment
- expected firewall evidence
- `nft list ruleset` inspection inside `fw1`
- Keepalived VIP ownership checks
- conntrackd synchronization checks
- pytest and Ansible test orchestration
- generated HTML report
- Gitea Actions notes
- acceptance criteria
- AI usage documentation links
- team contributions

The most important proof command is:

```bash
docker exec fw1 nft list ruleset
```

This command shows the rules that are actually loaded in the Linux kernel. This is stronger than only showing a Jinja2 template, because it proves that Ansible rendered and applied the firewall rules successfully.

---

## 3. Final Test Results

The final project version passed the automated integration tests.

Main test command:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/run_tests.yml
```

Observed result:

```text
85 passed, 0 failed, 11 skipped
pytest exit: 0
```

Generated artifacts:

```text
test_results/report.html
test_results/pytest.json
test_results/summary.json
test_results/pytest.stdout.log
test_results/pytest.stderr.log
```

Final generated summary excerpt:

```text
test_summary:
  passed: 85
  failed: 0
  skipped: 11
  total: 96
  success: true
health_summary:
  failover_count: 11
  split_brain_count: 1
  last_vip_owners:
    mgmt: fw1
    frontend: fw1
    backend: fw1
```

The one split-brain count was a transient monitor snapshot during forced failover stress. The test suite still passed and final VIP ownership returned to `fw1` on all three networks.

---

## 4. Files I Worked On or Finalized

### Main Ansible files

```text
ansible/ansible.cfg
ansible/requirements.yml
ansible/playbooks/site.yml
ansible/playbooks/run_tests.yml
ansible/roles/routing/defaults/main.yml
ansible/roles/routing/tasks/main.yml
```

### Inventory and group variables

```text
ansible/inventory/hosts.yml
ansible/inventory/hosts.ini
ansible/group_vars/all.yml
ansible/group_vars/firewalls.yml
ansible/library/inventory_validate.py
```

### Project validation and execution helpers

```text
.ansible-lint
requirements.txt
pytest.ini
Makefile
run_wsl_checks.sh
```

### Documentation

```text
README.md
docs/member-5-status.md
docs/requirements-validation.md
docs/team-integration-notes.md
docs/gitea-setup.md
docs/ci-runner-notes.md
```

### Shared integration touchpoints

```text
docker-compose.yml
scripts/monitor_health.py
scripts/generate_report.py
tests/conftest.py
tests/test_conntrackd.py
tests/test_failover.py
tests/test_ipv6.py
tests/test_nftables_rules.py
tests/test_port_isolation.py
```

Some of these files were shared integration files. My role was not always to create them alone. In several cases my contribution was to adapt, connect, test, document or finalize them so the complete project worked as one system.

---

## 5. Relevant Git Work

My work was mainly developed and integrated through the `yedige-ansible` branch and later through final integration commits on `main`.

Relevant branch commits include:

| Commit | Description |
|---|---|
| `46caeb0` | Added Ansible roles to the correct repository structure |
| `ebcf6ec` | Completed core Ansible infrastructure, linting and role testing direction |
| `57cc65b` | Updated README documentation |
| `9ea68ca` | Integrated Iliyas firewall branch into Ansible integration branch |
| `a3321d6` | Integrated Aisana monitoring branch into Ansible integration branch |

Relevant final integration commits include:

| Commit | Description |
|---|---|
| `9d4e7c5` | Finalized tested firewall lab delivery |
| `93fef9e` | Refined final README |
| `4f1946f` | Added individual report of Yedige |

---

## 6. Challenges and Solutions

| Challenge | Solution |
|---|---|
| Separate member branches did not work as one complete system at first | Connected Docker Compose, Ansible inventory, roles, tests and reports into one workflow |
| Ansible needed to manage Docker containers instead of normal VMs | Used Docker-compatible inventory and container-safe service handling |
| Early firewall output could look too empty if Ansible deployment was not applied | Added real verification using `docker exec fw1 nft list ruleset` after deployment |
| Routing could bypass the firewall path | Added and finalized the routing role through firewall VIPs |
| Integration tests needed to run repeatably | Created `run_tests.yml` to automate pytest, health monitoring and report generation |
| Generated reports needed to prove behavior, not just describe it | Added evidence from pytest, health monitor, VIP owners and nftables inspection |
| AI usage had to be transparent | Added AI documentation links and course/reference sources in README |

---

## 7. AI Usage

I used AI tools during the project for planning, debugging, refactoring suggestions, documentation structure and checking Ansible/Jinja2/Python logic. The AI output was not used blindly.

My workflow was:

1. Define the desired behavior using course material and the team architecture
2. Ask AI for implementation ideas or review suggestions
3. Compare the suggestions with Ansible, Docker, nftables and pytest requirements
4. Adapt the result to the actual repository structure
5. Run real commands and tests before accepting the work
6. Document the usage transparently

The final README includes links to the AI usage documentation:

- Team AI documentation for all members: https://docs.google.com/document/d/1Ib7Gq88vuzpHSePuDb54yeavhl8a8tRxOMuLts43P2o/edit?tab=t.0
- Full Member 5 Ansible prompt documentation: https://docs.google.com/document/d/15P2ON8nWbpC8yPIZYH8-OSrFajq5AzmDLTRxhw9PafI/edit?tab=t.0

References used during the work:

- Cloud Computing 07 Ansible lecture material: https://moodle.hof-university.de/pluginfile.php/1059261/mod_resource/content/1/CloudComputing_07_Ansible.pdf
- Professor's Cloud Computing GitLab examples: https://gitlab.hof-university.de/wwiedermann/20261_cloudcomputing
- Ansible YAML syntax reference: https://docs.ansible.com/projects/ansible/latest/reference_appendices/YAMLSyntax.html

---

## 8. Summary

My main contribution was making the project deployable, testable and explainable as one integrated firewall lab.

Completed work:

- Ansible configuration and deployment workflow completed
- Inventory and group variable integration completed
- Routing through firewall cluster VIPs completed
- Ansible-based integration test orchestration completed
- WSL/Linux Ansible checks completed
- Final verification evidence documented
- AI usage documentation references added
- Final project integration passed automated tests

Final result:

```text
85 passed, 0 failed, 11 skipped
```