import optparse
import string

from ovlib.template import VariableOption
from ovlib import OVLibError
from ovlib.wrapper import ObjectWrapper

# Find the best implementation available on this platform
try:
    from io import StringIO
except:
    from io import StringIO


class Verb(object):
    """A abstract class, used to implements actual verb"""
    def __init__(self, dispatcher):
        self.api = dispatcher.api
        self.dispatcher = object
        self.object = None

    def fill_parser(self, parser):
        pass

    def validate(self):
        """try to validate the object needed by the commande, should be overriden if the no particular object is expected"""
        return isinstance(self.object, ObjectWrapper)

    def uses_template(self):
        return False

    def parse(self, args):
        parser = optparse.OptionParser(option_class=VariableOption, usage=self.__doc__)
        if self.uses_template():
            parser.add_option("-V", "--variable", dest="yamlvariables", action="store_variable", type="string")
            parser.add_option("-T", "--template", dest="yamltemplate", default=None)
        self.fill_parser(parser)

        (verb_options, verb_args) = parser.parse_args(args)
        return (verb_options, verb_args)

    def execute(self, *args, **kwargs):
        raise NameError('Not implemented')

    def to_str(self, value):
        if value is True:
            return "success"
        else:
            return str(value)

    def get(self, lister, **kwargs):
        return lister.get(**kwargs)

    def status(self):
        """A default status command to run on success"""
        return 0;


class RepeterVerb(Verb):

    def validate(self, *args, **kwargs):
        return self.object is not None

    def get(self, lister, **kwargs):
        return lister.list(**kwargs)


class List(RepeterVerb):
    verb = "list"
    template = "{name!s} {id!s}"

    def fill_parser(self, parser):
        super(List, self).fill_parser(parser)
        parser.add_option("-t", "--template", dest="template", help="template for output formatting, default to %s" % self.template)

    def execute(self, template=None):
        if template is not None:
            self.template = template

        for i in self.object:
            yield i

    def to_str(self, item):
        formatter = string.Formatter()
        values = {}
        for i in formatter.parse(self.template):
            values[i[1]] = getattr(item, i[1])
        return  "%s" %(formatter.format(self.template, **values))


class XmlExport(RepeterVerb):
    verb = "export"

    def execute(self, *args):
        for i in self.object:
            yield i.export(args).strip()

    def to_str(self, item):
        return item


class Statistics(Verb):
    verb = "statistics"

    def execute(self, *args, **kwargs):
        for s in self.object.statistics.list():
            yield s

    def to_str(self, stat):
        return "%s: %s %s (%s)" % (stat.name, stat.values[0].datum, stat.unit, stat.type)


class Create(Verb):
    verb = "create"

    def validate(self):
        return True

    def get(self, lister, **kwargs):
        return lister


class Remove(Verb):
    verb = "remove"

    def execute(self, *args, **kwargs):
        return self.object.remove()


class RemoveForce(Remove):

    def fill_parser(self, parser):
        parser.add_option("-f", "--force", dest="force", help="Force", default=False, action='store_true')


    def execute(self, *args, **kwargs):
        return self.object.remove(**kwargs)


class Update(Verb):
    verb = "update"

    def validate(self):
        if getattr(self, 'param_name') is None:
            raise OVLibError("invalid verb definition, missing param_name")
        return super(Update, self).validate()

    def execute(self, *args, **kwargs):
        return self.object.update()


class WaitFor(Verb):
    verb = "waitfor"

    def fill_parser(self, parser):
        parser.add_option("-s", "--status", dest="status", help="The status to wait for")

    def execute(self, status=None):
        if status is None:
            raise OVLibError("No status given to wait")
        if hasattr(type(self.object.status), status.upper()):
            self.object.wait_for(getattr(type(self.object.status), status.upper()))
            return True
        else:
            raise OVLibError("Unknown status %s" % status)


class Permission(Verb):
    verb = "permissions"

    def fill_parser(self, parser):
        parser.add_option("-i", "--id", dest="id")
        parser.add_option("-n", "--name", dest="name")
        parser.add_option("-r", "--role", dest="role")
        parser.add_option("-g", "--group", dest="group")
        parser.add_option("-u", "--user", dest="user")

    def execute(self, action, role=None, group=None, user=None):
        if action == 'add':
            return self.object.permissions.add(role=role, group=group, user=user)
