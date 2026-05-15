#!/usr/bin/env python3

import subprocess
import json
from collections import defaultdict

def get_connections():
    try:
        result = subprocess.run(
            ['conntrack', '-L', '-o', 'json'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except FileNotFoundError:
        print("conntrack not installed (firewall not running yet)")
        return None
    
    return []

def analyze_connections():
    connections = get_connections()
    
    if connections is None:
        print("Demo mode: showing sample data")
        return {
            'total': 156,
            'by_protocol': {'tcp': 142, 'udp': 14},
            'by_state': {'ESTABLISHED': 89, 'TIME_WAIT': 52, 'CLOSE_WAIT': 15},
            'by_dest_port': {443: 67, 80: 45, 22: 23}
        }
    
    stats = {
        'total': len(connections),
        'by_protocol': defaultdict(int),
        'by_state': defaultdict(int),
        'by_dest_port': defaultdict(int)
    }
    
    for conn in connections:
        proto = conn.get('proto', 'unknown')
        stats['by_protocol'][proto] += 1
        
        state = conn.get('state', 'unknown')
        stats['by_state'][state] += 1
        
        if 'dst' in conn and 'port' in conn['dst']:
            stats['by_dest_port'][conn['dst']['port']] += 1
    
    return stats

if __name__ == "__main__":
    print("Connection Tracking Analysis:")
    stats = analyze_connections()
    
    print(f"Total connections: {stats['total']}")
    print("\nBy protocol:")
    for proto, count in stats['by_protocol'].items():
        print(f"   {proto}: {count}")
    
    print("\nBy state:")
    for state, count in stats['by_state'].items():
        print(f"   {state}: {count}")
    
    print("\nTop destination ports:")
    top_ports = sorted(stats['by_dest_port'].items(), key=lambda x: x[1], reverse=True)[:5]
    for port, count in top_ports:
        print(f"   Port {port}: {count} connections")
