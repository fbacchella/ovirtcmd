import ovlib.verb
from ovlib.dispatcher import dispatcher, command, Dispatcher
from ovlib.wrapper import ObjectWrapper, ListObjectWrapper, wrapper

from ovirtsdk4.types import Cluster, Cpu, Architecture, Network
from ovirtsdk4.writers import ClusterWriter, NetworkWriter
from ovirtsdk4.services import ClustersService, ClusterService, ClusterNetworksService, ClusterNetworkService


@wrapper(writer_class=NetworkWriter, type_class=Network, service_class=ClusterNetworkService, other_attributes=['vlan'])
class ClusterNetworkWrapper(ObjectWrapper):
    pass


@wrapper(service_class=ClusterNetworksService)
class ClusterNetworksWrapper(ListObjectWrapper):
    pass


@dispatcher(object_name="cluster", wrapper=ClusterNetworkWrapper, list_wrapper=ClusterNetworksWrapper)
class ClusterNetworkDispatcher(Dispatcher):
    pass


@wrapper(writer_class=ClusterWriter, type_class=Cluster, service_class=ClusterService, other_attributes=[])
class ClusterWrapper(ObjectWrapper):
    pass


@wrapper(service_class=ClustersService, service_root="clusters")
class ClustersWrapper(ListObjectWrapper):
    def creation_mapping(self, cpu_type=None, cpu=None, **kwargs):
        if cpu_type is not None and cpu is None:
            kwargs['cpu'] = Cpu(
                architecture = Architecture.X86_64,
                type = cpu_type,
            )
        return kwargs


@dispatcher(object_name="cluster", wrapper=ClusterWrapper, list_wrapper=ClustersWrapper)
class ClusterDispatcher(Dispatcher):
    pass


@command(ClusterDispatcher)
class ClusterList(ovlib.verb.List):
    pass


@command(ClusterDispatcher)
class ClusterExport(ovlib.verb.XmlExport):
    pass


@command(ClusterDispatcher)
class ClusterRemove(ovlib.verb.Remove):
    pass


@command(ClusterDispatcher)
class Create(ovlib.verb.Create):

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="New cluster name", default=None)

    def execute(self, *args, **kwargs):
        cpu_type = kwargs.pop('cpu_type', None)
        if cpu_type is not None:
            kwargs['cpu'] = params.CPU(id=cpu_type)

        datacenter = kwargs.pop('datacenter', None)
        if datacenter is not None:
            kwargs['data_center'] = self.get('datacenters', datacenter)

        memory_policy = kwargs.pop('memory_policy', None)
        if isinstance(memory_policy, dict):
            if 'overcommit' in memory_policy:
                memory_policy['overcommit'] = params.MemoryOverCommit(percent=memory_policy['overcommit'])
            if 'transparent_hugepages' in memory_policy:
                memory_policy['transparent_hugepages'] = params.TransparentHugePages(enabled=memory_policy['transparent_hugepages'] is True)
            kwargs['memory_policy'] = params.MemoryPolicy(**memory_policy)

        return self.contenaire.add(params.Cluster(**kwargs))


@command(ClusterDispatcher, verb="addnet")
class AddNetwork(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-i", "--netid", dest="netid", help="Network id")
        parser.add_option("-r", "--required", dest="required", help="Is required", default=False, action='store_true')

    def execute(self, *args, **kwargs):
        return self.object.add()


