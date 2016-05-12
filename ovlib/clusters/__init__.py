import ovlib.verb
from ovlib import Object_Context, add_command
from ovirtsdk.xml import params
from ovirtsdk.infrastructure.brokers import Cluster

class_ref = []

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
                memory_policy['transparent_hugepages'] = params.TransparentHugePages(enabled=memory_policy['transparent_hugepages']==True)
            kwargs['memory_policy'] = params.MemoryPolicy(**memory_policy)
        else:
            overcommit = kwargs.pop('overcommit', None)
            ballooning  = kwargs.pop('ballooning', None)
            transparent_hugepages = kwargs.pop('transparent_hugepages', None)
            if overcommit  is not None:
                pass

        self.broker = self.contenaire.add(params.Cluster(**kwargs))


@add_command(class_ref)
class Delete(ovlib.verb.Delete):
    pass


@add_command(class_ref)
class AddNetwork(ovlib.verb.Verb):
    verb = "addnet"

    def fill_parser(self, parser):
        parser.add_option("-i", "--netid", dest="netid", help="Network id")
        parser.add_option("-r", "--required", dest="required", help="Is required", default=False, action='store_true')

    def execute(self, *args, **kwargs):
        return self.broker.add()


content = Object_Context(api_attribute ="clusters", object_name ="cluster", commands = class_ref, broker_class=Cluster)
