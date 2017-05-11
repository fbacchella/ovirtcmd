import ovlib.verb
import urllib
import tempfile
import os
import time

from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.types import Vm, VmStatus, GraphicsConsole, Nic, OperatingSystem, Display, DiskAttachment, TimeZone, \
    CpuType, Cpu
from ovirtsdk4.services import VmsService, VmService, \
    VmNicsService, VmNicService, \
    OperatingSystemService, VmGraphicsConsoleService, VmGraphicsConsolesService, \
    DiskAttachmentService, DiskAttachmentsService
from ovirtsdk4.writers import VmWriter, GraphicsConsoleWriter, NicWriter, OperatingSystemWriter, DisplayWriter, \
    DiskAttachmentWriter, TimeZoneWriter, \
    CpuTypeWriter, CpuWriter


@wrapper(writer_class=CpuTypeWriter, type_class=CpuType)
class CpuTypeWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=CpuWriter, type_class=Cpu)
class CpuWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=TimeZoneWriter, type_class=TimeZone)
class TimeZoneWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=DiskAttachmentWriter, type_class=DiskAttachment, service_class=DiskAttachmentService, other_attributes=['active', 'disk'])
class DiskAttachmentWrapper(ObjectWrapper):
    pass


@wrapper(service_class=DiskAttachmentsService)
class DiskAttachmentsWrapper(ListObjectWrapper):
    pass


@wrapper(writer_class=GraphicsConsoleWriter, type_class=GraphicsConsole, service_class=VmGraphicsConsoleService)
class VmGraphicsConsoleWrapper(ObjectWrapper):
    pass


@wrapper(service_class=VmGraphicsConsolesService)
class VmGraphicsConsolesWrapper(ListObjectWrapper):
    pass


@wrapper(writer_class=GraphicsConsoleWriter, type_class=GraphicsConsole, service_class=VmGraphicsConsoleService)
class VmGraphicsConsoleWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=DisplayWriter, type_class=Display)
class DisplayWrapper(ObjectWrapper):
    pass


@wrapper(service_class=VmsService, service_root="vms")
class VmsWrapper(ListObjectWrapper):
    pass


@wrapper(writer_class=VmWriter, type_class=Vm, service_class=VmService, other_attributes=['os'], other_methods=['suspend'])
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
class VmNicsWrapper(ListObjectWrapper):
    pass


@wrapper(service_class=VmNicService, type_class=Nic, writer_class=NicWriter)
class VmNicWrapper(ObjectWrapper):
    pass


@wrapper(service_class=OperatingSystemService, type_class=OperatingSystem, writer_class=OperatingSystemWriter)
class OperatingSystemWrapper(ObjectWrapper):
    pass


@dispatcher(object_name="vm", wrapper=VmWrapper, list_wrapper=VmsWrapper)
class VmDispatcher(Dispatcher):
    pass


@command(VmDispatcher)
class VmStatistics(ovlib.verb.Statistics):
    pass


@command(VmDispatcher)
class VmList(ovlib.verb.List):
    pass


@command(VmDispatcher)
class VmExport(ovlib.verb.XmlExport):
    pass


@command(VmDispatcher, verb='start')
class VmStart(ovlib.verb.Verb):

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
class VmStop(ovlib.verb.Verb):

    def execute(self, *args, **kwargs):
        return self.object.stop()


@command(VmDispatcher, verb='suspend')
class VmSuspend(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-a", "--async", dest="async", help="Don't wait for completion state", default=False, action='store_true')

    def execute(self, async=False):
        self.object.suspend(async=async)
        if not async:
            self.object.wait_for(VmStatus.SUSPENDED)


@command(VmDispatcher, verb='ticket')
class Ticket(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-c", "--c", dest="console_number", help="Console number", default=0, type=int)

    def execute(self, console_number=0):
        self.object.wait_for(VmStatus.UP)
        consoles_service = self.object.service.graphics_consoles_service()
        consoles = consoles_service.list(current=True)
        console = consoles[console_number]
        console_service = consoles_service.console_service(console.id)
        ticket = console_service.ticket()
        port = self.object.type.display.port
        if port is None:
            port = self.object.type.display.secure_port
        console_info = {
            'type': self.object.type.display.type,
            'address': self.object.type.display.address,
            'password': ticket.value,
            'port': port,
            'secure_port': self.object.type.display.secure_port,
            'title': self.object.type.name + ":%d"
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


@command(VmDispatcher, verb='migrating')
class Migrating(ovlib.verb.Verb):

    def validate(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-f", "--follow", dest="follow", help="Follows status", default=False, action="store_true")
        parser.add_option("-p", "--pause", dest="pause", help="Pause in seconds between each status", default=5, type=int)

    def execute(self, follow=False, pause=5):
        # again is used to detect that at least one VM is actually migrating
        again = True
        while again:
            again = False
            for vm in self.object:
                if vm.status == VmStatus.MIGRATING:
                    stat = self.api.wrap(vm.statistics)
                    migration = stat.get(name='migration.progress')
                    again = True
                    yield "%s %s%%" % (vm.name,  migration.values[0].datum)
            if not follow:
                break

            time.sleep(5)


import autoinstall
import create
import remove
