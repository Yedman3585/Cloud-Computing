# Individual Report - Member 5: Ansible Orchestration, Routing, Integration and Documentation

**Name:** Yedige Mussabayev  
**GitLab:** @yedman3585  
**Branch:** `yedige-ansible`, final integration on `main`  
**Project:** Cloud Computing Group 05 - Topic 5.2: Scalable Firewall with Debian 13 and nftables  
**Date:** July 2026

---

## 1. My Responsibilities

As Member 5, I was responsible for the Ansible orchestration layer and for connecting several separately developed project parts into one repeatable deployment workflow.

My main responsibilities were:

- Configure the Ansible project structure and execution settings
- Connect Docker Compose infrastructure with Ansible deployment
- Maintain the inventory structure used by the firewall cluster
- Integrate firewall, keepalived, conntrackd and routing roles into one deployment playbook
- Implement routing orchestration for clients and backend servers
- Create the Ansible-based test orchestration playbook
- Run and document WSL/Debian validation commands
- Help integrate the work of other members into the final project version
- Maintain final README sections for installation, verification, acceptance criteria and AI usage transparency

---

## 2. What I Implemented

### 2.1 Ansible Project Configuration

I worked on the Ansible project configuration so that the repository can be deployed consistently from the project root.

Important files:

| File | Purpose |
|---|---|
| `ansible/ansible.cfg` | Defines inventory, roles path, custom library path and Ansible defaults |
| `ansible/requirements.yml` | Defines required Ansible collections, especially Docker-related modules |
| `.ansible-lint` | Keeps linting compatible with the Docker/container-based lab environment |
| `run_wsl_checks.sh` | Runs inventory graph, syntax check and ansible-lint in WSL/Linux |

The purpose was to make the Ansible part reproducible instead of depending on manual local configuration.

Validation command:

```bash
bash run_wsl_checks.sh
```

Observed result in the final version:

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

### 2.2 Inventory and Variable Integration

The final project uses an Ansible inventory that describes the Docker Compose lab nodes and connects them to firewall-specific variables.

Important files:

| File | Purpose |
|---|---|
| `ansible/inventory/hosts.yml` | YAML inventory for firewalls, backend servers and test clients |
| `ansible/inventory/hosts.ini` | Inventory compatibility format |
| `ansible/group_vars/all.yml` | Shared network topology, VIPs, firewall objects and firewall rules |
| `ansible/group_vars/firewalls.yml` | Firewall-specific package, nftables, keepalived and conntrackd variables |
| `ansible/library/inventory_validate.py` | Custom validation module for the inventory contract |

I helped align these variables with the final Docker Compose topology and with the requirements of the firewall, HA and routing roles.

The important design decision was to keep the firewall policy readable in group variables instead of hardcoding everything inside shell commands. This follows the desired-state idea from the course Ansible material.

### 2.3 Site Deployment Playbook

I worked on the main deployment playbook that connects all Ansible roles into one repeatable rollout.

File:

```text
ansible/playbooks/site.yml
```

The playbook performs three main phases:

1. Validate the firewall inventory contract
2. Configure firewall cluster nodes using the common, firewall, keepalived and conntrackd roles
3. Configure routing on backend servers and test clients

This allows the project to be deployed with one command:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/site.yml -i ansible/inventory/hosts.yml
```

Final observed result:

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

I implemented and finalized the routing role that forces lab traffic through the firewall cluster instead of bypassing it.

Files:

```text
ansible/roles/routing/defaults/main.yml
ansible/roles/routing/tasks/main.yml
```

The routing role is important because the project is not only about containers existing. Traffic from clients to backend servers must actually pass through the firewall path.

The role configures routes for:

- frontend clients
- backend servers
- Alpine-based backend containers
- Docker Compose network paths

This part was also adjusted after testing because some backend containers use Alpine tooling and required compatibility handling.

### 2.5 Integration Test Orchestration with Ansible

I created and finalized the Ansible playbook that runs the integration test workflow after deployment.

File:

```text
ansible/playbooks/run_tests.yml
```

The playbook performs:

1. Verify pytest is available in the active virtual environment
2. Wait until firewall containers become healthy
3. Start the health monitor in the background
4. Wait for Keepalived election to settle
5. Run the pytest integration suite
6. Save stdout and stderr logs
7. Stop the health monitor
8. Generate the combined HTML report
9. Fail the playbook when pytest fails

Run command:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/run_tests.yml
```

Final observed result:

```text
pytest exit: 0
PLAY RECAP
localhost ok=11 failed=0 skipped=2
```

### 2.6 Connecting Work from Other Members

A large part of my work was integration work. The project parts were developed separately, so they had to be connected into one runnable lab.

I helped connect:

