import ovlib.verb

from ovlib.dispatcher import dispatcher, command, Dispatcher
from ovlib.wrapper import ObjectWrapper, ListObjectWrapper, wrapper

from ovirtsdk4.types import OperatingSystemInfo
from ovirtsdk4.writers import OperatingSystemInfoWriter
from ovirtsdk4.services import OperatingSystemService, OperatingSystemsService

@wrapper(writer_class=OperatingSystemInfoWriter, type_class=OperatingSystemInfo, other_attributes=['large_icon', 'small_icon'], service_class=OperatingSystemService)
class OperatingSystemInfoWrapper(ObjectWrapper):
    pass


# Yes names are buggy in ovirt sdk
@wrapper(service_class=OperatingSystemsService, service_root="operatingsystems")
class OperatingSystemsInfoWrapper(ListObjectWrapper):
    pass


@dispatcher(object_name="os", wrapper=OperatingSystemInfoWrapper, list_wrapper=OperatingSystemsInfoWrapper)
class OperatingSystemInfoDispatcher(Dispatcher):
    pass


@command(OperatingSystemInfoDispatcher)
class OperatingSystemList(ovlib.verb.List):
    pass


@command(OperatingSystemInfoDispatcher)
class OperatingSystemExport(ovlib.verb.XmlExport):
    pass
