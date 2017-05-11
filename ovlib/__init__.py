import re
import inspect
import io
import time
import collections

from enum import IntEnum
from contextlib import contextmanager

from ovlib.template import load_template, DotTemplate

import ovirtsdk4.writers
import ovirtsdk4.types
import ovirtsdk4

from ovirtsdk4 import xml, List

class OVLibError(Exception):
    def __init__(self, error_message, value={}, exception=None):
        self.value = value
        if error_message is None:
            self.error_message = value
        else:
            self.error_message = error_message
        if exception is not None:
            self.exception = exception

    def __str__(self):
        return repr(self.message)


class OVLibErrorNotFound(OVLibError):
    pass

class EventsCode(IntEnum):
    USER_ADD_VM = 34
    USER_ADD_VM_STARTED = 37
    USER_ADD_VM_FINISHED_SUCCESS = 53
    USER_FAILED_ADD_VM = 57
    USER_ADD_VM_FINISHED_FAILURE = 60
    USER_ADD_DISK_TO_VM = 78
    USER_ADD_DISK_TO_VM_FINISHED_SUCCESS = 97
    USER_ADD_DISK_TO_VM_FINISHED_FAILURE = 98
    VDS_INSTALL_IN_PROGRESS_ERROR = 511
    HOST_AVAILABLE_UPDATES_FAILED = 839
    HOST_UPGRADE_STARTED = 840
    HOST_UPGRADE_FAILED = 841
    HOST_UPGRADE_FINISHED = 842
    HOST_UPDATES_ARE_AVAILABLE_WITH_PACKAGES = 843
    HOST_UPDATES_ARE_AVAILABLE = 844
    HOST_AVAILABLE_UPDATES_FINISHED = 885
    HOST_AVAILABLE_UPDATES_PROCESS_IS_ALREADY_RUNNING = 886
    HOST_AVAILABLE_UPDATES_SKIPPED_UNSUPPORTED_STATUS = 887
    HOST_UPGRADE_FINISHED_MANUAL_HA = 890
    NETWORK_ADD_VM_INTERFACE = 932
    NETWORK_ACTIVATE_VM_INTERFACE_SUCCESS = 1012
    NETWORK_ACTIVATE_VM_INTERFACE_FAILURE = 1013


class ExecutorWrapper(Exception):
    def __init__(self, executor):
        self.executor = executor


def join_default(val, default):
    for key in default:
        if key not in val:
            val[key] = default[key]

units = {
    'T': 1099511627776,
    'G': 1073741824,
    'M': 1048576,
    'K': 1024,
    'k': 1024,
    '': 1,
}
size_re = re.compile('(\\d+)([TGMKk]?)');


def parse_size(input_size, out_suffix="", default_suffix=None):
    if isinstance(input_size, basestring):
        matcher = size_re.match("%s" % input_size)
        if matcher is not None:
            value = float(matcher.group(1))
            suffix = matcher.group(2)
            if suffix == '' and default_suffix is not None:
                suffix = default_suffix
            return int(value * units[suffix] / units[out_suffix])
    else:
        return input_size


def create_re():
    re_elements = []
    for count in (8, 4, 4, 4, 12):
        re_elements.append('([0-9]|[a-z]){%d}' % count)
    return re.compile('^' + '-'.join(re_elements) + '$')


id_re = create_re()

def is_id(try_id):
    return isinstance(try_id, basestring) and id_re.match(try_id) is not None


dispatchers = { }

def command(dispatcher_class, verb=None):
    def decorator(command_class):
        if verb is not None:
            command_class.verb = verb
        dispatchers[dispatcher_class.object_name].add_command(command_class)
        return command_class
    return decorator

def dispatcher(object_name, wrapper, list_wrapper):
    def decorator(dispatcher_class):
        dispatcher_class.object_name = object_name
        dispatcher_class.list_wrapper = list_wrapper
        dispatcher_class.wrapper = wrapper
        dispatchers[object_name] = dispatcher_class()
        return dispatcher_class
    return decorator


