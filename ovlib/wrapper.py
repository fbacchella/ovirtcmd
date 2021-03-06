import inspect
import io
import time
import collections
from enum import EnumMeta
import inspect

import ovirtsdk4
import ovirtsdk4.writers
import ovirtsdk4.types

from ovirtsdk4 import xml, Struct
from ovirtsdk4.types import Identified
from ovirtsdk4.service import Future
from ovirtsdk4.services import HostService

from ovlib import OVLibError, OVLibErrorNotFound, is_id


type_wrappers={}
service_wrappers={}
writers={}


class AttributeWrapper(object):
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, objtype):
        if obj.dirty:
            obj.refresh()
        return getattr(obj.type, self.name)


def wrapper(writer_class=None, type_class=None, service_class=None, other_methods = [], other_attributes = [], service_root=None, name_type_mapping={}):
    def decorator(func):
        parent_class = func.__bases__[0]
        if writer_class is not None:
            func.writer_class = writer_class
        elif hasattr(parent_class, 'writer_class'):
            func.writer_class = parent_class.writer_class
        if type_class is not None:
            func.type_class = type_class
        elif hasattr(parent_class, 'type_class'):
            func.type_class = parent_class.type_class
        if service_class is not None:
            func.service_class = service_class
        elif hasattr(parent_class, 'service_class'):
            func.service_class = parent_class.service_class
        func.name_type_mapping = {}
        if hasattr(parent_class, 'name_type_mapping'):
            func.name_type_mapping.update(parent_class.name_type_mapping)
        func.name_type_mapping.update(name_type_mapping)

        # check if it inherits of ListObjectWrapper
        if ListObjectWrapper in inspect.getmro(func):
            func.service_root = service_root

        # Analyzing methods
        func.methods = []
        func.methods += other_methods
        if hasattr(parent_class, 'methods'):
            func.methods += filter(lambda x: x not in func.methods, parent_class.methods)
        func.methods += filter(lambda x: x not in func.methods, ['remove', 'list', 'start', 'stop', 'update', 'add'])

        # Analyzing attributes
        func.attributes = []
        func.attributes += other_attributes
        if hasattr(parent_class, 'other_attributes'):
            func.attributes += filter(lambda x: x not in func.attributes, parent_class.attributes)
        func.attributes += filter(lambda x: x not in func.attributes, ['status', 'name', 'id', 'comment'])
        for attribute in func.attributes:
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
    "This class try to mimim some aspect of a ListObjectWrapper, but don't expect too much from it"
    def __init__(self, api, parent_list):
        self.parent_list = parent_list
        self.api = api

    def __iter__(self):
        # __iter__ return wrapped list content
        for i in self.parent_list:
            yield self.api.wrap(i)

    def list(self):
        # list method is not expect to return a wrapped object
        return self.parent_list

    def export(self, path=[]):
        buf = ""
        for i in self.parent_list:
            if i is None:
                return ""
            i_wrapper = self.api.wrap(i)
            if hasattr(i_wrapper, 'export'):
                buf += "%s" % i_wrapper.export(path)
            else:
                buf += str(i) + "\n"
        return buf


class FuturWrapper(object):

    def __init__(self, context, futur):
        self.futur = futur
        self.context = context

    def wait(self):
        content = self.futur.wait()
        return self.context.wrap(content)

    def __str__(self):
        return "%s" % (self.futur)


