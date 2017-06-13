import ovlib.verb
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

    def get_ticket(self):
        ticket = self.api.wrap(self.ticket())
        console_info = {
            'address': self.address,
            'password': ticket.value,
            'port': self.port,
            'secure_port': self.tls_port,
        }
        if self.protocol == GraphicsType.SPICE:
            url = "spice://{address}:{port}/?password={password}&tls-port={secure_port}".format(**console_info)
        elif self.protocol == GraphicsType.VNC:
            url = "vnc://:{password}@{address}:{port}".format(**console_info)

        return url


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

    def get_graphic_console(self, protocol=GraphicsType.SPICE, console_protocol="spice"):
        if self.status != VmStatus.UP and self.status != VmStatus.POWERING_UP:
            raise OVLibError("No console available, not started")
        for c in self.graphics_consoles.list():
            if protocol == c.protocol:
                return c

        raise OVLibError("No matching console found")


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


@command(VmDispatcher)
class VmWaitFor(ovlib.verb.WaitFor):
    pass


@command(VmDispatcher, verb='start')
class VmStart(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-c", "--console", dest="console", help="Launch a console", default=False, action="store_true")
        parser.add_option("-C", "--console_protocol", dest="console_protocol", help="Console protocol (VNC or Spice)", default="spice")
        parser.add_option("--cloud_init", dest="use_cloud_init", help="Use cloud init", default=False, action="store_true")

    def execute(self, console=False, console_protocol='spice', use_cloud_init=False):
        self.object.start(use_cloud_init=use_cloud_init)
        if console:
            self.object.wait_for(VmStatus.POWERING_UP)
            protocol = GraphicsType[console_protocol.upper()]
            return self.object.get_graphic_console(protocol).get_vv_file()
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
        parser.add_option("-p", "--protocol", dest="console_protocol", help="Console Protocol", default="spice")
        parser.add_option("-w", "--wait", dest="wait", help="Wait for VM to be in a suitable state", default=False, action='store_true')

    def execute(self, console_protocol="spice", wait=False):
        if wait:
            if self.object.status != VmStatus.POWERING_UP or self.object.status != VmStatus.UP:
                self.object.wait_for((VmStatus.POWERING_UP, VmStatus.UP))
        protocol = GraphicsType[console_protocol.upper()]
        console = self.object.get_graphic_console(protocol)
        return self.getinfo(console)


@command(VmDispatcher, verb='ticket')
class Ticket(RemoteDisplay):

    def getinfo(self, console):
        return console.get_ticket()


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


from . import autoinstall
from . import create
from . import remove
