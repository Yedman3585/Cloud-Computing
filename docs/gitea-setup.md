# Gitea Setup And Delivery Notes

This repository contains a Gitea Actions workflow in `.gitea/workflows/ci.yml`.
The file is only one part of the Gitea requirement. A real demonstration also
needs a running Gitea instance, a repository hosted in that instance, an online
act runner, and registry settings for OCI image publishing.

## What The Repository Already Provides

- `.gitea/workflows/ci.yml` for Gitea Actions.
- Static validation job: Docker Compose config, Ansible inventory graph,
  Ansible syntax check, ansible-lint, Python compile check.
- OCI image build job for the firewall image and the client/test image.
- Integration job that starts Docker Compose, deploys with Ansible, runs the
  test playbook, and uploads `test_results/`.
- Optional image publishing job for the Gitea OCI registry.

The workflow runs on `main`, `master`, `final`, and `lastrun` branches. It can
also be started manually with `workflow_dispatch` when the Gitea installation
supports manual workflow dispatch.

## What Must Be Done In Gitea UI Or On The Server

1. Create or import the project repository in Gitea.
2. Push this repository to Gitea, including the `.gitea/workflows/ci.yml` file.
3. Enable Actions for the repository or instance.
4. Register an `act_runner` for the repository, organization, or instance.
5. Make sure the runner has Docker access, because the integration job starts
   privileged Docker Compose firewall containers.
6. Enable the Gitea package/container registry.
7. Add registry variables and secrets if image publishing should run.

## Required Runner Capability

The integration job needs Docker. A runner without Docker access can run only
static validation jobs. For the full project proof, the runner must be able to
run these commands:

```bash
docker compose config --quiet
docker build -f docker/DockerFile -t firewall-lab-firewall:ci .
docker build -f docker/Dockerfile.client -t firewall-lab-client:ci .
docker compose up -d --build
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/site.yml -i ansible/inventory/hosts.yml
ANSIBLE_CONFIG=ansible/ansible.cfg ansible-playbook ansible/playbooks/run_tests.yml
```

## Variables And Secrets For OCI Publishing

The `publish-images` job is disabled by default. Enable it only after the Gitea
registry is ready.

Repository or organization variables:

```text
PUBLISH_OCI_IMAGES=true
GITEA_REGISTRY=<gitea-hostname-with-optional-port>
GITEA_IMAGE_NAMESPACE=<owner-or-organization>
```

Repository or organization secrets:

```text
GITEA_REGISTRY_USER=<gitea-username>
GITEA_REGISTRY_TOKEN=<personal-access-token-or-password>
```

Expected image names after publishing:

```text
<GITEA_REGISTRY>/<GITEA_IMAGE_NAMESPACE>/firewall-lab-firewall:<git-sha>
<GITEA_REGISTRY>/<GITEA_IMAGE_NAMESPACE>/firewall-lab-firewall:latest
<GITEA_REGISTRY>/<GITEA_IMAGE_NAMESPACE>/firewall-lab-client:<git-sha>
<GITEA_REGISTRY>/<GITEA_IMAGE_NAMESPACE>/firewall-lab-client:latest
```

## Kubernetes Rollout Note

The current final repository focuses on the verified Docker Compose plus Ansible
firewall lab, because unverified Kubernetes and Helm files were removed after
review. If the instructor requires a real Kubernetes production path, then the
team still needs to add and test Kubernetes manifests or a Helm chart plus a
Gitea Actions rollout job using `kubectl` or `helm` against kind or minikube.

Do not claim Kubernetes deployment as complete unless the following is proven:

```bash
kind create cluster
kubectl apply -f <manifests>
kubectl get pods
kubectl get svc
kubectl rollout status deployment/<name>
```

## Minimum Evidence To Show

For the current final scope, the useful evidence is:

```text
Gitea repository exists
Gitea Actions are enabled
act_runner is online
validate job passed
build-images job passed
integration-test job passed
publish-images job passed, if registry variables/secrets are configured
OCI images visible in Gitea Packages, if publishing is enabled
```
