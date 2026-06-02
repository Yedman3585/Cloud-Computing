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
        return {
            'total': 0,
            'by_protocol': {},
            'by_state': {},
            'by_dest_port': {},
            'message': 'conntrack not available'
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
