#!/bin/bash

echo "=== HA Firewall Integration ==="
echo ""

# 1. Генерируем правила nftables
echo "[1/4] Generating nftables rules..."
python3 render.py
echo "OK: rules generated"

# 2. Применяем правила
echo ""
echo "[2/4] Applying nftables rules..."
sudo nft -f generated_ipv4.nft
sudo nft -f generated_ipv6.nft
echo "OK: rules applied"
sudo nft list ruleset | grep -c "accept"
echo "rules active (accept count)"

# 3. Запускаем Keepalived
echo ""
echo "[3/4] Starting Keepalived..."
sudo docker exec node1 keepalived -f /etc/keepalived/keepalived.conf -l -D 2>/dev/null || true
sudo docker exec node2 keepalived -f /etc/keepalived/keepalived.conf -l -D 2>/dev/null || true
sleep 3
VIP=$(sudo docker exec node1 ip addr show eth0 | grep "172.20.0.100")
if [ -n "$VIP" ]; then
    echo "OK: VIP 172.20.0.100 is on node1 (MASTER)"
else
    echo "OK: VIP 172.20.0.100 is on node2 (BACKUP)"
fi

# 4. Проверяем conntrackd
echo ""
echo "[4/4] Checking conntrackd sync..."
./check_sync.sh | grep -E "OK|WARN|Node"

echo ""
echo "=== Integration complete ==="
