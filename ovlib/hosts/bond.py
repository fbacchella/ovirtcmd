import ovlib.verb
import ipaddress

from ovlib import wrapper, ObjectWrapper, command
from ovlib.hosts import HostDispatcher

from ovirtsdk4.types import Bonding, Option, HostNic, NetworkAttachment
from ovirtsdk4.writers import BondingWriter, OptionWriter


@wrapper(writer_class=BondingWriter,
         type_class=Bonding)
class BondingWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=OptionWriter,
         type_class=Option)
class OptionWrapper(ObjectWrapper):
    pass


@command(HostDispatcher, verb='bond')
class Bond(ovlib.verb.Verb):

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-i", "--interface", dest="interfaces", help="Interface to add to bonding", default=[], action="append")
        parser.add_option("-m", "--mtu", dest="mtu", help="MTU for the interface", type=int)
        parser.add_option("-n", "--network", dest="networks", help="Network to bond", default=[], action="append")
        parser.add_option("-o", "--bond_option", dest="bond_options", action="store_variable", type="string", help="Used as '-o name value'")
        parser.add_option("-b", "--bond_name", dest="bond_name", default="bond0")

    def execute(self, bond_name='bond0', mtu=None, interfaces=[], bond_options={}, *args, **kwargs):
        nics = [HostNic(name=x, mtu=mtu) for x in interfaces]
        bond_options = [Option(name=x_y[0], value=x_y[1]) for x_y in iter(bond_options.items())]
        bonding = Bonding(slaves=nics, options=bond_options)
        bonded_if = HostNic(name=bond_name, bonding=bonding, mtu=mtu)
        bonded_na = []
        for i in self.api.wrap(self.object.network_attachments).list():
            old_na = self.api.wrap(i)
            new_na = NetworkAttachment()
            new_na.host_nic = bonded_if
            new_na.id = old_na.id
            bonded_na.append(new_na)
        self.object.setup_networks(
            modified_bonds=[bonded_if],
            modified_network_attachments=bonded_na,
        )
        self.object.commit_net_config()

        return True
