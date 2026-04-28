from jinja2 import Environment, FileSystemLoader
import yaml

env = Environment(loader=FileSystemLoader('templates'))

with open('vars.yml') as f:
    data = yaml.safe_load(f)

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
