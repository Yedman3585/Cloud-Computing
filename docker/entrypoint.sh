#!/bin/bash

set -e

echo "[entrypoint] Starting firewall node: ${HOSTNAME}"

echo 1 > /proc/sys/net/ipv4/ip_forward
echo 1 > /proc/sys/net/ipv6/conf/all/forwarding 2>/dev/null || true

echo 1 > /proc/sys/net/ipv4/ip_nonlocal_bind 2>/dev/null || true

# Create log directories
mkdir -p /var/log/supervisor
mkdir -p /var/log/nftables
mkdir -p /var/log/keepalived
mkdir -p /var/log/conntrackd

if [ ! -f /etc/nftables.conf ]; then
    echo "[entrypoint] No nftables.conf found, writing minimal default"
    cat > /etc/nftables.conf << 'EOF'
#!/usr/sbin/nft -f
flush ruleset

table inet filter {
    chain input {
        type filter hook input priority 0;
        policy drop;
        log prefix "DROP: " drop

        ct state established,related accept
        iif lo accept

        # Allow SSH so Ansible can connect
        tcp dport 22 accept

        # Allow ICMP / ICMPv6
        ip protocol icmp accept
        ip6 nexthdr icmpv6 accept

        # Allow VRRP (Keepalived)
        ip protocol vrrp accept
    }
    chain forward {
        type filter hook forward priority 0;
        policy drop;
        log prefix "DROP: " drop
    }
    chain output {
        type filter hook output priority 0;
        policy accept;
    }
}
EOF
fi

# shellcheck disable=SC2145
echo "[entrypoint] Handing off to: $@"
exec "$@"
