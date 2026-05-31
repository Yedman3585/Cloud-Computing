#!/usr/bin/python

from __future__ import annotations

import ipaddress
import re
from typing import Any


NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
VALID_ACTIONS = {"accept", "drop", "reject"}
VALID_CHAINS = {"input", "forward", "output"}
VALID_PROTOCOLS = {"tcp", "udp", "icmp", "icmpv6", "vrrp", "all"}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _validate_ip_network(value: str, family: int) -> None:
    parsed = ipaddress.ip_network(str(value), strict=False)
    if parsed.version != family:
        raise ValueError(f"{value} is not IPv{family}")


def _validate_ports(rule_name: str, ports: Any, errors: list[str]) -> None:
    for port in _as_list(ports):
        try:
            number = int(port)
        except (TypeError, ValueError):
            errors.append(f"rule {rule_name}: port {port!r} is not an integer")
            continue
        if number < 1 or number > 65535:
            errors.append(f"rule {rule_name}: port {number} is outside 1..65535")


def validate_nodes(
    names: list[str],
    hostvars: dict[str, dict[str, Any]],
    required_count: int,
    errors: list[str],
) -> None:
    if len(names) != required_count:
        errors.append(f"expected {required_count} firewall nodes, found {len(names)}")

    seen_ipv4: set[str] = set()
    seen_ipv6: set[str] = set()
    seen_priorities: set[int] = set()

    for name in names:
        data = hostvars.get(name, {})
        for field in ("ipv4_addr", "ipv6_addr", "keepalived_priority"):
            if field not in data:
                errors.append(f"{name}: missing required host variable {field}")

        if "ipv4_addr" in data:
            try:
                ipaddress.ip_address(str(data["ipv4_addr"]))
            except ValueError as exc:
                errors.append(f"{name}: invalid ipv4_addr {data['ipv4_addr']!r}: {exc}")
            if data["ipv4_addr"] in seen_ipv4:
                errors.append(f"{name}: duplicate ipv4_addr {data['ipv4_addr']}")
            seen_ipv4.add(data["ipv4_addr"])

        if "ipv6_addr" in data:
            try:
                ipaddress.ip_address(str(data["ipv6_addr"]))
            except ValueError as exc:
                errors.append(f"{name}: invalid ipv6_addr {data['ipv6_addr']!r}: {exc}")
            if data["ipv6_addr"] in seen_ipv6:
                errors.append(f"{name}: duplicate ipv6_addr {data['ipv6_addr']}")
            seen_ipv6.add(data["ipv6_addr"])

        if "keepalived_priority" in data:
            try:
                priority = int(data["keepalived_priority"])
            except (TypeError, ValueError):
                errors.append(f"{name}: keepalived_priority must be an integer")
                continue
            if priority < 1 or priority > 254:
                errors.append(f"{name}: keepalived_priority must be between 1 and 254")
            if priority in seen_priorities:
                errors.append(f"{name}: duplicate keepalived_priority {priority}")
            seen_priorities.add(priority)

        if "conntrackd_sync_peer_ipv4" in data:
            try:
                ipaddress.ip_address(str(data["conntrackd_sync_peer_ipv4"]))
            except ValueError as exc:
                errors.append(
                    f"{name}: invalid conntrackd_sync_peer_ipv4 "
                    f"{data['conntrackd_sync_peer_ipv4']!r}: {exc}"
                )


def validate_objects(objects: dict[str, Any], errors: list[str]) -> None:
    for object_name, object_data in objects.items():
        if not NAME_RE.match(object_name):
            errors.append(f"object {object_name!r}: name must be nftables-safe")
        for family_key, family in (("ipv4", 4), ("ipv6", 6)):
            for value in _as_list(object_data.get(family_key, [])):
                try:
                    _validate_ip_network(str(value), family)
                except ValueError as exc:
                    errors.append(f"object {object_name}: invalid {family_key} {value!r}: {exc}")


