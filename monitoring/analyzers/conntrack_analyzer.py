#!/usr/bin/env python3
import subprocess
import re
from collections import defaultdict

# Example line:
# tcp  6 13 TIME_WAIT src=127.0.0.1 dst=127.0.0.1 sport=59090 dport=5000 ...
LINE_RE = re.compile(
    r'^(?P<proto>\w+)\s+\d+\s+\d+\s+'
    r'(?:(?P<state>[A-Z_]+)\s+)?'
    r'.*?\bdport=(?P<dport>\d+)'
)

def get_connections():
    try:
        result = subprocess.run(
            ['conntrack', '-L'],
            capture_output=True, text=True
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return []
    return result.stdout.splitlines()

def analyze_connections():
    lines = get_connections()
    if lines is None:
        return {'total': 0, 'by_protocol': {}, 'by_state': {},
                'by_dest_port': {}, 'message': 'conntrack not available'}

    stats = {
        'total': 0,
        'by_protocol': defaultdict(int),
        'by_state': defaultdict(int),
        'by_dest_port': defaultdict(int),
    }
    for line in lines:
        m = LINE_RE.match(line.strip())
        if not m:
            continue
        stats['total'] += 1
        stats['by_protocol'][m.group('proto')] += 1
        stats['by_state'][m.group('state') or 'NONE'] += 1
        stats['by_dest_port'][m.group('dport')] += 1

    stats['by_protocol'] = dict(stats['by_protocol'])
    stats['by_state'] = dict(stats['by_state'])
    stats['by_dest_port'] = dict(stats['by_dest_port'])
    return stats

if __name__ == "__main__":
    stats = analyze_connections()
    print("Connection Tracking Analysis:")
    print(f"Total connections: {stats['total']}")
    print("By protocol:", stats['by_protocol'])
    print("By state:", stats['by_state'])