- Member 1 firewall/nftables work with Ansible role execution
- Member 2 Docker Compose infrastructure with Ansible inventory and routing
- Member 3 high availability and CI/Gitea direction with the final delivery structure
- Member 4 monitoring and automated tests with Ansible test orchestration

This integration work was important because the project is graded as a working system, not as five isolated parts.

### 2.7 Final Documentation and Verification Evidence

I worked on the final README so that the professor can quickly understand what to run and what to check.

Important README topics I documented or helped finalize:

- installation requirements
- Docker Compose startup
- Ansible deployment
- `nft list ruleset` proof inside `fw1`
- Keepalived VIP ownership checks
- conntrackd synchronization checks
- automated pytest results
- Gitea Actions notes
- acceptance criteria
- AI usage documentation links
- team contribution summary

The most important proof command is:

```bash
docker exec fw1 nft list ruleset
```

This command shows the firewall rules that are actually loaded in the Linux kernel. It is stronger evidence than reading a template file because it proves that Ansible rendered and applied the rules successfully.

---

## 3. Final Test Results

The final project version passed the automated test suite.

Main command:

```bash
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/run_tests.yml
```

Observed final result:

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

The generated summary included:

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

The one split-brain count was a transient monitor snapshot during forced failover stress. The tests still passed and final VIP ownership returned to `fw1` on all three networks.

---

## 4. Files I Worked On or Finalized

### Ansible orchestration

```text
ansible/ansible.cfg
ansible/requirements.yml
ansible/playbooks/site.yml
ansible/playbooks/run_tests.yml
ansible/roles/routing/defaults/main.yml
ansible/roles/routing/tasks/main.yml
```

### Inventory and firewall variable integration

```text
ansible/inventory/hosts.yml
ansible/inventory/hosts.ini
ansible/group_vars/all.yml
ansible/group_vars/firewalls.yml
ansible/library/inventory_validate.py
```

### Project validation and local execution support

```text
.ansible-lint
requirements.txt
pytest.ini
Makefile
run_wsl_checks.sh
```

### Final integration and documentation

```text
README.md
docs/member-5-status.md
docs/requirements-validation.md
docs/team-integration-notes.md
docs/gitea-setup.md
docs/ci-runner-notes.md
```

### Integration touchpoints with other members

```text
docker-compose.yml
scripts/monitor_health.py
scripts/generate_report.py
tests/conftest.py
tests/test_failover.py
tests/test_conntrackd.py
tests/test_ipv6.py
tests/test_nftables_rules.py
tests/test_port_isolation.py
```

Some of these files were shared integration files. My role was not always to create them alone, but to connect, adapt, test and document them inside the final working system.

---

## 5. Challenges and Solutions

| Challenge | Solution |
|---|---|
| Separate team parts did not run as one system at first | Connected Docker Compose, Ansible inventory, firewall roles, HA roles, tests and reports into one workflow |
| Firewall containers existed but early rulesets were too empty | Added README proof based on `docker exec fw1 nft list ruleset` and ensured Ansible deployment applies real nftables policy |
| Ansible roles had to run inside Docker containers without systemd | Adjusted service handling and lint configuration for supervisor/init/container compatibility |
| Backend/client routing could bypass the firewall path | Added routing role so traffic goes through firewall VIPs |
| Test execution needed to be repeatable | Created `run_tests.yml` to run pytest, monitor health and generate reports automatically |
| README needed to prove behavior, not only describe it | Added real evidence fragments from Ansible, pytest, nftables, VIP ownership and generated summaries |
| AI usage had to be transparent | Added documentation links and course/reference sources in README |

---

## 6. AI Usage

I used AI tools during the project, especially for planning, debugging, documentation drafts and checking Ansible/Jinja2/Python logic. The AI output was not accepted blindly.

My process was:

1. Define the desired project behavior based on course material and team architecture
2. Ask AI for implementation ideas or refactoring suggestions
3. Compare the suggestions with Ansible, Docker and nftables requirements
4. Adapt the code to the actual project structure
5. Run real commands and tests before accepting the result
6. Document the AI usage transparently

AI documentation links were added to the final README:

```text
Team AI documentation for all members
Full Member 5 Ansible prompt documentation
```

Course and technical references used:

```text
Cloud Computing 07 Ansible lecture material
Professor's Cloud Computing GitLab examples
Ansible YAML syntax reference
```

---

## 7. Summary

My main contribution was making the project deployable, testable and explainable as one complete firewall lab.

Completed work:

- Ansible configuration and deployment structure completed
- Inventory and group variable integration completed
- Routing through firewall cluster VIPs completed
- Ansible-based integration test orchestration completed
- Final WSL/Debian validation workflow completed
- README verification and acceptance criteria completed
- AI usage documentation references added
- Final project integration passed automated tests

Final result:

```text
85 passed, 0 failed, 11 skipped
```