import ovlib.verb
import urllib
import tempfile
import os
import time

from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, command, dispatcher, wrapper, OVLibError

from ovirtsdk4.types import Vm, VmStatus, Nic, OperatingSystem, Display, DiskAttachment, TimeZone, \
    CpuType, Cpu, Cdrom, ReportedDevice, HostDevice, \
    Ticket, GraphicsConsole, GraphicsType
from ovirtsdk4.services import VmsService, VmService, \
    VmNicsService, VmNicService, \
    OperatingSystemService, VmGraphicsConsoleService, VmGraphicsConsolesService, \
    DiskAttachmentService, DiskAttachmentsService, \
    VmCdromService, VmCdromsService, \
    VmReportedDeviceService, VmReportedDevicesService, \
    VmHostDeviceService, VmHostDevicesService
from ovirtsdk4.writers import VmWriter, NicWriter, OperatingSystemWriter, DisplayWriter, \
    DiskAttachmentWriter, TimeZoneWriter, \
    CpuTypeWriter, CpuWriter, CdromWriter, ReportedDeviceWriter, HostDeviceWriter, \
    GraphicsConsoleWriter, TicketWriter


@wrapper(writer_class=HostDeviceWriter, type_class=HostDevice, service_class=VmHostDeviceService)
class HostDeviceWrapper(ObjectWrapper):
    pass


@wrapper(service_class=VmHostDevicesService)
class VmHostDevicesWrapper(ListObjectWrapper):
    pass


@wrapper(writer_class=ReportedDeviceWriter, type_class=ReportedDevice, service_class=VmReportedDeviceService)
class ReportedDeviceWrapper(ObjectWrapper):
    pass


@wrapper(service_class=VmReportedDevicesService)
class ReportedDevicesWrapper(ListObjectWrapper):
    pass


@wrapper(writer_class=CdromWriter, type_class=Cdrom, service_class=VmCdromService)
class VmCdromWrapper(ObjectWrapper):
    pass


@wrapper(service_class=VmCdromsService)
class VmCdromsWrapper(ListObjectWrapper):
    pass


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


@wrapper(writer_class=TicketWriter, type_class=Ticket, other_attributes=['expiry', 'value'])
class TicketWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=GraphicsConsoleWriter, type_class=GraphicsConsole, service_class=VmGraphicsConsoleService,
         other_methods=['ticket', 'remote_viewer_connection_file', 'proxy_ticket'],
         other_attributes=['port', 'tls_port', 'address', 'vm', 'protocol', 'vm'])
class VmGraphicsConsoleWrapper(ObjectWrapper):

    def refresh(self):
        self.type = self.service.get(current=True)
        self.dirty = False

    def get_vv_file(self, vvfile_path=None):
        if vvfile_path is None:
            (vvfile, vvfile_path) = tempfile.mkstemp(suffix='.vv')
            vvfile = os.fdopen(vvfile, 'w')
        else:
            vvfile = open(vvfile_path, 'w')
        vvfile.write(self.remote_viewer_connection_file())
        vvfile.close()
        return vvfile_path


@wrapper(service_class=VmGraphicsConsolesService)
class VmGraphicsConsolesWrapper(ListObjectWrapper):
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
        parser.add_option("--cloud_init", dest="use_cloud_init", help="Use cloud init", default=False, action="store_true")

    def execute(self, console=False, console_device=0, use_cloud_init=False):
        self.object.start(use_cloud_init=use_cloud_init)
        if console:
            self.object.wait_for(VmStatus.POWERING_UP)
            return self.object.get_vv_file(console_device)
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

class RemoteDisplay(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-c", "--c", dest="console_number", help="Console number", default=-1, type=int)
        parser.add_option("-p", "--p", dest="console_protocol", help="Console Protocol", default="spice")

    def execute(self, console_number=-1, console_protocol="spice"):
        self.object.wait_for(VmStatus.UP)
        consoles_service = self.object.graphics_consoles
        if console_number > 0:
            protocol = None
        else:
            protocol = GraphicsType[console_protocol.upper()]
        i = 0
        for c in consoles_service.list():
            if i == console_number or protocol == c.protocol:
                return self.getinfo(c)
            i += 1

        raise OVLibError("No matching console found")


@command(VmDispatcher, verb='ticket')
class Ticket(RemoteDisplay):

    def getinfo(self, console):
        ticket = self.api.wrap(console.ticket())
        console_info = {
            'address': console.address,
            'password': ticket.value,
            'port': console.port,
            'secure_port': console.tls_port,
        }
        if console.protocol == GraphicsType.SPICE:
            url = "spice://{address}:{port}/?password={password}&tls-port={secure_port}".format(**console_info)
        elif console.protocol == GraphicsType.VNC:
            url = "vnc://:{password}@{address}:{port}".format(**console_info)

        return url


@command(VmDispatcher, verb='viewer')
class Console(RemoteDisplay):

    def getinfo(self, console):
        return console.get_vv_file()


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
