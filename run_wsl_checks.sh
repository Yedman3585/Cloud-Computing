#!/bin/bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ANSIBLE_CONFIG="${repo_root}/ansible/ansible.cfg"
export ANSIBLE_INVENTORY="${repo_root}/ansible/inventory/hosts.yml"
export ANSIBLE_ROLES_PATH="${repo_root}/ansible/roles"
export ANSIBLE_LIBRARY="${repo_root}/ansible/library"
export ANSIBLE_MODULE_UTILS="${repo_root}/ansible/module_utils"

cd "${repo_root}"

if [[ -z "${VIRTUAL_ENV:-}" && -f "${repo_root}/.venv_linux/bin/activate" ]]; then
    # Prefer the project Linux virtualenv over broken user-level Ansible entrypoints.
    # shellcheck source=/dev/null
    source "${repo_root}/.venv_linux/bin/activate"
fi

export PYTHONNOUSERSITE=1

if ! python -c "import ansible" >/dev/null 2>&1; then
    cat >&2 <<'EOF'
ERROR: Ansible is not importable in the current Python environment.

Fix in WSL from the repository root:
  python3 -m venv .venv_linux
  source .venv_linux/bin/activate
  python -m pip install -r requirements.txt molecule molecule-plugins[docker] ansible-lint
  ansible-galaxy collection install -r ansible/requirements.yml

Then rerun:
  bash run_wsl_checks.sh
EOF
    exit 1
fi

for required_cmd in ansible-inventory ansible-playbook ansible-lint; do
    if ! command -v "${required_cmd}" >/dev/null 2>&1; then
        echo "ERROR: ${required_cmd} is not installed in the active environment." >&2
        exit 1
    fi
done

echo "Using Python: $(command -v python)"
echo "Using Ansible inventory: $(command -v ansible-inventory)"

echo "=== Running Inventory Graph ==="
ansible-inventory --graph

echo "=== Running Syntax Check ==="
ansible-playbook ansible/playbooks/site.yml --syntax-check

echo "=== Running Ansible Lint ==="
ansible-lint ansible/
