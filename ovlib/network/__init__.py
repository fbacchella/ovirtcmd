from numbers import Number

import ovlib.verb
from ovlib.dispatcher import dispatcher, command, Dispatcher
from ovlib.wrapper import ObjectWrapper, ListObjectWrapper, wrapper

from ovirtsdk4.types import Network, Vlan
from ovirtsdk4.services import NetworkService, NetworksService
from ovirtsdk4.writers import NetworkWriter, VlanWriter


@wrapper(writer_class=VlanWriter, type_class=Vlan)
class VlanWrapper(ObjectWrapper):
    pass


@wrapper(service_class=NetworksService, service_root="networks")
class NetworksWrapper(ListObjectWrapper):

    def creation_mapping(self, vlan=None, **kwargs):
        if vlan is not None:
            if isinstance(vlan, str):
                kwargs['vlan'] = Vlan(id=vlan)
            elif isinstance(vlan, Number):
                kwargs['vlan'] = Vlan(id='%d' % vlan)
            else:
                kwargs['vlan'] = vlan
        return kwargs


@wrapper(writer_class=NetworkWriter, type_class=Network, service_class=NetworkService, other_attributes=['vlan', 'mtu'],
         name_type_mapping={'network': Network})
class NetworkWrapper(ObjectWrapper):
    pass


@dispatcher(object_name="network", wrapper=NetworkWrapper, list_wrapper=NetworksWrapper)
class NetworkDispatcher(Dispatcher):
    pass


@command(NetworkDispatcher)
class List(ovlib.verb.List):
    pass


@command(NetworkDispatcher)
class XmlExport(ovlib.verb.XmlExport):
    pass


@command(NetworkDispatcher)
class Remove(ovlib.verb.Remove):
    pass


@command(NetworkDispatcher)
class Update(ovlib.verb.Update):
    param_name = 'Network'


@command(NetworkDispatcher)
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


@command(NetworkDispatcher, verb='assign')
class Assign(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-c", "--cluster", dest="cluster", help="Destination cluster")
        parser.add_option("-r", "--required", dest="required", help="Is required", default=False, action='store_true')


