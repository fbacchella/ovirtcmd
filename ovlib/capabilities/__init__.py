import ovlib.verb
from ovlib import Object_Context, add_command

class_ref = []

@add_command(class_ref)
class List(ovlib.verb.List):
    verb = "list"

@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    verb = "export"

    def execute(self, *args, **kwargs):
        #output = StringIO()
        #self.broker.export_(output, 0)
        #return output.getvalue()
        #for k in dir(self.broker):
        #    v = getattr(self.broker, k)
        #    print "%s %s" % (k, v)
        self.broker.current = None
        self.broker.features = None
        return super(XmlExport, self).execute(*args, **kwargs)


oc = Object_Context(api_attribute = "capabilities", object_name = "capa", commands = class_ref)
