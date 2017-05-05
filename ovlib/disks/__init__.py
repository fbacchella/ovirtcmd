import ovlib.verb

from ovlib import Dispatcher, ListObjectWrapper, ObjectWrapper, command, dispatcher, wrapper, parse_size

from ovirtsdk4.types import Disk
from ovirtsdk4.services import DiskService, DisksService
from ovirtsdk4.writers import DiskWriter


@wrapper(writer_class=DiskWriter, type_class=Disk, service_class=DiskService)
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
class DiskDelete(ovlib.verb.Delete):
    pass


@command(DiskDispatcher)
class DiskCreate(ovlib.verb.Create):

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-d", "--storage_domain", dest="storage_domain", help="Storage Domain name", default=None)
        parser.add_option("-s", "--size", dest="disk_size", help="size", default=None)
        parser.add_option("-l", "--lun_storage", dest="lun_storage", help="LUN device", default=None)

    def execute(self, **kwargs):
        disk_size = kwargs.pop('disk_size', None)
        if disk_size is not None:
            kwargs['size'] = parse_size(disk_size)

        storage_domain=kwargs.pop('storage_domain', None)
        if storage_domain is not None:
            storage_domain = StoragesDomainWrapper(self.api).get(name=storage_domain)
            kwargs['storage_domains'] = params.StorageDomains(
                storage_domain=[params.StorageDomain(id=storage_domain.id)])

        lun_storage = kwargs.pop('lun_storage', None)
        units = []
        if lun_storage is not None:
            for lu in lun_storage:
                units.append(params.LogicalUnit(**lu))
            if len(units) > 0:
                if units[0].address is not None:
                    storage_type = 'iscsi'
                else:
                    storage_type = 'fcp'
                kwargs['lun_storage'] = params.Storage(logical_unit=units, type_=storage_type)
        kwargs['type_'] = 'system'

        return self.contenaire.add(params.Disk(**kwargs))


