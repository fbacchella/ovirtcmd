import ovlib.verb
from ovlib import Object_Context, add_command
from ovirtsdk.infrastructure.brokers import Disk
from ovirtsdk.xml import params
from ovlib import parse_size

class_ref = []

@add_command(class_ref)
class List(ovlib.verb.List):
    pass

@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    def execute(self, *args, **kwargs):
        print self.broker.get_type()
        print self.broker.get_storage_type()
        return super(XmlExport, self).execute(*args, **kwargs)


@add_command(class_ref)
class Delete(ovlib.verb.Delete):
    pass

@add_command(class_ref)
class Create(ovlib.verb.Create):

    def uses_template(self):
        return True

    def execute(self, *args, **kwargs):
        disk_size = kwargs.pop('disk_size', None)
        if disk_size is not None:
            kwargs['size'] = parse_size(disk_size)

        storage_domain=kwargs.pop('storage_domain', None)
        if storage_domain is not None:
            storage_domain = self.get(self.api.storagedomains, storage_domain)
            kwargs['storage_domains'] = params.StorageDomains(
                storage_domain=[params.StorageDomain(id=storage_domain.id)])

        lun_storage = kwargs.pop('lun_storage', None)
        units = []
        if lun_storage is not None:
            for lu in lun_storage:
                units.append(params.LogicalUnit(**lu))
            kwargs['lun_storage'] = params.Storage(logical_unit=units)
            kwargs['storage_type'] = 'lun'
        kwargs['type_'] = 'system'

        return self.contenaire.add(params.Disk(**kwargs))


disk = Object_Context(api_attribute = "disks", object_name = "disk", commands = class_ref, broker_class=Disk)
