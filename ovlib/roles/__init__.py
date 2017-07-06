import ovlib.verb
from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.types import Role, Permit
from ovirtsdk4.writers import RoleWriter, PermitWriter
from ovirtsdk4.services import RoleService, RolesService, PermitService, PermitsService


@wrapper(service_class=PermitsService)
class PermitsWrapper(ListObjectWrapper):
    pass


@wrapper(service_class=PermitService, type_class=Permit, writer_class=PermitWriter, other_attributes=['administrative', 'role'])
class PermitWrapper(ObjectWrapper):
    pass


@wrapper(service_class=RolesService, service_root="roles")
class RolesWrapper(ListObjectWrapper):
    pass


@wrapper(service_class=RoleService, type_class=Role, writer_class=RoleWriter)
class RoleWrapper(ObjectWrapper):
    pass


@dispatcher(object_name="role", wrapper=RoleWrapper, list_wrapper=RolesWrapper)
class RoleDispatcher(Dispatcher):
    pass


@command(RoleDispatcher)
class RoleList(ovlib.verb.List):
    template = "{id!s} {name!s}"


@command(RoleDispatcher)
class RoleExport(ovlib.verb.XmlExport):
    pass

