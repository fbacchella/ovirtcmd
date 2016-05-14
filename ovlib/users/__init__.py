import ovlib.verb
from ovlib import ObjectContext, add_command
from ovirtsdk.infrastructure.brokers import User


class_ref = []


@add_command(class_ref)
class List(ovlib.verb.List):
    pass


@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    pass


oc = ObjectContext(api_attribute="users", object_name="user", commands=class_ref, broker_class=User)
