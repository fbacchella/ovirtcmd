import ovlib.verb
import create
import delete
import autoinstall
import urllib
import tempfile
import os
from ovlib import ObjectContext, add_command

from ovirtsdk4.types import Vm, GraphicsType, VmStatus
from ovirtsdk4.writers import VmWriter, GraphicsConsoleWriter

Vm.writer = VmWriter

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

    def fill_parser(self, parser):
        parser.add_option("-c", "--console", dest="console", help="Launch a console", default=False, action="store_true")
        parser.add_option("-C", "--console_device", dest="console_device", help="Console number", default=0, type=int)

    def execute(self, *args, **kwargs):
        self.service.start()
        if kwargs['console']:
            self.wait_for(VmStatus.POWERING_UP)
            graphics_consoles_service = self.service.graphics_consoles_service()
            graphics_console = graphics_consoles_service.list()[kwargs['console_device']]
            console_service = graphics_consoles_service.console_service(graphics_console.id)
            (vvfile, vvfile_path) = tempfile.mkstemp(suffix='.vv')
            with os.fdopen(vvfile, 'w') as vvfile:
                vvfile.write(console_service.remote_viewer_connection_file())
            return vvfile_path
        else:
            return None


@add_command(class_ref)
class Stop(ovlib.verb.Verb):
    verb = "stop"

    def execute(self, *args, **kwargs):
        return self.service.stop()


@add_command(class_ref)
class Ticket(ovlib.verb.Verb):
    verb = "ticket"

    def execute(self, *args, **kwargs):
        self.wait_for(VmStatus.UP)
        consoles_service = self.service.graphics_consoles_service()
        consoles = consoles_service.list(current=True)
        console = next(
            (c for c in consoles if c.protocol == GraphicsType.SPICE),
            None
        )
        console_service = consoles_service.console_service(console.id)
        ticket = console_service.ticket()

        console_info = {
            'type': self.type.display.type,
            'address': self.type.display.address,
            'password': ticket.value,
            'port': self.type.display.port,
            'secure_port': self.type.display.secure_port,
            'title': self.type.name + ":%d"
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
        print self.type.status
        graphics_consoles_service = self.service.graphics_consoles_service()
        graphics_console = graphics_consoles_service.list()[kwargs['console'] - 1]
        console_service = graphics_consoles_service.console_service(graphics_console.id)
        (vvfile, vvfile_path) = tempfile.mkstemp(suffix='.vv')
        vvfile = os.fdopen(vvfile, 'w')
        vvfile.write(console_service.remote_viewer_connection_file())
        vvfile.close()
        return vvfile_path


class_ref.append(create.Create)
class_ref.append(delete.Delete)
class_ref.append(autoinstall.Autoinstall)

content = ObjectContext(object_name="vm", commands=class_ref, service_root="vms")
