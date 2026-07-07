#!/bin/bash
set -e

echo "[client-entrypoint] Starting: ${HOSTNAME}"

# Add static route to backend network via the frontend VIP.
# This ensures traffic from clients transits the firewall cluster rather
# than going directly via the bridge gateway. The route is re-applied on
# every container start so it survives docker compose recreate cycles.
BACKEND_NET="${BACKEND_SUBNET:-172.22.0.0/24}"
FRONTEND_VIP="${FRONTEND_VIP:-172.21.0.100}"

if ip route show | grep -q "$BACKEND_NET"; then
    echo "[client-entrypoint] Route to $BACKEND_NET already present"
else
    echo "[client-entrypoint] Adding route: $BACKEND_NET via $FRONTEND_VIP"
    ip route replace "$BACKEND_NET" via "$FRONTEND_VIP" 2>/dev/null || true
fi

exec "$@"