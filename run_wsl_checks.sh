#!/bin/bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONNOUSERSITE=1
export ANSIBLE_CONFIG="${repo_root}/ansible/ansible.cfg"
export ANSIBLE_INVENTORY="${repo_root}/ansible/inventory/hosts.yml"
export ANSIBLE_ROLES_PATH="${repo_root}/ansible/roles"
export ANSIBLE_LIBRARY="${repo_root}/ansible/library"
export ANSIBLE_MODULE_UTILS="${repo_root}/ansible/module_utils"

cd "${repo_root}"

echo "=== Running Inventory Graph ==="
ansible-inventory --graph

echo "=== Running Syntax Check ==="
ansible-playbook ansible/playbooks/site.yml --syntax-check

echo "=== Running Ansible Lint ==="
ansible-lint ansible/
