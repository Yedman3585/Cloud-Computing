from jinja2 import Environment, FileSystemLoader
import yaml

env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('nftables_ipv4.j2')

with open('vars.yml') as f:
    data = yaml.safe_load(f)

output = template.render(data)

with open('generated.nft', 'w') as f:
    f.write(output)

print(output)
