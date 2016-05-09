import time
import ovlib.verb
from ovlib import Object_Context, add_command
from ovirtsdk.xml import params
from ovirtsdk.infrastructure.errors import RequestError
from ovirtsdk.infrastructure.brokers import Host

import create
import bond

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
        if self.broker.status.state != "maintenance":
            self.broker.deactivate()
            self.wait_for("maintenance")
        self.broker.delete()

@add_command(class_ref)
class Reboot(ovlib.verb.Verb):
    """Broken, do not use"""
    verb = "reboot"

    def execute(self, *args, **kwargs):
        if self.broker.status.state != "maintenance":
            self.broker.deactivate()
            self.wait_for("maintenance")
        self.broker.fence(params.Action(fence_type='restart'))
        # needs to be activated before checking for up, otherwise it will return maintenance forever
        doactivate=True
        while doactivate:
            try:
                self.broker.activate()
            except RequestError as e:
                print e.detail
                time.sleep(5)
        self.wait_for("up")
        return True

class_ref.append(create.Create)
class_ref.append(bond.Bond)

content = Object_Context(api_attribute ="hosts", object_name ="host", commands = class_ref, broker_class=Host)
