import ovlib.verb
import create
import delete
import autoinstall
import urllib
from ovlib import Object_Context, add_command
from ovirtsdk.infrastructure.brokers import VM


class_ref = []

@add_command(class_ref)
class List(ovlib.verb.Statistics):
    pass


@add_command(class_ref)
class List(ovlib.verb.List):
    pass


@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    pass


@add_command(class_ref)
class Start(ovlib.verb.Verb):
    verb = "start"

    def execute(self, *args, **kwargs):
        self.broker.start()


@add_command(class_ref)
class Start(ovlib.verb.Verb):
    verb = "stop"

    def execute(self, *args, **kwargs):
        self.broker.stop()


@add_command(class_ref)
class Start(ovlib.verb.XmlExport):
    verb = "ticket"

    def execute(self, *args, **kwargs):
        ticket = self.broker.ticket().ticket
        console_info = {
            'type': self.broker.display.type_,
            'address': self.broker.display.address,
            'password': ticket.value,
            'port': self.broker.display.port,
            'secure_port': self.broker.display.secure_port,
            'title': self.broker.name + ":%d"
        }
        for (k,v) in console_info.items():
            console_info[k] = urllib.quote(str(v))
        if console_info['type'] == 'spice':
            url = "spice://{address}:{port}/?password={password}&tls-port={secure_port}".format(**console_info)
        elif console_info['type'] == 'vnc':
            url = "vnc://{address}:{port}".format(**console_info)

        return url


class_ref.append(create.Create)
class_ref.append(delete.Delete)
class_ref.append(autoinstall.Autoinstall)

content = Object_Context(api_attribute ="vms", object_name ="vm", commands = class_ref, broker_class=VM)
