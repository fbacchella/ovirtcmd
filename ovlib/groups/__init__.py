import ovlib.verb
from ovlib.dispatcher import dispatcher, command, Dispatcher
from ovlib.wrapper import ObjectWrapper, ListObjectWrapper, wrapper

from ovirtsdk4.types import Group
from ovirtsdk4.writers import GroupWriter
from ovirtsdk4.services import GroupsService, GroupService


@wrapper(service_class=GroupsService, service_root="groups")
class GroupsWrapper(ListObjectWrapper):
    pass


@wrapper(service_class=GroupService, type_class=Group, writer_class=GroupWriter, other_attributes=[])
class GroupWrapper(ObjectWrapper):
    pass


@dispatcher(object_name="group", wrapper=GroupWrapper, list_wrapper=GroupsWrapper)
class GroupDispatcher(Dispatcher):
    pass

@command(GroupDispatcher)
class GroupList(ovlib.verb.List):
    pass


@command(GroupDispatcher)
class GroupExport(ovlib.verb.XmlExport):
    pass

