# Individual Report — Member: Said Darkhanuly

**Name:** Said Darkhanuly 

**GitLab:** @saiddrk 

**Branch:** `said-testing`

**Project:** Cloud Computing Group 05 — Topic 5.2: Scalable Firewall with Debian 13 and nftables  

---

## 1. My Responsibilities

As a project member, I was responsible for the Docker infrastructure, automated testing, monitoring, and reporting components of the firewall cluster.

My responsibilities included:

- Building the Docker environment for firewall and client nodes
- Creating isolated Docker networks
- Building custom Debian 13 Docker images
- Developing automated Python tests
- Implementing traffic generation using Scapy
- Integrating tests with Ansible
- Implementing cluster health monitoring
- Generating HTML reports from test results

---

## 2. What I Implemented

### 2.1 Docker Compose Infrastructure

I created the Docker Compose environment consisting of three firewall nodes (`fw1`, `fw2`, `fw3`) configured for high availability with Keepalived.

Each firewall container:

- Has fixed IP addresses on all three networks
- Uses different Keepalived priorities (110, 100, 90)
- Runs in privileged mode to manage nftables
- Includes health checks using `nft list ruleset`

I also created three client containers (`client1`, `client2`, `client3`) for traffic simulation. They are connected only to the frontend network and use Scapy to generate raw packets.

---

### 2.2 Docker Networks

I designed three isolated Docker bridge networks:

| Network | Purpose |
|----------|---------|
| `mgmt_net` | Management traffic (SSH, Keepalived, conntrackd) |
| `frontend_net` | Client-to-firewall communication |
| `backend_net` | Protected backend servers |

Each container receives static IP addresses, ensuring predictable communication between nodes.

---

### 2.3 Custom Docker Images

I created custom Debian 13 Docker images for both firewall and client nodes.

The firewall image includes:

- nftables
- Keepalived
- conntrackd
- Python
- OpenSSH
- Scapy
- Pytest

I also implemented:

- `entrypoint.sh` to enable IPv4/IPv6 forwarding and initialize nftables
- `supervisord.conf` to run SSH and firewall services simultaneously

A lightweight client image was also created with Python, Scapy, and networking tools.

---

### 2.4 Automated Failover Testing

I developed automated pytest tests verifying Keepalived failover.

The tests:

- Stop the master firewall
- Detect VIP migration to backup nodes
- Verify recovery after restart
- Test double-failure scenarios

Helper functions automatically restore the environment after each test.

---

### 2.5 nftables Validation Tests

I implemented tests validating the firewall configuration.

The test suite verifies:

- nftables rules are loaded
- Default DROP policy is active
- Allowed ports (22, 80, 443) are reachable
- Blocked ports are filtered
- Required firewall rules exist on every node

---

### 2.6 IPv6 Tests

I created automated IPv6 tests that verify:

- IPv6 forwarding
- IPv6 nftables rules
- ICMPv6 support
- IPv6 TCP connectivity
- Proper handling when Docker IPv6 is unavailable

---

### 2.7 Traffic Generator

I implemented a Scapy-based traffic generation tool capable of:

- Sending TCP SYN packets
- Sending ICMP echo requests
- Sending UDP packets
- Performing HTTP GET requests
- Generating SYN bursts for stress testing

The tool can be executed as standalone or integrated into the pytest suite.

---

### 2.8 Ansible Test Integration

I created an Ansible playbook that automatically runs the entire test suite after deployment.

The playbook:

- Waits for all firewall nodes to become healthy
- Starts health monitoring
- Executes pytest
- Generates HTML reports
- Fails the deployment if any tests fail

---

### 2.9 Health Monitoring and Reporting

I implemented continuous health monitoring for the firewall cluster.

The monitoring script checks:

- Container status
- nftables availability
- VIP ownership
- SSH connectivity
- Keepalived status

Snapshots are stored in `health.json`.

I also created an HTML report generator that combines monitoring data with pytest results to produce:

- Test summaries
- Pass/Fail statistics
- Failover timeline
- Cluster health information
- CI-friendly JSON summary

---

## 3. Files I Created

```text
docker-compose.yml

docker/
├── Dockerfile
├── Dockerfile.client
├── entrypoint.sh
└── supervisord.conf

tests/
├── conftest.py
├── test_failover.py
├── test_nftables_rules.py
├── test_ipv6.py
└── traffic_generator.py

scripts/
├── monitor_health.py
└── generate_report.py

ansible/
├── inventory/hosts.yml
└── playbooks/run_tests.yml
```

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

## 5. AI Usage

I used Claude as an AI assistant during this project. The AI helped with:

- Explaining Docker Compose networking and container communication
- Assisting with Python test development and debugging (Pytest and Scapy)
- Helping implement health monitoring and HTML reporting scripts
- Identifying and fixing issues in Python and Docker configuration files
- Explaining Docker networking, Keepalived failover behavior, and Ansible test integration

All AI-generated code was reviewed, tested, and verified to work correctly before committing. The final validation was always done by running the actual commands and checking real output.

---

## 6. Summary

I successfully implemented the Docker infrastructure, automated testing, monitoring, and reporting components of the firewall project.

Completed work includes:

- Docker Compose environment with HA firewall nodes
- Custom Debian 13 Docker images
- Automated failover testing
- nftables validation tests
- IPv6 testing
- Scapy traffic generation tools
- Ansible test integration
- Health monitoring system
- HTML reporting for test results