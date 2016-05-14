import ovlib.verb
from ovlib import ObjectContext, add_command
from ovirtsdk.infrastructure.brokers import Capabilities


class_ref = []


@add_command(class_ref)
class List(ovlib.verb.List):

    def execute(self, *args, **kwargs):
        for i in self.contenaire.list():
            if i.current:
                current = 'c'
            else:
                current = ' '
            yield "%s %d.%d %s " % (current, i.get_major(), i.get_minor(), i.get_id())

@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    pass


class CapabilitiesContext(ObjectContext):
    def __init__(self, object_name, api_attribute, commands):
        super(CapabilitiesContext, self).__init__(object_name, api_attribute, commands, Capabilities)
        self.allcapa = None

    def fill_parser(self, parser):
        parser.add_option("-i", "--id", dest="id", help="object ID")
        parser.add_option("-v", "--version", dest="version", help="capabilities version major.minor")
        parser.add_option("-c", "--current", dest="current", help="Get the current capabilities", default=False, action="store_true")

    # needed to work around bug https://bugzilla.redhat.com/show_bug.cgi?id=1326729
    def get(self, **kwargs):
        id = kwargs.pop('id', None)
        version = kwargs.pop('version', None)
        current = kwargs.pop('current', False)
        if self.allcapa is None:
            self.allcapa = self.execute("list")
        for i in self.allcapa:
            if current and i.current:
                return i
            elif id is not None and i.get_id() == id:
                return i
            elif version is not None and ("%d.%d" %(i.get_major(), i.get_minor())) == version:
                return i
        return None


oc = CapabilitiesContext(api_attribute = "capabilities", object_name = "capa", commands = class_ref)
