class_ref = []
import ovlib.verb
from ovlib import Object_Context, add_command
from ovirtsdk.xml import params
from ovirtsdk.infrastructure.brokers import Network

@add_command(class_ref)
class List(ovlib.verb.List):
    verb = "list"


@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    verb = "export"


@add_command(class_ref)
class Delete(ovlib.verb.Verb):
    verb = "delete"

    def execute(self, *args, **kwargs):
        self.broker.delete()


@add_command(class_ref)
class Create(ovlib.verb.Verb):
    verb = "create"

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="Network name")
        parser.add_option("-d", "--datacenter", dest="datacenter", help="Datacenter destination")
        parser.add_option("-m", "--mtu", dest="mtu", help="MTU for the network", type=int)
        parser.add_option("-v", "--vlan", dest="vlan", help="VLAN number for the network", type=int)
        parser.add_option("-s", "--stp", dest="stp", help="Activate STP", default=False, action='store_true')
        parser.add_option("-V", "--VM", dest="canVM", help="is a VM network", default=True)

    def validate(self):
        return True

    def execute(self, *args, **kwargs):
        kwargs['data_center'] = self.get('datacenters', kwargs.pop('datacenter', 'Default'))
        vlan = kwargs.pop('vlan', None)
        if vlan is not None:
            kwargs['vlan'] = params.VLAN(id=vlan)
        if kwargs.pop('canVM', True) == True:
            kwargs['usages'] = params.Usages(kwargs.pop('usages', ['vm']))
        else:
            kwargs['usages'] = params.Usages(kwargs.pop('usages', []))
        new_network = params.Network(**kwargs)
        return self.contenaire.add(new_network)


@add_command(class_ref)
class Assign(ovlib.verb.Verb):
    verb = "assign"

    def fill_parser(self, parser):
        parser.add_option("-c", "--cluster", dest="cluster", help="Destination cluster")
        parser.add_option("-r", "--required", dest="required", help="Is required", default=False, action='store_true')

content = Object_Context(api_attribute ="networks", object_name ="network", commands = class_ref, broker_class=Network)
