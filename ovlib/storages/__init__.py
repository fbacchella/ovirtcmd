import ovlib.verb
from ovlib import Object_Context, add_command
from ovirtsdk.xml import params
from ovirtsdk.infrastructure.brokers import StorageDomain
from ovirtsdk.infrastructure.common import Base

class_ref = []

@add_command(class_ref)
class List(ovlib.verb.List):
    pass


@add_command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    pass


@add_command(class_ref)
class Delete(ovlib.verb.Delete):

    def fill_parser(self, parser):
        parser.add_option("-h", "--host", dest="host", help="Host used to delete domain", default=None)
        parser.add_option("-f", "--format", dest="format", help="Format domain", default=False, action='store_true')

    def execute(self, *args, **kwargs):
        host_name = kwargs.pop('host', None)
        if host_name is not None :
            host_delete = self.get('hosts', host_name)
            kwargs['host'] = host_delete
        delete_info = params.StorageDomain(**kwargs)
        self.broker.delete(delete_info)


@add_command(class_ref)
class Discover(ovlib.verb.Verb):
    verb = "discover"

    def validate(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-H", "--host", dest="host", help="Host used to discover")
        parser.add_option("-I", "--sid", dest="storage_id", help="ID of the storage to import")
        parser.add_option("-N", "--sname", dest="storage_name", help="Name of the storage to import")

    def execute(self, *args, **kwargs):
        host = self.get('hosts', kwargs.pop('host', None))
        domains_list = host.unregisteredstoragedomainsdiscover().storage_domains.storage_domain
        storage_id = kwargs.pop('storage_id', None)
        storage_name = kwargs.pop('storage_name', None)
        if storage_id is None and storage_name is None:
            def iterate():
                for i in domains_list:
                    yield i
            return iterate()
        else:
            for domain in domains_list:
                if storage_id is not None and storage_id == domain.id:
                    return domain.storage
                elif storage_name is not None and storage_name == domain.name:
                    return domain.storage
            return None

    def to_str(self, value):
        if isinstance(value, Base):
            return self._export(value)
        else:
            return value.__str__()



@add_command(class_ref)
class Import(ovlib.verb.Verb):
    verb = "import"

    def validate(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name")
        parser.add_option("-t", "--type", dest="type", default='data')
        parser.add_option("-w", "--warning_low", dest="warning_low_space_indicator", type='int')
        parser.add_option("-c", "--type", dest="critical_space_action_blocker", type='int')
        parser.add_option("-c", "--type", dest="critical_space_action_blocker", type='int')
        parser.add_option("-H", "--host", dest="host")
        parser.add_option("-I", "--sid", dest="storage_id", help="ID of the storage to import")
        parser.add_option("-N", "--sname", dest="storage_name", help="Name of the storage to import")
        parser.add_option("-A", "--saddress", dest="storage_address", help="Adress of the storage to import")
        parser.add_option("-T", "--stype", dest="storage_type", help="Type of the storage to import")

    def execute(self, *args, **kwargs):
        host = self.get('hosts', kwargs.pop('host', None))
        address = kwargs.pop('storage_address', None)
        storage_type = kwargs.pop('storage_type', None)
        storage = kwargs.pop('storage', None)
        if address is None:
            storage_id = kwargs.pop('storage_id', None)
            storage_name = kwargs.pop('storage_name', None)
            unregisted = host.unregisteredstoragedomainsdiscover().storage_domains
            for domain in unregisted.storage_domain:
                if storage_id is not None and storage_id == domain.id:
                    kwargs['storage'] = domain.storage
                elif storage_name is not None and storage_name == domain.name:
                    kwargs['storage'] = domain.storage
                    break
        elif storage_type is not None and address is not None:
            kwargs['storage'] = params.Storage(address=address, type_=storage_type)
        elif storage is not None:
            kwargs['storage'] = storage
        kwargs['type_'] = kwargs.pop('type', None)
        kwargs['host'] = params.Host(id=host.id)
        kwargs['import_'] = True
        new_storage_name = kwargs.get('name', None)
        if new_storage_name is None and storage_name is not None:
            kwargs['name'] = storage_name
        sd_params = params.StorageDomain(**kwargs)
        return self.contenaire.add(sd_params)

    def to_str(self, value):
        return self._export(value.storage_domains)


oc = Object_Context(api_attribute = "storagedomains", object_name = "storage", commands = class_ref, broker_class=StorageDomain)