class Dispatcher(object):

    def __init__(self):
        self.verbs = {}
        self._api = None

    def add_command(self, new_command):
        self.verbs[new_command.verb] = new_command

    def fill_parser(self, parser):
        parser.add_option("-i", "--id", dest="id", help="object ID")
        parser.add_option("-n", "--name", dest="name", help="object tag 'Name'")

    def execute(self, name, method_args=[], method_kwargs={}):
        NameError('Not implemented')

    def get_cmd(self, verb):
        if verb in self.verbs:
            cmd_class = self.verbs[verb]
            cmd = cmd_class(self)
            return cmd
        else:
            # Everything failed so return false
            return False

    def fill_template(self, template, variables):
        if template is None:
            if len(variables) > 0:
                raise OVLibError("YAML template not found")
            return {}
        else:
            return load_template(template, variables)

    def run_phrase(self, verb, object_options={}, object_args=[]):
        cmd = self.get_cmd(verb)
        if cmd:
            (verb_options, verb_args) = cmd.parse(object_args)

            # transform options to a dict and removed undeclared arguments
            verb_options = {k: v for k, v in vars(verb_options).iteritems()
                            if v is not None and (not isinstance(v, (list, tuple, buffer, xrange, dict)) or len(v) != 0)}
            return self.execute_phrase(cmd, object_options, verb_options, verb_args)
        else:
            raise OVLibError("unknown verb %s" % verb)


    def execute_phrase(self, cmd, object_options={}, verb_options={}, verb_args=[]):
        if cmd.object is None and len(object_options) > 0:
            try:
                cmd.object = self.get(**object_options)
            except ovirtsdk4.Error as e:
                raise OVLibError(e.message)
        else:
            cmd.object = self._lister

        if cmd.validate():
            if cmd.uses_template():
                yamltemplate = verb_options.pop('yamltemplate', None)
                yamlvariables = verb_options.pop('yamlvariables', {})
                template = self.fill_template(yamltemplate, yamlvariables)
                for (k, v) in template.items():
                    if k not in verb_options and v is not None:
                        verb_options[k] = v
            return (cmd, cmd.execute(*verb_args, **verb_options))
        else:
            raise OVLibError("validation failed")

    def get(self, **kwargs):
        return self._lister.get(**kwargs)

    @property
    def api(self):
        return self._api

    @api.setter
    def api(self, api):
        self._api = api
        self._lister = self.__class__.list_wrapper(api)


type_wrappers={}
service_wrappers={}
writers={}


class AttributeWrapper(object):
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, objtype):
        if obj.dirty:
            obj.type = obj.api.follow_link(obj.type)
            obj.dirty = False
        return getattr(obj.type, self.name)


def wrapper(writer_class=None, type_class=None, service_class=None, other_methods = [], other_attributes = [], service_root=None):
    def decorator(func):
        func.writerClass = writer_class
        func.typeClass = type_class
        func.service_class = service_class
        for clazz in inspect.getmro(func):
            if clazz == ListObjectWrapper:
                func.service_root = service_root
                break
        func.methods = other_methods + ['remove', 'list', 'start', 'stop', 'statistics_service', 'update', 'add']
        for attribute in other_attributes + ['status', 'name', 'id']:
            if not hasattr(func, attribute):
                setattr(func, attribute, AttributeWrapper(attribute))
        if type_class is not None:
            type_wrappers[type_class] = func
        if service_class is not None:
            service_wrappers[service_class] = func
        if writer_class is not None:
            if type_class is not None:
                writers[type_class] = writer_class
            if service_class is not None:
                writers[service_class] = writer_class
        return func
    return decorator

native_type = type


def method_wrapper(object_wrapper, service, method):
    service_method = getattr(service, method)
    def check(*args, **kwargs):
        object_wrapper.dirty = True
        return service_method(*args, **kwargs)
    return check


class IteratorObjectWrapper(object):
    def __init__(self, api, parent_list):
        self.parent_list = parent_list
        self.api = api

    def __iter__(self):
        self.iterator = iter(self.parent_list)
        return self

    def next(self):
        next_object = self.iterator.next()
        return self.api.wrap(next_object)


