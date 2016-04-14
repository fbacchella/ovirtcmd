import ovlib.verb
from ovlib import Object_Context, add_command
from ovirtsdk.xml import params

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

oc = Object_Context(api_attribute = "datacenters", object_name = "datacenter", commands = class_ref)
