import ovlib.verb
import create
import delete
import autoinstall
from ovlib import Object_Context, add_command

class_ref = []

@add_command(class_ref)
class List(ovlib.verb.List):
    verb = "list"

@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    verb = "export"

    def execute(self, *args, **kwargs):
        import sys
        print self.broker.hostdevices.export_(sys.stdout, 0)

        return super(XmlExport, self).execute(*args, **kwargs)


@add_command(class_ref)
class Start(ovlib.verb.XmlExport):
    verb = "start"

    def execute(self, *args, **kwargs):
        self.broker.start()


class_ref.append(create.Create)
class_ref.append(delete.Delete)
class_ref.append(autoinstall.Autoinstall)

content = Object_Context(api_attribute ="vms", object_name ="vm", commands = class_ref)
