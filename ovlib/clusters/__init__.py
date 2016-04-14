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
class Delete(ovlib.verb.Verb):
    verb = "delete"

    def execute(self, *args, **kwargs):
        self.broker.delete()

content = Object_Context(api_attribute ="clusters", object_name ="cluster", commands = class_ref)
