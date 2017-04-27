import ovlib.verb
from ovlib import Dispatcher, command
from ovirtsdk.infrastructure.brokers import Template

class_ref = []

@command(class_ref)
class List(ovlib.verb.List):
    pass


oc = Dispatcher(api_attribute="templates", object_name="template", commands=class_ref, broker_class=Template)
