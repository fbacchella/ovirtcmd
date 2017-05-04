import ovlib.verb
from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.types import Session, User
from ovirtsdk4.writers import SessionWriter, UserWriter
from ovirtsdk4.services import UserService, UsersService


@wrapper(service_class=UsersService, service_root="users")
class UsersWrapper(ListObjectWrapper):
    pass


@wrapper(service_class=UserService, type_class=User, writer_class=UserWriter)
class UserWrapper(ObjectWrapper):
    pass


@dispatcher(object_name="user", wrapper=UserWrapper, list_wrapper=UsersWrapper)
class UserDispatcher(Dispatcher):
    def get(self, name=None, id=None):
        if id is None and name is not None:
            id=name
        return super(UserDispatcher, self).get(user_name=name)

@command(UserDispatcher)
class UserList(ovlib.verb.List):
    template = "{id!s} {user_name!s}"


@command(UserDispatcher)
class UserExport(ovlib.verb.XmlExport):
    pass

