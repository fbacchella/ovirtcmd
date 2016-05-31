class_ref = []
import ovlib.verb
from ovlib import ObjectContext, add_command
from ovirtsdk.xml import params
from ovirtsdk.infrastructure.brokers import Network, DataCenterNetwork


@add_command(class_ref)
class List(ovlib.verb.List):
    pass


@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    pass


@add_command(class_ref)
class Delete(ovlib.verb.Delete):
    pass


@add_command(class_ref)
class Update(ovlib.verb.Update):
    param_name = 'Network'


@add_command(class_ref)
class Create(ovlib.verb.Create):

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="Network name")
        parser.add_option("-d", "--datacenter", dest="datacenter", help="Datacenter destination")
        parser.add_option("-c", "--cluster", dest="clusters", help="cluster to be attached", default=[], action='append')
        parser.add_option("-m", "--mtu", dest="mtu", help="MTU for the network", type=int)
        parser.add_option("-v", "--vlan", dest="vlan", help="VLAN number for the network", type=int)
        parser.add_option("-s", "--stp", dest="stp", help="Activate STP", default=False, action='store_true')
        parser.add_option("-V", "--VM", dest="canVM", help="is a VM network", default=True)

    def execute(self, *args, **kwargs):
        kwargs['data_center'] = self.get('datacenters', kwargs.pop('datacenter', None))
        required = kwargs.pop('required', False)

        clusters = []
        for cluster in kwargs.pop('clusters', []):
            clusters.append(self.get(kwargs['data_center'].clusters, cluster))

        vlan = kwargs.pop('vlan', None)
        if vlan is not None:
            kwargs['vlan'] = params.VLAN(id=vlan)
        if kwargs.pop('canVM', True) is True:
            kwargs['usages'] = params.Usages(kwargs.pop('usages', ['vm']))
        else:
            kwargs['usages'] = params.Usages(kwargs.pop('usages', []))
        new_network = self.contenaire.add(params.Network(**kwargs))

        for cluster in clusters:
            cluster.networks.add(params.Network(id=new_network.id, required=required))


@add_command(class_ref)
class Assign(ovlib.verb.Verb):
    verb = "assign"

    def fill_parser(self, parser):
        parser.add_option("-c", "--cluster", dest="cluster", help="Destination cluster")
        parser.add_option("-r", "--required", dest="required", help="Is required", default=False, action='store_true')


oc = ObjectContext(api_attribute="networks", object_name="network", commands=class_ref, broker_class=[Network, DataCenterNetwork])