class ObjectWrapper(object):
    """This object wrapper the writer, the type and the service in a single object than can access all of that"""

    @staticmethod
    def make_wrapper(api, detect):
        """Try to resolve the wrapper, given a type, or a service or a list."""
        if detect is None or isinstance(detect, ObjectWrapper) or isinstance(detect, IteratorObjectWrapper):
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
        elif isinstance(detect, collections.Iterable) and not isinstance(detect, str):
            list = detect
        elif isinstance(detect, Future):
            return FuturWrapper(api, detect)
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
            if service_class in service_wrappers:
                wrapper = service_wrappers[service_class]
        elif type is not None:
            type_class = native_type(type)
            if type_class in type_wrappers:
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
        if type is None and not isinstance(self, ListObjectWrapper):
            self.type = service.get()
            self.dirty = False
        else:
            self.type = type
        # type is taken directly, it might not have been resolved
        # but some types have not href (like tickets), they will never be dirty
        if self.type is not None and self.type.href is not None:
            self.dirty = True
        else:
            self.dirty = False
        if service is None and self.type is not None and self.type.href is not None:
            self.service = api.resolve_service_href(type.href)
        else:
            self.service = service
        for method in self.__class__.methods:
            if hasattr(self.service, method) and not hasattr(self, method):
                setattr(self, method, method_wrapper(self, self.service, method))

        for method in dir(self.service):
            if method.startswith("_"): continue
            if method == "qos_service": continue
            if method == 'storage_service' and not isinstance(self.service, HostService): continue
            if (method.endswith("s_service") or method == 'storage_service'):
                service_name = method.replace("_service", "")
                if not hasattr(self, service_name):
                    try:
                        services_method = getattr(self.service, method)()
                        setattr(self, service_name, self.api.wrap(services_method))
                    except OVLibError:
                        setattr(self, service_name, getattr(self.service, method)())
            elif method == 'add':
                self.add = self._add
            elif method == 'update':
                self.update = self._update

    def export(self, path=[]):
        buf = None
        writer = None
        if len(path) == 0 and self.writer_class is not None:
            self.refresh()
            try:
                buf = io.BytesIO()
                writer = xml.XmlWriter(buf, indent=True)
                self.writer_class.write_one(self.type, writer)
                writer.flush()
                return buf.getvalue().decode('utf-8', 'replace')
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
                self.refresh()
                next_type = getattr(self.type, next)
                next_wrapper = self.api.wrap(next_type)
                if next_wrapper is not None and hasattr(next_wrapper, 'export'):
                    return next_wrapper.export(path[1:])
                elif isinstance(next_wrapper, collections.Iterable) and not isinstance(next_wrapper, (str, bytes)):
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
        if not isinstance(status, collections.Iterable):
            status = (status, )
        while True:
            self.type = self.api.follow_link(self.type)
            self.dirty = False
            if self.status in status:
                return
            else:
                time.sleep(wait)

    @staticmethod
    def _map_dict(name_type_mapping, d):
        return {k: ObjectWrapper._transform_arg_type(name_type_mapping, k, v) for k, v in d.items()}

    @staticmethod
    def _transform_arg_type(name_type_mapping, k, v):
        name_type = name_type_mapping.get(k, None)
        name_type_wrapper = type_wrappers.get(name_type)
        if v is None:
            t = None
        elif isinstance(v, ObjectWrapper):
            t = v.type
        elif isinstance(v, str) and isinstance(name_type, EnumMeta):
            try:
                t = name_type(v)
            except ValueError:
                try:
                    t = name_type[v]
                except KeyError:
                    raise OVLibError("invalid name %s for %s" % (v, name_type.__name__))
        elif isinstance(v, str) and hasattr(name_type, 'name'):
            t = name_type(name=v)
        elif isinstance(v, dict) and name_type_wrapper is not None:
            try:
                mapped_kwargs = ObjectWrapper._map_dict(name_type_wrapper.name_type_mapping, v)
                t = name_type_mapping[k](**mapped_kwargs)
            except TypeError as e:
                raise OVLibError("Incomplete type mapping for %s(%s): %s" % (name_type_mapping[k], mapped_kwargs, e), exception=e)
        elif isinstance(v, collections.Iterable) and not isinstance(v, str) and not isinstance(v, dict):
            t = list(map(lambda x: ObjectWrapper._transform_arg_type(name_type_mapping, k, x), v))
        else:
            t = v
        return t

    def _wrap_call(self, method_name, *args, wait=True, **kwargs):
        kwargs = ObjectWrapper._map_dict(self.name_type_mapping, kwargs)
        method = getattr(self.service, method_name)
        return self.api.wrap(method(*args, wait=wait, **kwargs))

    def _add(self, *args, **kwargs):
        return self._wrap_call('add', *args, **kwargs)

    def _update(self, *args, **kwargs):
        return self._wrap_call('update', *args, **kwargs)

    def __str__(self):
        return "%s<%s>" % (type(self).__name__, "" if self.service is None else self.service._path[1:])

    def refresh(self):
        if (self.type is not None):
            self.type = self.api.follow_link(self.type)
        self.dirty = False

    def get_type_name(self):
        return type(self.type).__name__.lower()


class ListObjectWrapper(ObjectWrapper):

    def __init__(self, api, list=None, service=None):
        if list is not None:
            service = api.resolve_service_href(list.href)
        elif service is None:
            service = api.service(self.__class__.service_root)
        super(ListObjectWrapper, self).__init__(api, service=service)

    def get(self, *args, **kwargs):
        # If one arg was given, try to detect what is is and add it to kwargs
        if (len(args) == 1):
            if hasattr(self, 'wrapper') and isinstance(args[0], self.wrapper):
                return args[0]
            elif is_id(args[0]):
                kwargs['id'] = args[0]
            elif isinstance(args[0], str):
                kwargs['name'] = args[0]
            return self.get(**kwargs)
        res = self._do_query(**kwargs)
        if len(res) == 0:
            raise OVLibErrorNotFound("no object found matching the search %s" % (kwargs))
        elif len(res) > 1:
            raise OVLibError("Too many objects found matching the search %s" % (kwargs))
        else:
            return self.api.wrap(res[0])

    def list(self, **kwargs):
        for i in self._do_query(**kwargs):
            if i is not None:
                yield self.api.wrap(i)

    def _do_query(self, search=None, id=None, **kwargs):
        """
        Search for the entity by attributes. Nested entities don't support search
        via REST, so in case using search for nested entity we return all entities
        and filter them by specified attributes.
        """

        if id is not None:
            service = self.api.service("%s/%s" % (self.service._path[1:], id))
            return [service]
        else:
            search_keys = set(kwargs.keys()) - set(inspect.getargspec(self.service.list).args)
            search_args = {k: kwargs[k] for k in search_keys if kwargs[k] is not None}
            list_args = {k: kwargs[k] for k in (set(kwargs.keys()) -  search_keys) if kwargs[k] is not None}
            if 'search' in inspect.getargspec(self.service.list)[0]:
                # Check if 'list' method support search(look for search parameter):
                if search is None and len(search_args) > 0:
                    search = ' and '.join('{}={}'.format(k, v) for k, v in list(search_args.items()))
                res = self.service.list(search=search, **list_args)
            else:
                res = [
                    e for e in self.service.list() if len([
                        k for k, v in list(kwargs.items()) if getattr(e, k, None) == v
                    ]) == len(kwargs)
                ]
            return res

    def export(self, path=[], **kwargs):
        buf = ""
        for i in self.list(**kwargs):
            next_wrapper = self.api.wrap(i)
            if next_wrapper is not None:
                buf += "%s" % next_wrapper.export(path)
        return buf

    def __str__(self):
        return "%s<%s>" % (type(self).__name__, "" if self.service is None else self.service._path[1:])
