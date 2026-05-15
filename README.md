# Scalable High-Availability Firewall (nftables)

**Cloud Computing Term Project**  
**Topic 5.2**: Scalable Firewall — Debian 13 + nftables

## Project Description

This project implements a **flexible, high-availability firewall** consisting of **three identical nodes**.  
The solution provides automatic failover using Keepalived. If the active node fails, one of the standby nodes automatically takes over the virtual (Cluster) IP with minimal downtime.

The entire firewall is configured and managed exclusively through **Ansible**, ensuring identical behavior across different environments:
- Docker / Docker Compose (development & testing)
- Kubernetes
- Virtual machines
- Physical hardware / LXC containers

### Key Features
- Modern **nftables** firewall (IPv4 + IPv6 fully supported)
- High availability with **Keepalived** (VRRP / unicast mode suitable for containers)
- Connection state synchronization (**conntrackd**)
- Rules are fully configurable via **Ansible Inventory** (including dynamic hostname resolution)
- Ansible manages everything: OS configuration, package installation, nftables rules, and Keepalived
- Diagnostic tools included: `tcpdump`, `iftop`, `cbm`
- Test infrastructure with multiple isolated networks for realistic traffic testing

## Project Structure

```bash
.
├── ansible/                  # Ansible configuration
│   ├── inventory/
│   ├── roles/
│   │   ├── common/
│   │   ├── nftables/        
│   │   ├── keepalived/      
│   │   ├── conntrackd/      
│   │   └── monitoring/
│   ├── playbooks/
│   └── group_vars/
├── docker/                   # Local test environment
│   ├── docker-compose.yml
│   └── Dockerfile            # Minimal Debian 13 base
├── kubernetes/               # Helm chart (prepared by team member 5)
├── tests/                    # Automated tests (failover, rules, IPv6, etc.)
├── docs/
├── README.md
└── .gitlab-ci.yml            # CI/CD pipeline (Gitea Actions)


## Note:
Initial description and proejct's structure can be changed. 
The given markdown is done in order to provide overall understanding of specific part of work for each individual. 

