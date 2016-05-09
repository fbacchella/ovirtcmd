import ovlib.verb
from ovlib import Object_Context, add_command
from ovirtsdk.infrastructure.brokers import Template

class_ref = []

@add_command(class_ref)
class List(ovlib.verb.List):
    verb = "list"

oc = Object_Context(api_attribute = "templates", object_name = "template", commands = class_ref, broker_class=Template)