@contextmanager
def event_waiter(api, object_filter, events, wait_for=[], break_on=[], timeout=1000, wait=1, verbose=False):
    # Works on copy, as we don't know where the arguments are coming from.
    break_on=map(lambda x: x.value, break_on)
    wait_for=map(lambda x: x.value, wait_for)
    def purge(x):
        try:
            wait_for.remove(x)
        except ValueError:
            pass
    events_service = ovlib.events.EventsWrapper(api)
    last_event = api.events.get_last()
    yield
    end_of_wait =  time.time() + timeout
    while True:
        search = '%s and %s' % (object_filter, " or ".join(map(lambda x: "type=%s" % x, set(wait_for + break_on))))
        if time.time() > end_of_wait:
            raise OVLibError("Timeout will waiting for events", value={'ids': wait_for})
        founds = events_service.list(
            from_= last_event,
            search=search,
        )
        if len(founds) > 0:
            last_event = int(founds[-1].id)
            founds = api.wrap(founds)
            events += founds
            if verbose:
                for j in founds:
                    print "%s" % j.export(['description']).strip()
            stop_id = filter(lambda x: x in break_on, map(lambda x: int(x.code), founds))
            if len(stop_id) > 0:
                break
            map(purge, map(lambda x: int(x.code), founds))
            if len(wait_for) == 0:
                break
        time.sleep(wait)


class ObjectWrapper(object):
    """This object wrapper the writer, the type and the service in a single object than can access all of that"""

    @staticmethod
    def make_wrapper(api, detect):
        """Try to resolve the wrapper, given a type, or a service or a list."""
        if detect is None or isinstance(detect, ObjectWrapper):
            return detect
        # If detect was given, it will override any other given values and find the good one
        type = None
        service = None
        list = None
        if isinstance(detect, ovirtsdk4.Struct):
            type = detect
        elif isinstance(detect, ovirtsdk4.service.Service):
            service = detect
        elif isinstance(detect, ovirtsdk4.List):
            list = detect
        else:
            return detect
        if service is None:
            if isinstance(type, ovirtsdk4.Struct) and type.href is not None:
                service = api.resolve_service_href(type.href)
            elif isinstance(list, ovirtsdk4.List) and list.href is not None:
                service = api.resolve_service_href(list.href)
        wrapper = None
        if service is not None:
            service_class = native_type(service)
            if service_wrappers.has_key(service_class):
                wrapper = service_wrappers[service_class]
        elif type is not None:
            type_class = native_type(type)
            if type_wrappers.has_key(type_class):
                wrapper = type_wrappers[type_class]
        if wrapper is not None:
            if issubclass(wrapper, ListObjectWrapper):
                return wrapper(api=api, list=list, service=service)
            else:
                return wrapper(api=api, service=service, type=type)
        elif list is not None:
            # We found a wrapper, but no service, it's just a plain list, wraps the content
            return IteratorObjectWrapper(api, list)

         # nothing succeded to find the wrapper, return None
        raise OVLibError("failed to wrap an object" , {'type': type, 'service': service, 'list': list})

    def __init__(self, api, type=None, service=None):
        self.api = api
        self._is_enumerator = False
        if type is None and not isinstance(self, ListObjectWrapper):
            self.type = service.get()
            self.dirty = False
        else:
            self.type = type
            # type is taken directly, it might not have been resolved
            self.dirty = True
        if service is None:
            self.service = api.resolve_service_href(type.href)
        else:
            self.service = service
        for method in self.__class__.methods:
            if hasattr(self.service, method) and not hasattr(self, method):
                setattr(self, method, method_wrapper(self, self.service, method))

        if self.service is not None:
            for method in dir(self.service):
                if method.endswith("s_service") and not method.startswith("_") and not method == "qos_service":
                    service_name = method.replace("_service", "")
                    if not hasattr(self, service_name):
                        try:
                            services_method = getattr(self.service, method)()
                            setattr(self, service_name, self.api.wrap(services_method))
                        except OVLibError:
                            setattr(self, service_name, getattr(self.service, method)())


    def export(self, path=[]):
        buf = None
        writer = None
        if len(path) == 0 and self.writerClass is not None:
            try:
                buf = io.BytesIO()
                writer = xml.XmlWriter(buf, indent=True)
                self.writerClass.write_one(self.type, writer)
                writer.flush()
                return buf.getvalue()
            finally:
                if writer is not None:
                    writer.close()
                if buf is not None:
                    buf.close()
        elif len(path) == 0:
            raise OVLibError("Unexportable class, missing writer class: %s" % type(self))
        else:
            next=path[0]
            if hasattr(self.type, next):
                next_type = getattr(self.type, next)
                next_wrapper = self.api.wrap(next_type)
                if next_wrapper is not None and hasattr(next_wrapper, 'export'):
                    return next_wrapper.export(path[1:])
                elif isinstance(next_wrapper, collections.Iterable) and not isinstance(next_wrapper, (str, unicode)):
                    # yes, a string is iterable in python, not funny
                    buf = ""
                    for i in next_type:
                        if i is None:
                            return ""
                        i_wrapper = self.api.wrap(i)
                        if hasattr(i_wrapper, 'export'):
                            buf += "%s" % i_wrapper.export(path[1:])
                        else:
                            buf += str(next_type) + "\n"
                    return buf
                else:
                    return str(next_type) + "\n"
            else:
                raise OVLibError("Attribute %s missing in %s" % (next, self))

    def wait_for(self, status, wait=1):
        while True:
            self.type = self.api.follow_link(self.type)
            self.dirty = False
            if self.status == status:
                return
            else:
                time.sleep(wait)

    def update(self):
        if self.type is not None:
            self.service.update(self.type)

    def __str__(self):
        return "%s<%s>" % (type(self).__name__, "" if self.type is None else self.type.href)

    @property
    def is_enumerator(self):
        return self._is_enumerator


