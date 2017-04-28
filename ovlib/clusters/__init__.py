import ovlib.verb
from ovlib import Dispatcher, ObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.types import Cluster
from ovirtsdk4.writers import ClusterWriter
from ovirtsdk4.services import ClustersService

@wrapper(writerClass=ClusterWriter, type_class=Cluster, service_class=ClustersService)
class ClusterWrapper(ObjectWrapper):
    pass

@dispatcher(service_root="clusters", object_name="cluster", wrapper=ClusterWrapper)
class ClusterDispatcher(Dispatcher):
    pass

@command(ClusterDispatcher)
class List(ovlib.verb.List):
    pass


@command(ClusterDispatcher)
class XmlExport(ovlib.verb.XmlExport):
    pass


@command(ClusterDispatcher)
class Delete(ovlib.verb.Delete):
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


@command(ClusterDispatcher)
class Delete(ovlib.verb.Delete):
    pass


@command(ClusterDispatcher)
class AddNetwork(ovlib.verb.Verb):
    verb = "addnet"

    def fill_parser(self, parser):
        parser.add_option("-i", "--netid", dest="netid", help="Network id")
        parser.add_option("-r", "--required", dest="required", help="Is required", default=False, action='store_true')

    def execute(self, *args, **kwargs):
        return self.broker.add()


