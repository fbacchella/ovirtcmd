import ovlib.verb
from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.types import DataCenter, Qos, Network, StorageFormat
from ovirtsdk4.writers import DataCenterWriter, QosWriter, NetworkWriter
from ovirtsdk4.services import DataCenterService, DataCentersService, QossService, QosService, DataCenterNetworkService, DataCenterNetworksService


@wrapper(writer_class=NetworkWriter, type_class=Network, service_class=DataCenterNetworkService)
class DataCenterNetworkWrapper(ObjectWrapper):
    pass


@wrapper(service_class=DataCenterNetworksService)
class DataCenterNetworkWrapper(ListObjectWrapper):
    pass


@wrapper(writer_class=QosWriter, type_class=Qos, service_class=QosService)
class QosWrapper(ObjectWrapper):
    pass

@wrapper(service_class=QossService)
class QossWrapper(ListObjectWrapper):
    pass


@wrapper(writer_class=DataCenterWriter, type_class=DataCenter, service_class=DataCenterService)
class DataCenterWrapper(ObjectWrapper):
    pass


@wrapper(service_class=DataCentersService, service_root="datacenters"
)
class DataCentersWrapper(ListObjectWrapper):
    def creation_mapping(self, mac_pool=None, **kwargs):
        if isinstance(mac_pool, str):
            kwargs['mac_pool'] = self.api.macpools.get(kwargs['mac_pool'])
        else:
            kwargs['mac_pool'] = mac_pool
        return kwargs


@dispatcher(object_name="datacenter", wrapper=DataCenterWrapper, list_wrapper=DataCentersWrapper, name_type_mapping={
            'storage_format': StorageFormat
        })
class DataCenterDispatcher(Dispatcher):
    pass


@command(DataCenterDispatcher)
class List(ovlib.verb.List):
    pass


@command(DataCenterDispatcher)
class XmlExport(ovlib.verb.XmlExport):
    pass

@command(DataCenterDispatcher)
class Delete(ovlib.verb.RemoveForce):
    pass


@command(DataCenterDispatcher)
class Attach(ovlib.verb.Verb):
    verb = "attach"

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="Domain name", default=None)
        parser.add_option("-i", "--id", dest="id", help="Domain id", default=None)

    def execute(self, *args, **kwargs):
        sd = self.api.storagedomains.get(**kwargs)
        self.broker.storagedomains.add(params.StorageDomain(id=sd.id))


@command(DataCenterDispatcher)
class Create(ovlib.verb.Create):

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="New datecenter name", default=None)
        parser.add_option("-m", "--macpool", dest="macpool", help="Mac Pool", default=None)

    def execute(self, *args, **kwargs):
        macpool = kwargs.pop('macpool', None)
        if macpool is not None:
            kwargs['mac_pool'] = self.api.macpools.get(macpool)

        return self.api.datacenters.create(**kwargs)


@command(DataCenterDispatcher)
class AddQoS(ovlib.verb.Verb):
    verb = "addqos"

    def execute(self, *args, **kwargs):
        kwargs['type_'] = kwargs.pop('type', None)
        return self.broker.qoss.add(params.QoS(**kwargs))