class ListObjectWrapper(ObjectWrapper):

    def __init__(self, api, list=None, service=None):
        if list is not None:
            service = api.resolve_service_href(list.href)
        elif service is None:
            service = api.service(self.__class__.service_root)
        super(ListObjectWrapper, self).__init__(api, service=service)
        self._is_enumerator = True

    def get(self, **kwargs):
        """
        Search for the entity by attributes. Nested entities don't support search
        via REST, so in case using search for nested entity we return all entities
        and filter them by specified attributes.
        """
        if 'id' in kwargs:
            service = self.api.service("%s/%s" % (self.__class__.service_root, kwargs['id']))
            return self.api.wrap(service)
        # Check if 'list' method support search(look for search parameter):
        elif 'search' in inspect.getargspec(self.service.list)[0]:
            res = self.service.list(
                search=' and '.join('{}={}'.format(k, v) for k, v in kwargs.items())
            )
        else:
            res = [
                e for e in self.service.list() if len([
                    k for k, v in kwargs.items() if getattr(e, k, None) == v
                ]) == len(kwargs)
            ]
        if len(res) == 1:
            search_type = res[0]
            if search_type is not None:
                return self.api.wrap(search_type)
            else:
                return OVLibError("Invalid object found matching the search")
        elif len(res) == 0:
            raise OVLibError("no object found matching the search")
        else:
            raise OVLibError("Too many objects found matching the search")

    def __iter__(self):
        for i in self.list():
            yield self.api.wrap(i)

    def export(self, path=[]):
        buf = ""
        for i in self.list():
            next_wrapper = self.api.wrap(i)
            if next_wrapper is not None:
                buf += "%s" % next_wrapper.export(path)
        return buf

    def __str__(self):
        return "%s<%s>" % (type(self).__name__, "" if self.service is None else self.service._path)



import ovlib.events
import ovlib.vms
import ovlib.datacenters
import ovlib.disks
import ovlib.capabilities
import ovlib.hosts
import ovlib.network
import ovlib.macpools
import ovlib.system
import ovlib.users
import ovlib.templates
import ovlib.clusters
import ovlib.operatingsystem
import ovlib.storages
import ovlib.disks
#import ovlib.permissions
