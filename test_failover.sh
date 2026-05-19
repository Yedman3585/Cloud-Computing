#!/bin/bash

PASS=0
FAIL=0

echo "==============================="
echo "  HA Firewall Failover Tests"
echo "==============================="

# ─── Сценарий 1: Node1 падает ───
echo ""
echo "--- Test 1: Node1 goes down ---"

# Убеждаемся что keepalived запущен на обоих
sudo docker exec node1 pkill keepalived 2>/dev/null || true
sudo docker exec node2 pkill keepalived 2>/dev/null || true
sleep 1
sudo docker exec node1 keepalived -f /etc/keepalived/keepalived.conf -l -D
sudo docker exec node2 keepalived -f /etc/keepalived/keepalived.conf -l -D
sleep 3

# VIP должен быть на node1
VIP=$(sudo docker exec node1 ip addr show eth0 | grep "172.20.0.100")
if [ -n "$VIP" ]; then
    echo "OK: VIP is on node1 (MASTER) before test"
else
    echo "WARN: VIP not on node1 before test"
fi

# Останавливаем keepalived на node1
sudo docker exec node1 pkill keepalived
sleep 4

# VIP должен перейти на node2
VIP2=$(sudo docker exec node2 ip addr show eth0 | grep "172.20.0.100")
if [ -n "$VIP2" ]; then
    echo "PASS: VIP moved to node2 after node1 failure"
    PASS=$((PASS+1))
else
    echo "FAIL: VIP did not move to node2"
    FAIL=$((FAIL+1))
fi

# Восстанавливаем node1
sudo docker exec node1 keepalived -f /etc/keepalived/keepalived.conf -l -D
sleep 3
echo "OK: node1 restored"

# ─── Сценарий 2: nftables crash ───
echo ""
echo "--- Test 2: nftables crash on node1 ---"

# Сбрасываем все правила (имитация краша)
sudo nft flush ruleset
RULES=$(sudo nft list ruleset | wc -l)
if [ "$RULES" -eq 0 ]; then
    echo "OK: nftables flushed (crash simulated)"
fi

# Восстанавливаем через наш скрипт
sudo nft -f generated_ipv4.nft
sudo nft -f generated_ipv6.nft
RULES=$(sudo nft list ruleset | grep -c "accept")
if [ "$RULES" -gt 0 ]; then
    echo "PASS: nftables restored, $RULES rules active"
    PASS=$((PASS+1))
else
    echo "FAIL: nftables not restored"
    FAIL=$((FAIL+1))
fi

# ─── Сценарий 3: conntrackd sync проверка ───
echo ""
echo "--- Test 3: conntrackd sync after failover ---"

N1_SENT=$(sudo docker exec node1 conntrackd -C /etc/conntrackd/conntrackd.conf -s | grep "Pckts sent" | awk '{print $1}')
N2_SENT=$(sudo docker exec node2 conntrackd -C /etc/conntrackd/conntrackd.conf -s | grep "Pckts sent" | awk '{print $1}')

if [ "$N1_SENT" -gt 0 ] && [ "$N2_SENT" -gt 0 ]; then
    echo "PASS: conntrackd syncing after failover (node1=$N1_SENT node2=$N2_SENT pkts)"
    PASS=$((PASS+1))
else
    echo "FAIL: conntrackd not syncing"
    FAIL=$((FAIL+1))
fi

# ─── Итог ───
echo ""
echo "==============================="
echo "  Results: PASS=$PASS FAIL=$FAIL"
echo "==============================="

if [ "$FAIL" -eq 0 ]; then
    echo "  ALL TESTS PASSED"
    exit 0
else
    echo "  SOME TESTS FAILED"
    exit 1
fi
