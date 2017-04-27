import ovlib.verb

from ovlib import Dispatcher, ObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.types import Network
from ovirtsdk4.services import NetworkService
from ovirtsdk4.writers import NetworkWriter

@wrapper(writerClass=NetworkWriter, type_class=Network, service_class=NetworkService)
class NicWrapper(ObjectWrapper):
    pass

@dispatcher(object_name="network", service_root="nics", wrapper=NicWrapper)
class NicDispatcher(Dispatcher):
    pass


@command(NicDispatcher)
class List(ovlib.verb.List):
    pass


@command(NicDispatcher)
class XmlExport(ovlib.verb.XmlExport):
    pass


@command(NicDispatcher)
class Delete(ovlib.verb.Delete):
    pass


@command(NicDispatcher)
class Update(ovlib.verb.Update):
    param_name = 'Network'


@command(NicDispatcher)
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


@command(NicDispatcher, verb='assign')
class Assign(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-c", "--cluster", dest="cluster", help="Destination cluster")
        parser.add_option("-r", "--required", dest="required", help="Is required", default=False, action='store_true')


