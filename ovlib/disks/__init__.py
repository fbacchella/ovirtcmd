import ovlib.verb

from ovlib import Dispatcher, ListObjectWrapper, ObjectWrapper, command, dispatcher, wrapper, parse_size, event_waiter, EventsCode

from ovirtsdk4.types import Disk,  DiskFormat, StorageDomain, DiskAttachment, DiskInterface
from ovirtsdk4.services import DiskService, DisksService
from ovirtsdk4.writers import DiskWriter



@wrapper(writer_class=DiskWriter, type_class=Disk, service_class=DiskService, other_attributes=['comment', 'bootable'])
class DiskWrapper(ObjectWrapper):
    pass


@wrapper(service_class=DisksService, service_root="disks")
class DisksWrapper(ListObjectWrapper):
    pass


@dispatcher(object_name="disk", wrapper=DiskWrapper, list_wrapper=DisksWrapper)
class DiskDispatcher(Dispatcher):
    pass


@command(DiskDispatcher)
class DiskStatistics(ovlib.verb.Statistics):
    pass


@command(DiskDispatcher)
class List(ovlib.verb.List):
    pass


@command(DiskDispatcher)
class DiskExport(ovlib.verb.XmlExport):
    pass


@command(DiskDispatcher)
class DiskRemove(ovlib.verb.Remove):
    pass


@command(DiskDispatcher)
class DiskCreate(ovlib.verb.Create):

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="Disk name", default=None)
        parser.add_option("-d", "--storage_domain", dest="storage_domain", help="Storage Domain name", default=None)
        parser.add_option("-s", "--size", dest="disk_size", help="size", default=None)
        parser.add_option("-D", "--description", dest="description", help="Disk description", default=None)
        parser.add_option("-v", "--vm", dest="vm", help="Attachement VM", default=None)
        parser.add_option("-f", "--format", dest="format", help="disk format", default=None)

    def execute(self, name, disk_size, storage_domain, vm=None, description=None, format=DiskFormat.RAW, disk_size_ratio=10,
                disk_interface = DiskInterface.VIRTIO_SCSI,
                **kwargs):
        provisioned_size = parse_size(disk_size)

        if isinstance(format, (str, unicode)):
            format = DiskFormat[format.upper()]

        events_returned = []
        waiting_events = [EventsCode.USER_ADD_DISK_FINISHED_SUCCESS]
        break_on = [EventsCode.USER_ADD_DISK_FINISHED_FAILURE, EventsCode.USER_FAILED_ADD_DISK]
        filter = "event_storage = %s" % storage_domain
        if vm is not None:
            filter += " or event_vm = %s" % vm
            vm = self.api.vms.get(name=vm)
        with event_waiter(self.api, filter, events_returned,
                          wait_for=waiting_events,
                          break_on=break_on,
                          verbose=True):
            newdisk = self.api.disks.add(Disk(
                name = name, storage_domains=[StorageDomain(name=storage_domain)], description=description,
                provisioned_size=provisioned_size, format=format))

        if vm is not None:
            da = DiskAttachment(disk=newdisk, interface=disk_interface, bootable=False, active=True)
            vm.disk_attachments.add(da)

        return newdisk


