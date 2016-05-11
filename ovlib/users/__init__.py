class_ref = []
import ovlib.verb
from ovlib import Object_Context, add_command
from ovirtsdk.xml import params
from ovirtsdk.infrastructure.brokers import User

@add_command(class_ref)
class List(ovlib.verb.List):
    verb = "list"

@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    verb = "export"

content = Object_Context(api_attribute ="users", object_name ="user", commands = class_ref, broker_class=User)
