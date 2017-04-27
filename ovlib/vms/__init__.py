import ovlib.verb
import urllib
import tempfile
import os

from ovlib import Dispatcher, ObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.types import Vm, GraphicsType, VmStatus, GraphicsConsole, Nic, OperatingSystem
from ovirtsdk4.services import VmsService, VmNicsService, VmNicService, OperatingSystemService
from ovirtsdk4.writers import VmWriter, GraphicsConsoleWriter, NicWriter, OperatingSystemWriter


@wrapper(writerClass=VmWriter, type_class=Vm, service_class=VmsService)
class VmWrapper(ObjectWrapper):

    def get_graphic_console(self, console):
        graphics_consoles_service = self.service.graphics_consoles_service()
        graphics_console = graphics_consoles_service.list()[console]
        return graphics_consoles_service.console_service(graphics_console.id)

    def get_vv_file(self, console, vvfile_path=None):
        graphics_console_service = self.get_graphic_console(console)
        if vvfile_path is None:
            (vvfile, vvfile_path) = tempfile.mkstemp(suffix='.vv')
            vvfile = os.fdopen(vvfile, 'w')
        else:
            vvfile = open(vvfile_path, 'w')
        vvfile.write(graphics_console_service.remote_viewer_connection_file())
        vvfile.close()
        return vvfile_path


@wrapper(service_class=VmNicsService)
class VmNicsWrapper(ObjectWrapper):
    pass


@wrapper(service_class=VmNicService, type_class=Nic, writerClass=NicWriter)
class VmNicWrapper(ObjectWrapper):
    pass


@wrapper(service_class=OperatingSystemService, type_class=OperatingSystem, writerClass=OperatingSystemWriter)
class OperatingSystemWrapper(ObjectWrapper):
    pass


@dispatcher(object_name="vm", service_root="vms", wrapper=VmWrapper)
class VmDispatcher(Dispatcher):
    pass


@command(VmDispatcher)
class Statistics(ovlib.verb.Statistics):
    pass


@command(VmDispatcher)
class List(ovlib.verb.List):
    pass


@command(VmDispatcher)
class XmlExport(ovlib.verb.XmlExport):
    pass


@command(VmDispatcher, verb='start')
class Start(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-c", "--console", dest="console", help="Launch a console", default=False, action="store_true")
        parser.add_option("-C", "--console_device", dest="console_device", help="Console number", default=0, type=int)

    def execute(self, console=False, console_device=0):
        self.object.start()
        if console:
            return self.object.get_vv_file(console_device)
            self.wait_for(VmStatus.POWERING_UP)
        else:
            return None


@command(VmDispatcher, verb='stop')
class Stop(ovlib.verb.Verb):

    def execute(self, *args, **kwargs):
        return self.object.stop()


@command(VmDispatcher, verb='ticket')
class Ticket(ovlib.verb.Verb):

    def execute(self, *args, **kwargs):
        self.object.wait_for(VmStatus.UP)
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


@command(VmDispatcher, verb='console')
class Console(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-c", "--c", dest="console", help="Console number", default=0, type=int)

    def execute(self, console=0):
        return self.object.get_vv_file(console)


@wrapper(writerClass=GraphicsConsoleWriter, type_class=GraphicsConsole)
class GraphicsConsoleWrapper(ObjectWrapper):
    pass


import autoinstall
import create
import delete
