#!/usr/bin/python3
from ansible.module_utils.basic import AnsibleModule
import subprocess

DOCUMENTATION = '''
module: nftables_rule
short_description: Manage nftables rules
description:
    - Add or remove nftables rules
options:
    table:
        description: nftables table name
        required: true
    chain:
        description: nftables chain name
        required: true
    rule:
        description: nftables rule to add or remove
        required: true
    state:
        description: present or absent
        default: present
'''

def run_nft(cmd):
    result = subprocess.run(
        ['nft'] + cmd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr

def main():
    module = AnsibleModule(
        argument_spec=dict(
            table=dict(type='str', required=True),
            chain=dict(type='str', required=True),
            rule=dict(type='str', required=True),
            state=dict(type='str', default='present',
                      choices=['present', 'absent']),
        )
    )

    table = module.params['table']
    chain = module.params['chain']
    rule  = module.params['rule']
    state = module.params['state']

    rc, stdout, stderr = run_nft(['list', 'chain', table, chain])
    exists = rule in stdout

    if state == 'present' and not exists:
        rc, _, stderr = run_nft(['add', 'rule', table, chain, rule])
        if rc != 0:
            module.fail_json(msg=f"nft error: {stderr}")
        module.exit_json(changed=True, msg="Rule added")

    elif state == 'absent' and exists:
        for line in stdout.splitlines():
            if rule in line and 'handle' in line:
                handle = line.split('handle')[-1].strip().split()[0]
                run_nft(['delete', 'rule', table, chain, 'handle', handle])
        module.exit_json(changed=True, msg="Rule removed")

    else:
        module.exit_json(changed=False, msg="No changes needed")

if __name__ == '__main__':
    main()