def validate_rules(rules: list[dict[str, Any]], objects: dict[str, Any], errors: list[str]) -> None:
    known_objects = set(objects.keys()) | {"any"}
    for index, rule in enumerate(rules):
        rule_name = str(rule.get("name", f"rule_{index}"))
        if not NAME_RE.match(rule_name):
            errors.append(f"rule {rule_name!r}: name must be nftables-safe")

        action = str(rule.get("action", "")).lower()
        if action not in VALID_ACTIONS:
            errors.append(f"rule {rule_name}: action must be one of {sorted(VALID_ACTIONS)}")

        chain = str(rule.get("chain", "input")).lower()
        if chain not in VALID_CHAINS:
            errors.append(f"rule {rule_name}: chain must be one of {sorted(VALID_CHAINS)}")

        protocol = str(rule.get("protocol", "all")).lower()
        if protocol not in VALID_PROTOCOLS:
            errors.append(f"rule {rule_name}: protocol must be one of {sorted(VALID_PROTOCOLS)}")

        for endpoint in ("source", "destination"):
            value = str(rule.get(endpoint, "any"))
            if value not in known_objects:
                errors.append(f"rule {rule_name}: unknown {endpoint} object {value!r}")

        ports = rule.get("ports", [])
        if protocol in {"tcp", "udp"}:
            if not _as_list(ports):
                errors.append(f"rule {rule_name}: tcp/udp rules must define ports")
            _validate_ports(rule_name, ports, errors)
        elif _as_list(ports):
            errors.append(f"rule {rule_name}: ports are only valid for tcp/udp rules")


def validate_keepalived_cluster(cluster: dict[str, Any], errors: list[str]) -> None:
    if not cluster:
        errors.append("keepalived_cluster must be defined")
        return

    router_id = cluster.get("virtual_router_id")
    try:
        router_id_number = int(router_id)
    except (TypeError, ValueError):
        errors.append("keepalived_cluster.virtual_router_id must be an integer")
    else:
        if router_id_number < 1 or router_id_number > 255:
            errors.append("keepalived_cluster.virtual_router_id must be between 1 and 255")

    if not cluster.get("interface"):
        errors.append("keepalived_cluster.interface must be defined")

    for field, family in (("vip_ipv4", 4), ("vip_ipv6", 6)):
        value = cluster.get(field)
        if not value:
            errors.append(f"keepalived_cluster.{field} must be defined")
            continue
        try:
            _validate_ip_network(str(value), family)
        except ValueError as exc:
            errors.append(f"keepalived_cluster.{field} is invalid: {exc}")


def main() -> None:
    from ansible.module_utils.basic import AnsibleModule

    module = AnsibleModule(
        argument_spec=dict(
            firewall_node_names=dict(type="list", elements="str", required=True),
            firewall_hostvars=dict(type="dict", required=True),
            firewall_objects=dict(type="dict", required=True),
            firewall_rules=dict(type="list", elements="dict", required=True),
            keepalived_cluster=dict(type="dict", required=False, default={}),
            required_firewall_count=dict(type="int", default=3),
        ),
        supports_check_mode=True,
    )

    names = module.params["firewall_node_names"]
    hostvars = module.params["firewall_hostvars"]
    objects = module.params["firewall_objects"]
    rules = module.params["firewall_rules"]
    cluster = module.params["keepalived_cluster"]
    required_count = module.params["required_firewall_count"]

    errors: list[str] = []
    validate_nodes(names, hostvars, required_count, errors)
    validate_objects(objects, errors)
    validate_rules(rules, objects, errors)
    validate_keepalived_cluster(cluster, errors)

    if errors:
        module.fail_json(msg="inventory validation failed", errors=errors)

    module.exit_json(
        changed=False,
        msg="inventory contract is valid",
        firewall_nodes=names,
        firewall_rule_count=len(rules),
    )


if __name__ == "__main__":
    main()
