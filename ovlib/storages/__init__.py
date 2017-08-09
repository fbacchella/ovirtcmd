import ovlib.verb
from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.types import StorageDomain, Qos, DiskProfile
from ovirtsdk4.writers import StorageDomainWriter
from ovirtsdk4.services import StorageDomainsService, StorageDomainService


@wrapper(writer_class=StorageDomainWriter, type_class=StorageDomain, service_class=StorageDomainService)
class StorageDomainWrapper(ObjectWrapper):
    pass

@wrapper(service_class=StorageDomainsService, service_root="storagedomains")
class StorageDomainsWrapper(ListObjectWrapper):
    pass


@dispatcher(object_name="storagedomain", wrapper=StorageDomainWrapper, list_wrapper=StorageDomainsWrapper)
class StorageDomainDispatcher(Dispatcher):
    pass


@command(StorageDomainDispatcher)
class StorageDomainList(ovlib.verb.List):
    pass


@command(StorageDomainDispatcher)
class StorageDomainExport(ovlib.verb.XmlExport):
    pass


@command(StorageDomainDispatcher)
class StorageDomainRemove(ovlib.verb.Remove):

    def fill_parser(self, parser):
        parser.add_option("-H", "--host", dest="host", help="Host used to delete domain", default=None)
        parser.add_option("-f", "--format", dest="format", help="Format domain", default=False, action='store_true')

    def execute(self, *args, **kwargs):
        host_name = kwargs.pop('host', None)
        if host_name is not None :
            host_delete = self.get('hosts', host_name)
            kwargs['host'] = host_delete
        delete_info = StorageDomain(**kwargs)
        self.broker.delete(delete_info)


@command(StorageDomainDispatcher, verb="discover")
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

def extract_storage_infos(host, source):
    storage = None
    if isinstance(source, dict):
        storage_info = source.pop('storage', {})
        storage_info['type'] = source.pop('storage_type', None)
        storage_info['name'] = source.pop('storage_name', None)
        storage_info['id'] = source.pop('storage_id', None)
        storage_info['path'] = source.pop('storage_path', None)
        storage_info['address'] = source.pop('storage_address', None)
        if 'type' in storage_info and 'type_' not in storage_info:
            storage_info['type_'] = storage_info.pop('type')
        storage = params.Storage(**storage_info)
    elif isinstance(source, params.Storage):
        storage = storage

    return storage

@command(StorageDomainDispatcher, verb="import")
class StorageDomainImport(ovlib.verb.Verb):
    verb = "import"

    def validate(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name")
        parser.add_option("-t", "--type", dest="type", default='data')
        parser.add_option("-w", "--warning_low", dest="warning_low_space_indicator", type='int')
        parser.add_option("-c", "--critical", dest="critical_space_action_blocker", type='int')
        parser.add_option("-H", "--host", dest="host")
        parser.add_option("-I", "--sid", dest="storage_id", help="ID of the storage to import")
        parser.add_option("-N", "--sname", dest="storage_name", help="Name of the storage to import")
        parser.add_option("-A", "--saddress", dest="storage_address", help="Adress of the storage to import")
        parser.add_option("-T", "--stype", dest="storage_type", help="Type of the storage to import")
        parser.add_option("-P", "--spath", dest="storage_path", help="Path of the storage to import")

    def execute(self, *args, **kwargs):
        host = self.get('hosts', kwargs.pop('host', None))

        storage = extract_storage_infos(host, kwargs)
        if storage.name is not None or storage.id is not None:
            unregisted = host.unregisteredstoragedomainsdiscover().storage_domains
            for domain in unregisted.storage_domain:
                if storage.id is not None and storage.id == domain.id:
                    storage = domain.storage
                    break
                elif storage.name is not None and storage.name == domain.name:
                    storage = domain.storage
                    break

        kwargs['storage'] = storage
        kwargs['type_'] = kwargs.pop('type', None)
        kwargs['host'] = params.Host(id=host.id)
        kwargs['import_'] = True

        new_storage_name = kwargs.get('name', None)
        if new_storage_name is None and storage is not None and storage.name is not None:
            kwargs['name'] = storage.name
        sd_params = StorageDomain(**kwargs)
        return self.contenaire.add(sd_params)

    def to_str(self, value):
        return self._export(value.storage_domains)

@command(StorageDomainDispatcher)
class StorageDomainCreate(ovlib.verb.Create):
    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name")
        parser.add_option("-t", "--type", dest="type")
        parser.add_option("-d", "--dc", "--datacenter", dest="datacenter")
        parser.add_option("-H", "--host", dest="host")
        parser.add_option("-T", "--storage_type", dest="storage_type")
        parser.add_option("-c", "--cluster", dest="cluster")
        parser.add_option("-P", "--spath", dest="storage_path", help="Path of the storage to import")

    def execute(self, *args, **kwargs):
        sd_type = kwargs.pop('type', None)
        name = kwargs.pop('name', None)
        datacenter = kwargs.pop('datacenter', None)
        cluster=kwargs.pop('datacenter', None)
        host = kwargs.pop('host', None)
        if host is not None:
            host = self.get('hosts', host)
        if cluster is None and host is not None:
            cluster = host.cluster
        elif cluster is not None:
            cluster = self.get('clusters')
        if datacenter is None and cluster is not None:
            datacenter = cluster.data_center
        elif datacenter is not None:
            datacenter = self.get('datacenters', datacenter)

        type = kwargs.pop('type', None)
        if type is not None:
            kwargs['type_'] = type
        new_storage = extract_storage_infos(host, kwargs)
        sd_params = params.StorageDomain(name=name,
                                         data_center=datacenter, host=host, type_=sd_type, storage_format="v3",
                                         storage=new_storage)
        return self.contenaire.add(sd_params)

@command(StorageDomainDispatcher, verb="addprofile")
class AddProfile(ovlib.verb.Verb):

    def execute(self, *args, **kwargs):
        qoss = None
        dc = kwargs.pop('datacenter', None)
        if dc is not None:
            dc = self.get(self.api.datacenters, dc)
            qoss = dc.qoss
        qos = kwargs.pop('qos', None)
        if qos is not None:
            qos = self.get(qoss, qos)
        if qos is not None:
            kwargs['qos'] = Qos(id=qos.id)
        if kwargs.get('name', None) is None:
            kwargs['name'] = qos.name
        return self.broker.diskprofiles.add(DiskProfile(**kwargs), )


@command(StorageDomainDispatcher, verb="refresh_luns")
class RefreshLuns(ovlib.verb.Verb):

    def execute(self, *args, **kwargs):
        storage = self.api.wrap(self.object.storage)
        lu = self.api.wrap(storage.volume_group.logical_units)
        to_refresh=[]
        for i in lu:
            to_refresh.append(i.type)
        return self.object.refresh_luns(logical_units=to_refresh)

