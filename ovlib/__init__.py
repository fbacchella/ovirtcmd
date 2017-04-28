import re
from ovlib.template import load_template, DotTemplate
import ovirtsdk4
import inspect
import io
import time

import ovirtsdk4.writers
import ovirtsdk4.types

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

all_libs = (
    'vms',
    'datacenters',
#    'templates',
    'disks',
    'capabilities',
    'hosts',
#    'clusters',
#    'storages',
    'network',
#    'permissions',
#    'generics',
)


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
        func.methods = other_methods + ['delete', 'list', 'start', 'stop', 'statistics_service', 'update']
        for attribute in other_attributes + ['status', 'name']:
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


class ObjectWrapper(object):
    """This object wrapper the writer, the type and the service in a single object than can access all of that"""

    @staticmethod
    def make_wrapper(api, type=None, service=None):
        """Try to resolve the wrapper, given a type, or a service."""
        if service is None and type is None:
            return None
        if service is None:
            if type is not None and hasattr(type, 'href'):
                if type.href is not None:
                    service = api.resolve_service_href(type.href)
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
            return wrapper(api=api, service=service, type=type)
         # nothing succeded to find the wrapper, return None
        return None

    def __init__(self, api, type=None, service=None):
        self.api = api
        if hasattr(service, "list"):
            self._is_enumerator = True
        else:
            self._is_enumerator = False
        if type is None and not self._is_enumerator:
            self.type = service.get()
        else:
            self.type = type
        if service is None:
            self.service = api.resolve_service_href(type.href)
        else:
            self.service = service
        self.dirty = False
        for method in self.__class__.methods:
            if hasattr(self.service, method):
                setattr(self, method, method_wrapper(self, self.service, method))

    def export(self, path):
        buf = None
        writer = None
        if self.is_enumerator:
            buf = ""
            for i in self.list():
                next_wrapper = ObjectWrapper.make_wrapper(self.api, i)
                if next_wrapper is not None:
                    buf += "%s\n" % next_wrapper.export(path)
            return buf
        elif len(path) == 0:
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
        else:
            next=path[0]
            if hasattr(self.type, next):
                next_type = getattr(self.type, next)
                next_wrapper = ObjectWrapper.make_wrapper(self.api, type=next_type)
                if next_wrapper is not None:
                    return next_wrapper.export(path[1:])
                elif isinstance(next_type, List) and len(next_type) > 0:
                    buf = ""
                    for i in next_type:
                        i_class = type(i)
                        if type_wrappers.has_key(i_class):
                            next_wrapper = type_wrappers[i_class](api=self.api, type=i)
                            buf += "%s\n" % next_wrapper.export(path[1:])
                    return buf
                elif not hasattr(next_type, 'href'):
                    return str(next_type)
                else:
                     print "no way to export %s" % next_type
                     return ""
            else:
                return ""

    def wait_for(self, status, wait=1):
        while True:
            self.type = self.api.follow_link(self.type)
            self.dirty = False
            if self.status == status:
                return
            else:
                time.sleep(wait)

    @property
    def is_enumerator(self):
        return self._is_enumerator


class ListObjectWrapper(ObjectWrapper):

    def __init__(self, api):
        super(ListObjectWrapper, self).__init__(api, service=api.service(self.__class__.service_root))

    def get(self, **kwargs):
        """
        Search for the entity by attributes. Nested entities don't support search
        via REST, so in case using search for nested entity we return all entities
        and filter them by specified attributes.
        """
        if 'id' in kwargs:
            service = self.api.service("%s/%s" % (self.__class__.service_root, kwargs['id']))
            return ObjectWrapper.make_wrapper(self.api, service=service)
        # Check if 'list' method support search(look for search parameter):
        elif 'search' in inspect.getargspec(self.service.list)[0]:
            res = self.service.list(
                search=' and '.join('{}={}'.format(k, v) for k, v in kwargs.items())
            )
            print res
        else:
            res = [
                e for e in self.service.list() if len([
                    k for k, v in kwargs.items() if getattr(e, k, None) == v
                ]) == len(kwargs)
            ]
        if len(res) == 1:
            search_type = res[0]
            if search_type is not None:
                return ObjectWrapper.make_wrapper(api=self.api, type=search_type)
            else:
                return OVLibError("Invalid object found matching the search")
        elif len(res) == 0:
            raise OVLibError("no object found matching the search")
        else:
            raise OVLibError("Too many objects found matching the search")


for lib in all_libs:
    __import__(lib, globals(), locals(), [], -1)

