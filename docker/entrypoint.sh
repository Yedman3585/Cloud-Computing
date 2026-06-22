#!/bin/bash
set -e

echo "[entrypoint] Starting firewall node: ${HOSTNAME}"

echo 1 > /proc/sys/net/ipv4/ip_forward
echo 1 > /proc/sys/net/ipv6/conf/all/forwarding 2>/dev/null || true
echo 1 > /proc/sys/net/ipv4/ip_nonlocal_bind 2>/dev/null || true

# Create log directories
mkdir -p /var/log/supervisor /var/log/nftables /var/log/keepalived /var/log/conntrackd /var/log/firewall

# ulogd config: NFLOG group 1 -> /var/log/firewall/dropped.log
cat > /etc/ulogd.conf << 'ULOGDEOF'
[global]
logfile="/var/log/ulogd.log"
loglevel=5
stack=log1:NFLOG,base1:BASE,ifi1:IFINDEX,ip2str1:IP2STR,print1:PRINTPKT,emu1:LOGEMU

[log1]
group=1

[emu1]
file="/var/log/firewall/dropped.log"
sync=1
ULOGDEOF

echo "[entrypoint] Writing default nftables ruleset with NFLOG logging"
cat > /etc/nftables.conf << 'EOF'
#!/usr/sbin/nft -f
flush ruleset

table inet filter {
    chain input {
        type filter hook input priority 0;
        policy drop;

        ct state established,related accept
        iif lo accept

        tcp dport 22 accept
        tcp dport 5000 accept
        ip protocol icmp accept
        ip6 nexthdr icmpv6 accept
        ip protocol vrrp accept

        log prefix "DROP-IN " group 1 counter drop
    }
    chain forward {
        type filter hook forward priority 0;
        policy drop;
        log prefix "DROP-FWD " group 1 counter drop
    }
    chain output {
        type filter hook output priority 0;
        policy accept;
    }
}
EOF

# shellcheck disable=SC2145
echo "[entrypoint] Handing off to: $@"
exec "$@"
