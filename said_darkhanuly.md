# Individual Report — Member: Said Darkhanuly

**Name:** Said Darkhanuly 

**GitLab:** @saiddrk 

**Branch:** `said-testing`

**Project:** Cloud Computing Group 05 — Topic 5.2: Scalable Firewall with Debian 13 and nftables  


---

# My Responsibilities

I was responsible for the Docker infrastructure, automated testing, monitoring, and reporting components of the firewall project.

---

# What I Implemented

## Docker Infrastructure

- Created a Docker Compose environment with three firewall nodes (`fw1`, `fw2`, `fw3`) configured for Keepalived high availability.
- Added three client containers for traffic simulation.
- Designed three isolated Docker networks (`mgmt_net`, `frontend_net`, `backend_net`) with static IP addressing.
- Built custom Debian 13 Docker images for firewall and client containers with the required networking and testing tools.

## Automated Testing

Developed Python test suites to verify:

- Keepalived failover between firewall nodes.
- nftables rules and allowed/blocked ports.
- IPv6 forwarding, rules, and connectivity.
- Traffic generation using Scapy for firewall validation.

## Ansible Integration

- Created an Ansible playbook to automatically execute the full test suite after deployment.
- Configured the inventory for all firewall nodes and integrated testing into the deployment pipeline.

## Monitoring and Reporting

- Implemented a health monitoring script for firewall status, VIP ownership, Keepalived, nftables, and SSH checks.
- Developed an HTML reporting tool that combines pytest results and monitoring data into a readable report.

---

## 4. Git Commit History

My work was committed to the `said-testing` branch:

| Commit | Description |
|---|---|
| `b34f92ec` | fixing docker-compose.yml file |
| `48ed9822` | Added Dockerfile.cleint |
| `405486b5` | Moved Dockerfile.cleint to docker directory |
| `f8b8bcb3` | fix: docker foundation and config correction |
| `fc4376de` | feat: pytest test suite - rules and failover |
| `bddf2ce4` | feat: IPv6 tests and scapy traffic generator |
| `38a4a8ab` | feat: conntrackd tests, pytest config, dependencies |
| `6696e75b` | feat: Ansible integration and CI/CD pipeline |

---

# Files I Created

```text
docker-compose.yml
docker/Dockerfile
docker/Dockerfile.client
docker/entrypoint.sh
docker/supervisord.conf

tests/conftest.py
tests/test_failover.py
tests/test_nftables_rules.py
tests/test_ipv6.py
tests/traffic_generator.py

ansible/playbooks/run_tests.yml
ansible/inventory/hosts.yml

scripts/monitor_health.py
scripts/generate_report.py
```

---

# Technologies Used

- Docker & Docker Compose
- Debian 13
- Python
- Pytest
- Scapy
- nftables
- Keepalived
- Ansible

---

# Summary

I implemented the Docker infrastructure, automated testing, monitoring, and reporting components of the project. The completed work provides automated deployment validation, failover testing, IPv4/IPv6 verification, traffic generation, cluster health monitoring, and HTML reporting for the firewall environment.