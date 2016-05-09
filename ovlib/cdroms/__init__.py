import ovlib.verb
from ovlib import Object_Context, add_command
from ovirtsdk.infrastructure.brokers import VMCdRoms

class_ref = []

@add_command(class_ref)
class List(ovlib.verb.List):
    verb = "list"

@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    verb = "export"

oc = Object_Context(api_attribute = "cdroms", object_name = "cdrom", commands = class_ref, broker_class=VMCdRoms)
