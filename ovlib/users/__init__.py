import ovlib.verb
from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.types import User, SshPublicKey
from ovirtsdk4.writers import UserWriter, SshPublicKeyWriter
from ovirtsdk4.services import UserService, UsersService, SshPublicKeyService, SshPublicKeysService


@wrapper(service_class=UsersService, service_root="users")
class UsersWrapper(ListObjectWrapper):
    pass


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
    def get(self, name=None, id=None):
        return super(UserDispatcher, self).get(login=name, id=id)


@command(UserDispatcher)
class UserList(ovlib.verb.List):
    template = "{id!s} {principal!s}"


@command(UserDispatcher)
class UserExport(ovlib.verb.XmlExport):
    pass

