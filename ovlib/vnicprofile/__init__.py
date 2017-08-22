import ovlib.verb

from ovlib.dispatcher import dispatcher, command, Dispatcher
from ovlib.wrapper import ObjectWrapper, ListObjectWrapper, wrapper

from ovirtsdk4.types import VnicProfile
from ovirtsdk4.writers import VnicProfileWriter
from ovirtsdk4.services import VnicProfilesService, VnicProfileService, AssignedVnicProfileService, AssignedVnicProfilesService


@wrapper(writer_class=VnicProfileWriter, type_class=VnicProfile, service_class=AssignedVnicProfileService)
class AssignedVnicProfileWrapper(ObjectWrapper):
    pass


@wrapper(service_class=AssignedVnicProfilesService)
class AssignedVnicProfilesWrapper(ListObjectWrapper):
    pass


@wrapper(writer_class=VnicProfileWriter, type_class=VnicProfile, service_class=VnicProfileService)
class VnicProfileWrapper(ObjectWrapper):
    pass


@wrapper(service_class=VnicProfilesService, service_root='vnicprofiles')
class VnicProfilesWrapper(ListObjectWrapper):
    pass


@dispatcher(object_name='vnicprofile', wrapper=VnicProfileWrapper, list_wrapper=VnicProfilesWrapper,)
class VnicProfileDispatcher(Dispatcher):
    pass


@command(VnicProfileDispatcher)
class VnicProfileList(ovlib.verb.List):
    pass


@command(VnicProfileDispatcher)
class VnicProfileExport(ovlib.verb.XmlExport):
    pass


@command(VnicProfileDispatcher)
class VnicProfileRemove(ovlib.verb.Remove):
    pass
