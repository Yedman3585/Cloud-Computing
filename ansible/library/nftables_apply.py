#!/usr/bin/python

from __future__ import annotations

from pathlib import Path


def read_rules(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text()


def main() -> None:
    from ansible.module_utils.basic import AnsibleModule

    module = AnsibleModule(
        argument_spec=dict(
            rules_path=dict(type="path", required=True),
            nft_bin=dict(type="str", default="nft"),
            apply=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
    )

    rules_path = Path(module.params["rules_path"])
    nft_bin = module.params["nft_bin"]
    should_apply = module.params["apply"]

    if not rules_path.exists():
        module.fail_json(msg=f"nftables rules file does not exist: {rules_path}")
    if not rules_path.is_file():
        module.fail_json(msg=f"nftables rules path is not a file: {rules_path}")

    content = read_rules(rules_path)
    if not content.strip():
        module.fail_json(msg=f"nftables rules file is empty: {rules_path}")
    if "table " not in content or "chain " not in content:
        module.fail_json(msg="nftables rules must contain at least one table and chain")

    check_rc, check_out, check_err = module.run_command([nft_bin, "-c", "-f", str(rules_path)])
    if check_rc != 0:
        module.fail_json(
            msg="nftables syntax validation failed",
            rc=check_rc,
            stdout=check_out,
            stderr=check_err,
        )

    if not should_apply:
        module.exit_json(
            changed=False,
            msg="nftables rules validated; apply skipped because rendered file was unchanged",
            stdout=check_out,
            stderr=check_err,
        )

    if module.check_mode:
        module.exit_json(
            changed=True,
            msg="nftables rules validated; apply would run in normal mode",
            stdout=check_out,
            stderr=check_err,
        )

    apply_rc, apply_out, apply_err = module.run_command([nft_bin, "-f", str(rules_path)])
    if apply_rc != 0:
        module.fail_json(
            msg="nftables apply failed",
            rc=apply_rc,
            stdout=apply_out,
            stderr=apply_err,
        )

    module.exit_json(
        changed=True,
        msg="nftables rules validated and applied",
        stdout=apply_out,
        stderr=apply_err,
    )


if __name__ == "__main__":
    main()
