# This script can be used to create a datacenter for a single host using a non shared storage.
# Create a file that store the power management settings like:
# power_management:
#   address: ${name}-bmc.domain.com
#   username: admin
#   password: admin
#   kdump_detection: False
#   type: ipmilan
# and then launch with:
# ./ovcmd -c ovirt.ini eval -v name hostname -v cpu cputype -e bmc.yaml noshared.py

import re

dc = context.datacenter(name=name)
if dc is None:
    print "creating datacenter"
    dc = context.datacenter().create(name=name, local=True, storage_format="v3")

cluster = context.cluster(name=name)
if cluster is None:
    print "creating cluster"
    cluster = context.cluster().create(name=name, cpu_type=cpu, datacenter=dc,
                         memory_policy={'guaranteed': True, 'overcommit': 100, 'transparent_hugepages': False},
                         ballooning_enabled=True)

network = dc.get('networks', 'ovirtmgmt')
if network.broker.mtu != 9000:
    network.broker.mtu = 9000
    network.update()

host = context.host(name=name)
if host is None:
    print "creating host"
    host = context.host().create(name=name, address=name + ".prod.exalead.com",
                          cluster=cluster,
                          override_iptables=False,
                          reboot_after_installation=True,
                          power_management=power_management)

else:

    sd = dc.broker.storagedomains.get(name)
    if sd is None:
        print "creating storage domain"
        sd = context.storage().create(domain_type="data",
                                      name=name,
                                      host=host,
                                      type='localfs',
                                      path='/data/ovirt/data')
    bondre = re.compile("bond\d")
    nics = []
    bonded = False
    for nic in host.broker.nics.list():
        if bondre.match(nic.name):
            bonded = True
            break
        else:
            nics.append(nic.name)

    if not bonded:
        print "bonding interfaces"
        host.bond(bond_name='bond0',
            mtu=9000,
            bond_options={
                          'mode': '4',
                          'xmit_hash_policy': 'layer2+3',
                          'miimon': '100'},
            interfaces=nics,
        )
