# shahzod.md — My Work on This Project

**Author:** Shahzod Mukhamedzhanov (Member 3)
**Project:** Cloud Computing Group 05 — Topic 5.2: Scalable Firewall with Debian 13 and nftables
**Reference branch:** `shahzod-final` (all changes described below can be reviewed there)

---

## 1. How my role changed during the project

I originally started on the Kubernetes side of the project — Services,
Deployments, HorizontalPodAutoscaler (HPA) configuration, and the related
manifests, before the project direction changed.

When the instructor told the team not to use Kubernetes for this topic, my
work shifted away from that direction. From that point on, I moved to
finalizing the project on the Ansible/Docker Compose architecture the team
settled on — the High Availability layer (Keepalived/VRRP), the routing
configuration, the Docker Compose setup, and the CI/CD pipeline — and became
the member who pulled the pieces together into a working, finalized project.

## 2. Files I created or changed

The following are the files and areas I created or modified. (No commit
hashes listed here — everything below can be reviewed directly on the
`shahzod-final` branch.)

- Keepalived / VRRP Ansible role — three VRRP instances for mgmt, frontend,
  and backend networks, including the fix for the VRRP split-brain issue
- Ansible routing role — static routes between the mgmt, frontend, and
  backend networks
- Docker Compose configuration — service/network definitions, and the fix
  for the intermittent Docker DNS resolution issue between containers
- Gitea CI/CD pipeline (`run_tests.yml`), including the fix for the pytest
  working-directory issue
- `monitor_health.py` — restored multi-VIP tracking after it was reverted to
  single-VIP by a branch merge
- Removal of the obsolete Kubernetes manifests/scripts once the project
  direction moved away from Kubernetes
- The configuration folder I created for the routing setup, which I shared
  with the rest of the team so everyone could deploy it consistently

## 3. Folder and file listing

```text
ansible/roles/keepalived/                      VRRP role: mgmt/frontend/backend instances, split-brain fix
    tasks/main.yml
    templates/keepalived.conf.j2
    defaults/main.yml

ansible/roles/routing/                         Static routing role between the three networks
    tasks/main.yml
    templates/routes.j2
    defaults/main.yml

docker-compose.yml                             Service/network definitions, Docker DNS resolution fix

.gitea/workflows/run_tests.yml                 CI/CD pipeline, pytest working-directory fix

scripts/monitor_health.py                      Multi-VIP cluster health monitor (restored after merge regression)

k8s/ (removed)                                 Obsolete Kubernetes manifests/scripts, removed after
                                                the instructor's direction to drop Kubernetes
```

_(Adjust paths/filenames above if they differ from the exact names in the
repository — this list reflects the roles and files I created or changed as
described in Section 2.)_

## 4. Note to the instructor — regarding git history

As we discussed, most of my commits were pushed close to the final deadline.
I want to note again, for the record, that this reflects when the work was
integrated and finalized, not when it was done. I attended every practice
session and lecture this semester and showed my progress weekly throughout —
this can be checked against your own weekly notes. I'd ask that the timing of
my pushes on their own not be used to reduce my score, given that context.

## 5. Note on the routing files and Member 5

I created the Ansible routing role and the accompanying configuration
folder, and I sent that folder to the rest of the group, including Member 5,
so the team could use it.

I want to flag, in my own words and for my own record, that Member 5's
individual report describes those routing files as work he created. From
what I can tell, he took the folder I had already written, ran it past AI to
reword/rewrite the description of it, and wrote it up as his own
contribution. I don't think that's an accurate account of who actually
created the routing files, and I want that noted here.

This is my own account of the situation, written for my own records — I'm
not asserting this is settled or proven, just documenting what I observed so
there's a record of my side alongside Member 5's report.

## 6. Weekly participation and progress

I participated in every practice session throughout the semester and showed
my progress each week — following the guidance given in those sessions,
adjusting my work as the project direction changed (including the move away
from Kubernetes), and keeping the team updated on where the HA/CI-CD side of
the project stood. This weekly record is separate from the git history and
should be checked against the professor's own notes from each session.

---

_This file is my own summary of my contribution. For the authoritative
change history, please refer to the `shahzod-final` branch directly._
