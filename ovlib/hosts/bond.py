import ovlib.verb
from ovirtsdk.xml import params
import ipaddress

class Bond(ovlib.verb.Verb):
    verb = "bond"

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-i", "--interface", dest="interfaces", help="Interface to add to bonding", default=[], action="append")
        parser.add_option("-m", "--mtu", dest="mtu", help="MTU for the interface")
        parser.add_option("-n", "--network", dest="network", help="Network to bond", default='ovirtmgmt')
        parser.add_option("-o", "--bond_option", dest="bond_options", action="store_variable", type="string")
        parser.add_option("-b", "--bond_name", dest="bond_name", default="bond0")
        parser.add_option("-I", "--ip", dest="ip")
        parser.add_option("-G", "--gateway", dest="gateway")
        parser.add_option("-D", "--dhcp", dest="dhcp", action="store_true")

    def execute(self, *args, **kwargs):
        mtu = int(kwargs.pop('mtu', None))
        nics = []
        for if_name in kwargs['interfaces']:
            nic = params.HostNIC(name=if_name,
                                 network=params.Network(),
                                 boot_protocol='none',
                                 ip=params.IP(address='*', netmask= '*', gateway = ''))
            if mtu is not None:
                nic.set_mtu(mtu)
            nics.append(nic)

        bond_options = []
        bond_options_dict = kwargs.pop('bond_options', {})
        for (option_name, option_value) in bond_options_dict.items():
            bond_option = params.Option(name=option_name, value=option_value)
            bond_options.append(bond_option)

        bonding = params.Bonding(
            slaves=params.Slaves(host_nic=nics),
            options=params.Options(
                option=bond_options
            )
        )

        ip = kwargs.pop('ip', None)
        gateway = kwargs.pop('gateway', None)
        if ip is not None:
            ip = unicode(ip)
            ip_addr = ipaddress.ip_address(ip.split('/')[0])
            ip_net = ipaddress.ip_network(ip, strict=False)
            kwargs['ip'] = params.IP(address=str(ip_addr),
                                     netmask=str(ip_net).split('/')[0])
            if gateway is not None:
                kwargs['ip'].set_gateway(gateway)
            kwargs['boot_protocol'] = 'static'
        elif kwargs.pop('dhcp', False):
            kwargs['boot_protocol'] = 'dhcp'
            kwargs['ip'] = params.IP()

        bonded_if = params.HostNIC(network=params.Network(name=kwargs['network']),
                                           name=kwargs['bond_name'],
                                           boot_protocol=kwargs['boot_protocol'],
                                           ip=kwargs['ip'],
                                           override_configuration=1,
                                           bonding=bonding)
        if mtu is not None:
            bonded_if.set_mtu(mtu)
        return self.broker.setupnetworks(params.Action(force = 1,
                                                check_connectivity = 1,
                                                host_nics = params.HostNics(host_nic = [bonded_if])))
