import ovlib
from ovlib.eventslib import event_waiter, EventsCode

mac_pool = context.macpools.get("Default")

try:
    dc = context.datacenters.get(host_name)
except ovlib.OVLibErrorNotFound:
    dc = context.datacenters.add(data_center={'name': host_name, 'local': True, 'storage_format': 'V4', 'mac_pool': mac_pool})

dc_net_vlan = set()
dc_nets_id = set()

for net in dc.networks.list():
    if net.vlan is not None:
        dc_net_vlan.add(net.vlan.id)
    if net.name == "ovirtmgmt" and net.mtu != 9000:
        net.update(network={'mtu': 9000})
    dc_nets_id.add(net.id)

try:
    cluster = context.clusters.get(host_name)
except ovlib.OVLibErrorNotFound:
    cluster = context.clusters.add(cluster={'name': host_name, 'cpu': {'type': 'AMD Opteron G3'}, 'data_center': dc, 'mac_pool': mac_pool})

futurs = []
for (name, vlan) in (("VLAN1", 1), ("VLAN2", 2), ('VLAN3', 3)):
    if not vlan in dc_net_vlan:
        new_net = context.networks.add(network={'name': name, 'vlan': {'id': "%d" % vlan} , 'mtu': 9000, 'data_center': dc, 'usages': ['VM'],
                                          }, wait= False)
        futurs.append(new_net)

for f in futurs:
    network = f.wait()
    dc_nets_id.add(network.id)

cluster_nets_id = set()

for net in cluster.networks.list():
    cluster_nets_id.add(net.id)

futurs = []
for missing in dc_nets_id - cluster_nets_id:
    futurs.append(cluster.networks.add(network={'id': missing, 'required': False}, wait=False))

try:
    host = context.hosts.get(host_name)
except ovlib.OVLibErrorNotFound:
    events_returned = []
    waiting_events = [EventsCode.VDS_DETECTED]
    with event_waiter(context, "host.name=%s" % host_name, events_returned, verbose=True, break_on=waiting_events):
        host = context.hosts.add(host={
            'name': host_name, 'address': host_name,
            'cluster': cluster,
            'override_iptables': False,
            'ssh': {'authentication_method': 'PUBLICKEY'},
            'power_management': {
                'enabled': True,
                'kdump_detection': False,
                'pm_proxies': [{'type': 'CLUSTER'}, {'type': 'DC'}, {'type': 'OTHER_DC'}]
            }
        }, wait=True)

host.refresh()

storages = host.storage.list()
if len(storages) == 1 and storages[0].type.name == 'FCP' and storages[0].type.name == 'FCP' and storages[0].logical_units[0].status.name == 'FREE':
    lu = {'id': storages[0].id}
    vg = {'logical_units': [lu]}
    storage = {'type': 'FCP', 'volume_group': vg}
    sd = {'name': host_name, 'type': 'DATA', 'data_center': dc, 'host': host, 'storage': storage}
    sd = context.storagedomains.add(storage_domain={'name': host_name, 'type': 'DATA', 'data_center': dc, 'host': host, 'storage': storage})
else:
    sd = context.storagedomains.get(host_name)

events_returned = []
waiting_events = [EventsCode.VDS_DETECTED]
if(host.status.name != 'UP'):
    with event_waiter(context, "host.name=%s" % host_name, events_returned, verbose=True, break_on=waiting_events):
        print(events_returned)

if sd.status is not None and sd.status.value == 'unattached':
    futurs.append(dc.storage_domains.add(storage_domain=sd, wait=False))

if host.hardware_information.product_name is not None and len(list(host.fence_agents.list())) == 0:
    fence_agent_type={'ProLiant DL185 G5': 'ipmilan'}[host.hardware_information.product_name]
    futurs.append(host.fence_agents.add(agent={'address': host_name + "-ilo", 'username': 'admin', 'password': 'password', 'type': fence_agent_type, 'order': 1}, wait=False))

for f in futurs:
    pf.wait()

