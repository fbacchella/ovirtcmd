import ovlib.verb
from ovirtsdk.xml import params
import ipaddress

class Bond(ovlib.verb.Verb):
    verb = "bond"

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-i", "--interface", dest="interfaces", help="Interface to add to bonding", default=[], action="append")
        parser.add_option("-m", "--mtu", dest="mtu", help="MTU for the interface", type=int)
        parser.add_option("-n", "--network", dest="network", help="Network to bond", default='ovirtmgmt')
        parser.add_option("-o", "--bond_option", dest="bond_options", action="store_variable", type="string")
        parser.add_option("-b", "--bond_name", dest="bond_name", default="bond0")
        parser.add_option("-I", "--ip", dest="ip")
        parser.add_option("-G", "--gateway", dest="gateway")
        parser.add_option("-D", "--dhcp", dest="dhcp", action="store_true", default=True, help="configure this interface using DHCP")
        parser.add_option("-K", "--keep", dest="keep", help="Keep IP information for this interface")

    def execute(self, *args, **kwargs):
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

        ip = kwargs.pop('ip', None)
        gateway = kwargs.pop('gateway', None)
        keep = kwargs.pop('keep', None)
        dhcp = kwargs.pop('dhcp', False)
        if keep is not None:
            old_ip_nic = self.broker.nics.get(name=keep)
            ip_assignment = old_ip_nic.networkattachments.list()[0].ip_address_assignments
        elif ip is not None:
            ip = unicode(ip)
            ip_addr = ipaddress.ip_address(ip.split('/')[0])
            ip_net = ipaddress.ip_network(ip, strict=False)
            ip_conf = params.IP(address=str(ip_addr),
                                netmask=str(ip_net).split('/')[0])
            if gateway is not None:
                ip_conf.set_gateway(gateway)
            ip_assignment = params.IpAddressAssignments([params.IpAddressAssignment(assignment_method="static", ip=ip_conf)])
        elif dhcp == True:
            ip_assignment = params.IpAddressAssignments([params.IpAddressAssignment(assignment_method="dhcp", ip=params.IP())])

        bonded_network = params.NetworkAttachment(network=params.Network(name=kwargs['network']),
                                                  host_nic=params.HostNIC(name=bond_name),
                                                  ip_address_assignments=ip_assignment)

        return self.broker.setupnetworks(params.Action(modified_bonds = params.HostNics(host_nic = [bonded_if]),
                                                       modified_network_attachments = params.NetworkAttachments(network_attachment=[bonded_network]),
                                                       )
                                         )
