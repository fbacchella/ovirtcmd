import string
import yaml
import sys
import optparse


try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


# a template that allows . in variables name
class DotTemplate(string.Template):
    pattern = r"""
    \$(?:
      {(?P<braced>[_a-z][_a-z0-9\.]*)}     |   # delimiter and a braced identifier
      (?P<escaped>^$)                      |   # Escape sequence of two delimiters
      (?P<named>^$)                        |   # delimiter and a Python identifier
      (?P<invalid>^$)                          # Other ill-formed delimiter exprs
    )
    """


# A dictionary that resolve string using a template and variables
class TemplateDict(dict):

    def __init__(self, variables, *args, **kwargs):
        self.variables = variables
        super(TemplateDict, self).__init__(*args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        value = super(TemplateDict, self).__getitem__(*args, **kwargs)
        return self.resolve(value)

    def items(self):
        for (key, value) in super(TemplateDict, self).items():
            yield (key, self.resolve(value))

    def iteritems(self):
        for (key, value) in super(TemplateDict, self).iteritems():
            yield (key, self.resolve(value))

    def pop(self, key, default=None):
        value = super(TemplateDict, self).pop(key, default)
        return self.resolve(value)

    def resolve(self, value):
        if isinstance(value, str):
            return DotTemplate(value).substitute(self.variables)
        elif isinstance(value, (list, tuple)):
            return map(lambda x: self.resolve(x), value)
        elif isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.iteritems()}
        else:
            return value

    def getraw(self, key):
        return super(TemplateDict, self).__getitem__(key)


class VariableOption(optparse.Option):
    ACTIONS = optparse.Option.ACTIONS + ("store_first", "store_variable", )
    STORE_ACTIONS = optparse.Option.STORE_ACTIONS + ("store_first", "store_variable", )
    TYPED_ACTIONS = optparse.Option.TYPED_ACTIONS + ("store_first", "store_variable", )
    ALWAYS_TYPED_ACTIONS = optparse.Option.ALWAYS_TYPED_ACTIONS + ("store_first", "store_variable", )

    def __init__(self, *args, **kwargs):
        if 'action' in kwargs:
            if kwargs['action'] == "store_variable":
                kwargs['nargs'] = 2
                if not 'default' in kwargs:
                    kwargs['default'] = {}
            elif kwargs['action'] == "store_first":
                self.seen = set([])
        optparse.Option.__init__(self, *args, **kwargs)

    def take_action(self, action, dest, opt, value, values, parser):
        if action == "store_first" and dest in self.seen:
            pass
        elif action == "store_variable":
            (v_key, v_value) = value
            getattr(values, dest)[v_key] = v_value
        else:
            if action == "store_first":
                self.seen.add(dest)
                action = "store"
            optparse.Option.take_action(self, action, dest, opt, value, values, parser)


def load_template(template, variables):
    # Load the yaml docker file
    with open(template, 'r') as docker_file:
        try:
            yaml_template = yaml.safe_load(docker_file)
        except (yaml.scanner.ScannerError, yaml.parser.ParserError) as e:
            print >> sys.stderr, e
            return None
    return TemplateDict(variables, yaml_template)
