#!/bin/bash

NODE1="node1"
NODE2="node2"

echo "=== conntrackd sync check ==="
echo ""

# Получаем статистику с node1
echo "--- Node1 stats ---"
sudo docker exec $NODE1 conntrackd -C /etc/conntrackd/conntrackd.conf -s

echo ""
echo "--- Node2 stats ---"
sudo docker exec $NODE2 conntrackd -C /etc/conntrackd/conntrackd.conf -s

echo ""
echo "--- Comparison ---"

# Считаем пакеты
N1_SENT=$(sudo docker exec $NODE1 conntrackd -C /etc/conntrackd/conntrackd.conf -s | grep "Pckts sent" | awk '{print $1}')
N1_RECV=$(sudo docker exec $NODE1 conntrackd -C /etc/conntrackd/conntrackd.conf -s | grep "Pckts sent" | awk '{print $4}')

N2_SENT=$(sudo docker exec $NODE2 conntrackd -C /etc/conntrackd/conntrackd.conf -s | grep "Pckts sent" | awk '{print $1}')
N2_RECV=$(sudo docker exec $NODE2 conntrackd -C /etc/conntrackd/conntrackd.conf -s | grep "Pckts sent" | awk '{print $4}')

echo "Node1: sent=$N1_SENT recv=$N1_RECV"
echo "Node2: sent=$N2_SENT recv=$N2_RECV"

# Проверяем что пакеты идут в обе стороны
if [ "$N1_SENT" -gt 0 ] && [ "$N2_SENT" -gt 0 ]; then
    echo ""
    echo "OK: nodes are syncing with each other"
    exit 0
else
    echo ""
    echo "WARN: sync may not be working"
    exit 1
fi
