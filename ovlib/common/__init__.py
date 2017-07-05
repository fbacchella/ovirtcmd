from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, wrapper

from ovirtsdk4.types import Permission
from ovirtsdk4.writers import PermissionWriter
from ovirtsdk4.services import PermissionService, AssignedPermissionsService


@wrapper(service_class=PermissionService, type_class=Permission, writer_class=PermissionWriter)
class PermissionWrapper(ObjectWrapper):
    pass


@wrapper(service_class=AssignedPermissionsService)
class AssignedPermissionsWrapper(ListObjectWrapper):
    pass
