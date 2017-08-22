from ovirtsdk4.types import Permission, Role, Group, User
from ovirtsdk4.writers import PermissionWriter, RoleWriter
from ovirtsdk4.services import PermissionService, AssignedPermissionsService, RoleService, RolesService

from ovlib import OVLibError, is_id
from ovlib.wrapper import wrapper, ObjectWrapper, ListObjectWrapper

from ovlib.users import UserWrapper
from ovlib.groups import GroupWrapper
from ovlib.roles import RoleWrapper
from ovlib.system import SystemWrapper

@wrapper(type_class=Role, writer_class=RoleWriter, service_class=RoleService)
class RoleWrapper(ObjectWrapper):
    pass


@wrapper(service_class=RolesService)
class RolesWrapper(ListObjectWrapper):
    pass


@wrapper(service_class=PermissionService, type_class=Permission, writer_class=PermissionWriter,
         other_attributes=['cluster', 'comment', 'data_center', 'description', 'disk', 'group', 'host', 'role', 'storage_domain', 'template', 'user', 'vm', 'vm_pool'],
         name_type_mapping={'role': Role, 'group': Group, 'user': User})
class PermissionWrapper(ObjectWrapper):
    def __str__(self):
        return self.format_relative()

    def format_relative(self, reference=None):
        destination = None
        source = None
        for j in ['group', 'user']:
            if getattr(self, j) is not None:
                source = self.api.wrap(getattr(self, j))
                break
        for j in ['cluster', 'data_center', 'disk', 'host', 'storage_domain', 'template', 'vm', 'vm_pool']:
            if getattr(self, j) is not None:
                destination = self.api.wrap(getattr(self, j))
                break
        if reference is not None and source.id == reference.id:
            source = ""
        elif isinstance(source, UserWrapper):
            source = "From user '%s' " % source.principal
        else:
            source = "From group '%s' " % source.name
        if destination is None:
            destination = '(system)'
        else:
            destination = "%s '%s'" % (type(destination.type).__name__.lower(), destination.name)
        return "%shas role '%s' on %s" % (source, self.api.wrap(self.role).name, destination)

    def get_source(self):
        for j in ['group', 'user']:
            if getattr(self, j) is not None:
                return self.api.wrap(getattr(self, j))

    def get_destination(self):
        destination = None
        for j in ['cluster', 'data_center', 'disk', 'host', 'storage_domain', 'template', 'vm', 'vm_pool']:
            if getattr(self, j) is not None:
                destination = self.api.wrap(getattr(self, j))
                break
        if destination is None:
            destination = SystemWrapper(self.api)
        return destination


@wrapper(service_class=AssignedPermissionsService, name_type_mapping={'permission': Permission})
class AssignedPermissionsWrapper(ListObjectWrapper):

    def add(self, role, user=None, group=None, wait=True):
        if user is None and group is None:
            raise OVLibError("Neither group or user given when adding permission")

        if user is not None and group is not None:
            raise OVLibError("Both group or user given when adding permission")

        if role is not None and is_id(role):
            role = self.api.roles.get(id=role).type
        elif isinstance(role, str):
            role = self.api.roles.get(name=role).type
        elif isinstance(role, RoleWrapper):
            role = role.type

        if user is not None and is_id(user):
            user = self.api.users.get(id=user).type
        elif isinstance(user, str):
            user = self.api.users.get(name=user).type
        elif isinstance(user, UserWrapper):
            user = user.type

        if group is not None and is_id(group):
            group = self.api.groups.get(id=group).type
        elif isinstance(group, str):
            group = self.api.groups.get(name=group).type
        elif isinstance(group, GroupWrapper):
            group = group.type

        return self.api.wrap(self.service.add(Permission(role=role, user=user, group=group), wait=wait))

