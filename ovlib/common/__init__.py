from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, wrapper

from ovirtsdk4.types import Permission
from ovirtsdk4.writers import PermissionWriter
from ovirtsdk4.services import PermissionService, AssignedPermissionsService

from ovlib.users import UserWrapper
from ovlib.system import SystemWrapper

@wrapper(service_class=PermissionService, type_class=Permission, writer_class=PermissionWriter,
         other_attributes=['cluster', 'comment', 'data_center', 'description', 'disk', 'group', 'host', 'role', 'storage_domain', 'template', 'user', 'vm', 'vm_pool'])
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


@wrapper(service_class=AssignedPermissionsService)
class AssignedPermissionsWrapper(ListObjectWrapper):
    pass
