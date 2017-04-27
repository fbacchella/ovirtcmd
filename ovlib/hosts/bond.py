import ovlib.verb
import ipaddress

class Bond(ovlib.verb.Verb):
    verb = "bond"

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-i", "--interface", dest="interfaces", help="Interface to add to bonding", default=[], action="append")
        parser.add_option("-m", "--mtu", dest="mtu", help="MTU for the interface", type=int)
        parser.add_option("-n", "--network", dest="networks", help="Network to bond", default=[], action="append")
        parser.add_option("-o", "--bond_option", dest="bond_options", action="store_variable", type="string", help="Used as '-o name value'")
        parser.add_option("-b", "--bond_name", dest="bond_name", default="bond0")

    def execute(self, *args, **kwargs):
        # build the bonded interfaces
        bond_name = kwargs['bond_name']

        mtu = kwargs.pop('mtu', None)
        nics = map(lambda x: params.HostNIC(name=x, mtu=mtu), kwargs.pop('interfaces', []))
        bond_options = map(lambda (x, y): params.Option(name=x, value=y), kwargs.pop('bond_options', {}).iteritems() )
        bonding = params.Bonding(
            slaves=params.Slaves(host_nic=nics),
            options=params.Options(
                option=bond_options
            )
        )
        bonded_if = params.HostNIC(name=bond_name, bonding=bonding, mtu=mtu)

        # resolves the network that needs to be moved to this interface
        # IP configuration is kept if network already exists
        old_net_attachement = {}
        networks_by_name = {}
        for i in self.broker.networkattachments.list():
            net = self.get(self.api.networks, i.network.id)
            old_net_attachement[net.name] = {'id': i.id, 'ips': i.ip_address_assignments}
            networks_by_name[net.name] = net.id

        bonded_networks_list = kwargs.pop('networks', [])
        if len(bonded_networks_list) == 0:
            bonded_networks_list = ['ovirtmgmt']

        bonded_networks = []
        bond_nic = params.HostNIC(name=bond_name)
        for i in bonded_networks_list:
            attachement_kwargs = {'host_nic':  bond_nic }
            if i in networks_by_name:
                net_id = networks_by_name[i]
            else:
                host_cluster = self.get(self.api.clusters, self.broker.cluster.id)
                net_id = self.get(host_cluster.networks, i).id
            attachement_kwargs['network'] = params.Network(id=net_id)
            if i in old_net_attachement:
                attachement_kwargs['id'] = old_net_attachement[i]['id']
                attachement_kwargs['ip_address_assignments'] = old_net_attachement[i]['ips']
            bonded_networks.append(params.NetworkAttachment(**attachement_kwargs))

        return self.broker.setupnetworks(params.Action(modified_bonds=params.HostNics(host_nic=[bonded_if]),
                                                       modified_network_attachments=params.NetworkAttachments(network_attachment=bonded_networks),
                                                       )
                                         )
