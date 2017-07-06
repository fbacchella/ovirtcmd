import ovlib.verb
from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, command, dispatcher, wrapper
from ovlib.system import SystemWrapper

from ovirtsdk4.types import User, SshPublicKey
from ovirtsdk4.writers import UserWriter, SshPublicKeyWriter
from ovirtsdk4.services import UserService, UsersService, SshPublicKeyService, SshPublicKeysService


@wrapper(service_class=UsersService, service_root="users")
class UsersWrapper(ListObjectWrapper):

    def list(self, name=None, **kwargs):
        return super(UsersWrapper, self).list(usrname=name, **kwargs)

    def get(self, name=None, id=None):
        return super(UsersWrapper, self).get(usrname=name, id=id)


@wrapper(service_class=UserService, type_class=User, writer_class=UserWriter, other_attributes=['user_name', 'principal'])
class UserWrapper(ObjectWrapper):
    pass


@wrapper(service_class=SshPublicKeysService)
class SshPublicKeysWrapper(ListObjectWrapper):
    pass


@wrapper(service_class=SshPublicKeyService, type_class=SshPublicKey, writer_class=SshPublicKeyWriter)
class SshPublicKeyWrapper(ObjectWrapper):
    pass


@dispatcher(object_name="user", wrapper=UserWrapper, list_wrapper=UsersWrapper)
class UserDispatcher(Dispatcher):
    pass


@command(UserDispatcher)
class UserList(ovlib.verb.List):
    template = "{id!s} {principal!s}"


@command(UserDispatcher)
class UserExport(ovlib.verb.XmlExport):
    pass


@command(UserDispatcher, verb='permits')
class UserPermits(ovlib.verb.Verb):
    
    def execute(self, *args):
        permissions = {}
        for i in self.object.permissions.list():
            destination = i.get_destination()
            if isinstance(destination, SystemWrapper):
                key = destination.name
            else:
                key = "%s/%s" % (destination.get_type_name(), destination.name)
            permissions[key] = set()
            for j in self.api.wrap(i.role).permits.list():
                permissions[key].add(j.name)
        for k in sorted(permissions.keys()):
            yield k,permissions[k]

    def to_str(self, kv):
        object = kv[0]
        permits = kv[1]
        buffer = "%s:\n" % object
        for i in sorted(permits):
            buffer += "  %s\n" % i
        return buffer


@command(UserDispatcher, verb='roles')
class UserPermissions(ovlib.verb.Verb):
    def execute(self, *args):
        for i in self.object.permissions.list():
            yield i

    def to_str(self, permission):
        return(permission.format_relative(self.object))


