import re
from ovlib.template import load_template, DotTemplate

class OVLibError(Exception):
    def __init__(self, value):
        self.value = value
        self.error_message = value

    def __str__(self):
        return repr(self.value)

class OVLibErrorNotFound(Exception):
    def __init__(self, value):
        self.value = value
        self.error_message = value

    def __str__(self):
        return repr(self.value)

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
    matcher = size_re.match("%s" % input_size)
    if matcher is not None:
        value = float(matcher.group(1))
        suffix = matcher.group(2)
        if suffix == '' and default_suffix is not None:
            suffix = default_suffix
        return value * units[suffix] / units[out_suffix]

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
    'users',
    'generics',
)

def add_command(destination):
    def decorator(func):
        destination.append(func)
        return func
    return decorator

class Object_Context(object):

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
            verb_options = vars(verb_options)
            # removed undeclared arguments
            for (k, v) in verb_options.items():
                if v is None:
                    del verb_options[k]
            return self.execute_phrase(cmd, object_options, verb_options, verb_args)
        else:
            # Nothing done, return nothing
            return (None, None)


    def execute_phrase(self, cmd, object_options={}, verb_options={}, verb_args=[]):
        if cmd.broker is None:
            cmd.broker = self.get(**object_options)
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
                    if k not in verb_options or v is None:
                        verb_options[k] = v
            return (cmd, cmd.execute(*verb_args, **verb_options))
        else:
            # Nothing done, return nothing
            return (None, None)

    def get(self, **kwargs):
        if len(kwargs) >0:
            return self.execute("get", method_kwargs=kwargs)
        else:
            return None


for lib in all_libs:
    cmd_module = __import__(lib, globals(), locals(), [], -1)
    for attr_name in dir(cmd_module):
        attr = getattr(cmd_module, attr_name)
        if isinstance(attr, Object_Context):
            object_name = attr.object_name
            if not object_name in objects and object_name is not None:
                objects[object_name] = attr
            elif object_name is not None:
                print "dual definition of objects %s" % object_name
            objects_by_class[attr.broker_class] = attr
