import optparse
import time
import string
import io

from ovlib.template import VariableOption
from ovlib import OVLibErrorNotFound, is_id, OVLibError
from ovirtsdk4 import types, Struct
from ovirtsdk4.writer import Writer
from ovirtsdk4 import xml

# Find the best implementation available on this platform
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

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
        if self.object is None:
            return False
        else:
            return True

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
            print "success"
        else:
            print value

    def get(self, source, common=None, name=None, id=None):
        # if common is set, get was called with a single positionnal argument
        # try to be smart and detect it's type
        search=None
        if isinstance(common, ObjectExecutor):
            return common.type
        elif isinstance(common, Struct):
            return common
        elif common is not None and is_id(common):
            id = common
            name = None
            search ="id=%s" % id
        elif common is not None and isinstance(common, basestring):
            id = None
            name = common
            search ="name=%s" % name

        if isinstance(source, basestring):
            source = getattr(self.system_service(), source)

        # reach this point, so still needs resolution
        # but name and id contains expect type
        founds = source.list(search=search, case_sensitive=True)
        if len(founds) == 0:
            raise OVLibErrorNotFound("%s(name='%s', id=%s) not found" % (source, name, id))
        else:
            return founds[0]

    def status(self):
        """A default status command to run on success"""
        return 0;


class List(Verb):
    verb = "list"
    template = "{name!s} {id!s}"

    def validate(self,  *args, **kwargs):
        return True

    def fill_parser(self, parser):
        super(List, self).fill_parser(parser)
        parser.add_option("-q", "--query", dest="query")
        parser.add_option("-t", "--template", dest="template", help="template for output formatting, default to %s" % self.template)

    def execute(self, *args, **kwargs):
        self.template = kwargs.pop('template', self.template)

        for i in self.object.list(**kwargs):
            yield i

    def get_service_path(self, *args, **kwargs):
        return self.object.service_root

    def to_str(self, status):
        formatter = string.Formatter()
        values = {}
        for i in formatter.parse(self.template):
            values[i[1]] = getattr(status, i[1])
        return  "%s\n" %(formatter.format(self.template, **values))


class XmlExport(Verb):
    verb = "export"

    def execute(self, *args, **kwargs):
        return self.object.export(args)


class Statistics(Verb):
    verb = "statistics"

    def execute(self, *args, **kwargs):
        for s in self.object.statistics_service().list():
            yield s

    def to_str(self, stat):
        return "%s: %s %s (%s)\n" % (stat.name, stat.values[0].datum, stat.unit, stat.type)

class Create(Verb):
    verb = "create"

    def validate(self):
        return True


class Remove(Verb):
    verb = "remove"

    def execute(self, *args, **kwargs):
        return self.object.remove()


class RemoveForce(Remove):

    def fill_parser(self, parser):
        parser.add_option("-f", "--force", dest="force", help="Force", default=False, action='store_true')


    def execute(self, *args, **kwargs):
        action_params = types.Action(
            # force a True/False content
            force=kwargs['force'] is True,
        )
        return self.object.delete(action_params)

class Update(Verb):
    verb = "update"

    def validate(self):
        if getattr(self, 'param_name') is None:
            raise OVLibError("invalid verb definition, missing param_name")
        return super(Update, self).validate()

    def execute(self, *args, **kwargs):
        return self.object.update()
