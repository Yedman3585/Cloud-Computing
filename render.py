import socket
import yaml
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates'))

with open('vars.yml') as f:
    data = yaml.safe_load(f)

resolved = []
for hostname in data.get('hosts', []):
	entry = {'name': hostname, 'ipv4': None, 'ipv6': None}
	try:
		for res in socket.getaddrinfo (hostname, None):
			if res[0].name == 'AF_INET' and not entry['ipv4']:
				entry['ipv4'] = res[4][0]
			if res[0].name == 'AF_INET6' and not entry['ipv6']:
				entry['ipv6'] = res[4][0]
	except socket.gaierror as e:
		print(f"WARNING: cna't resolved {hostname}: {e}")
	resolved.append(entry)
data['resolved_hosts'] = resolved 

template_v4 = env.get_template('nftables_ipv4.j2')
output_v4 = template_v4.render(data)

with open('generated_ipv4.nft', 'w') as f:
    f.write(output_v4)


template_v6 = env.get_template('nftables_ipv6.j2')
output_v6 = template_v6.render(data)

with open ('generated_ipv6.nft', 'w') as f:
	f.write(output_v6)

print("IPv4 rules:\n", output_v4)
print("\nIPv6 rules:\n", output_v6)
