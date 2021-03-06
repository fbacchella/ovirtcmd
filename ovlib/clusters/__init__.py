import ovlib.verb
from ovlib.dispatcher import dispatcher, command, Dispatcher
from ovlib.wrapper import ObjectWrapper, ListObjectWrapper, wrapper
from ovlib.network import NetworkWrapper, NetworksWrapper

from ovirtsdk4.types import Cluster, Cpu, Architecture
from ovirtsdk4.writers import ClusterWriter
from ovirtsdk4.services import ClustersService, ClusterService, ClusterNetworksService, ClusterNetworkService


@wrapper(service_class=ClusterNetworkService)
class ClusterNetworkWrapper(NetworkWrapper):
    pass


@wrapper(service_class=ClusterNetworksService)
class ClusterNetworksWrapper(NetworksWrapper):
    pass


@dispatcher(object_name="cluster", wrapper=ClusterNetworkWrapper, list_wrapper=ClusterNetworksWrapper)
class ClusterNetworkDispatcher(Dispatcher):
    pass


@wrapper(writer_class=ClusterWriter, type_class=Cluster, service_class=ClusterService, other_attributes=['data_center'],
         name_type_mapping={'cpu': Cpu})
class ClusterWrapper(ObjectWrapper):
    pass


@wrapper(service_class=ClustersService, service_root="clusters",
         name_type_mapping={'cluster': Cluster})
class ClustersWrapper(ListObjectWrapper):
    pass


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


