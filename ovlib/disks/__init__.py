import ovlib.verb
from ovlib import Object_Context, add_command
from ovirtsdk.infrastructure.brokers import Disk

class_ref = []

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

        return True


ce = Object_Context(api_attribute = "disks", object_name = "disk", commands = class_ref, broker_class=Disk)
