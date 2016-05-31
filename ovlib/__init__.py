import re
from ovlib.template import load_template, DotTemplate
import ovirtsdk.infrastructure.errors

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


objects = { }
objects_by_class = { }

all_libs = (
    'vms',
    'datacenters',
    'templates',
    'disks',
    'capabilities',
    'hosts',
    'clusters',
    'storages',
    'network',
    'permissions',
    'generics',
)


def add_command(destination):
    def decorator(func):
        destination.append(func)
        return func
    return decorator


class ObjectContext(object):

    def __init__(self, object_name, api_attribute, commands, broker_class):
        self.verbs = {}
        for command in commands:
            verb_name = command.verb
            self.verbs[verb_name] = command
        self.api_attribute = api_attribute
        self.commands = commands
        self.object_name = object_name
        self.api = None
        self.broker_class = broker_class

    def fill_parser(self, parser):
        parser.add_option("-i", "--id", dest="id", help="object ID")
        parser.add_option("-n", "--name", dest="name", help="object tag 'Name'")

    def execute(self, name, method_args=[], method_kwargs={}):
        if self.api_attribute is not None:
            return getattr(getattr(self.api, self.api_attribute), name)(*method_args, **method_kwargs)
        else:
            NameError('Not implemented')

    def get_cmd(self, verb):
        if verb in self.verbs:
            cmd_class = self.verbs[verb]
            cmd = cmd_class(self.api)
            return cmd
        else:
            # Everything failed so return false
            return False

    def fill_template(self, template, variables):
        if template is None:
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
        if cmd.broker is None:
            try:
                cmd.broker = self.get(**object_options)
            except ovirtsdk.infrastructure.errors.AmbiguousQueryError as e:
                raise OVLibError(e.message)
        if self.api_attribute is not None:
            cmd.contenaire = getattr(self.api, self.api_attribute)
        else:
            cmd.contenaire = None
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
        if len(kwargs) > 0:
            return self.execute("get", method_kwargs=kwargs)
        else:
            return None


for lib in all_libs:
    cmd_module = __import__(lib, globals(), locals(), [], -1)
    for attr_name in dir(cmd_module):
        attr = getattr(cmd_module, attr_name)
        if isinstance(attr, ObjectContext):
            object_name = attr.object_name
            if not object_name in objects and object_name is not None:
                objects[object_name] = attr
            elif object_name is not None:
                print "dual definition of objects %s" % object_name
            # Can accept many class type because of duck typing
            if isinstance(attr.broker_class, (tuple, list)):
                for i in attr.broker_class:
                    objects_by_class[i] = attr
            else:
                objects_by_class[attr.broker_class] = attr
