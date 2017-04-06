import ovlib.verb
import create
import delete
import autoinstall
import urllib
from ovlib import ObjectContext, add_command
from ovirtsdk.infrastructure.brokers import VM


class_ref = []


@add_command(class_ref)
class Statistics(ovlib.verb.Statistics):
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
class Stop(ovlib.verb.Verb):
    verb = "stop"

    def execute(self, *args, **kwargs):
        self.broker.stop()


@add_command(class_ref)
class Ticket(ovlib.verb.Verb):
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

@add_command(class_ref)
class Console(ovlib.verb.Verb):
    verb = "console"

    def fill_parser(self, parser):
        parser.add_option("-c", "--c", dest="console", help="Console number", default=1, type=int)

    def execute(self, *args, **kwargs):
        return self._export(self.broker.graphicsconsoles.list()[kwargs['console'] - 1])

class_ref.append(create.Create)
class_ref.append(delete.Delete)
class_ref.append(autoinstall.Autoinstall)

content = ObjectContext(api_attribute="vms", object_name="vm", commands=class_ref, broker_class=VM)
