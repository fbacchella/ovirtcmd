import ovlib.verb
from ovlib import Object_Context, add_command
from ovirtsdk.xml import params
from ovirtsdk.infrastructure.brokers import DataCenter

class_ref = []

@add_command(class_ref)
class List(ovlib.verb.List):
    verb = "list"


@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    verb = "export"


@add_command(class_ref)
class Attach(ovlib.verb.Verb):
    verb = "attach"

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="Domain name", default=None)
        parser.add_option("-i", "--id", dest="id", help="Domain id", default=None)

    def execute(self, *args, **kwargs):
        sd = self.api.storagedomains.get(**kwargs)
        self.broker.storagedomains.add(params.StorageDomain(id=sd.id))


@add_command(class_ref)
class Create(ovlib.verb.Verb):
    verb = "create"

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="New datecenter name", default=None)

    def validate(self):
        return True

    def execute(self, *args, **kwargs):
        mac_pool_name = kwargs.pop('mac_pool_name', None)
        if mac_pool_name is not None:
            kwargs['mac_pool'] = self.api.macpools.get(name=mac_pool_name)

        self.broker = self.contenaire.add(params.DataCenter(**kwargs))


@add_command(class_ref)
class Delete(ovlib.verb.Verb):
    verb = "delete"

    def fill_parser(self, parser):
        parser.add_option("-f", "--force", dest="force", help="Force", default=False, action='store_true')


    def execute(self, *args, **kwargs):
        action_params = params.Action(
            # force a True/False content
            force= kwargs == True,
        )
        return self.broker.delete(action_params)


oc = Object_Context(api_attribute = "datacenters", object_name = "datacenter", commands = class_ref, broker_class=DataCenter)
