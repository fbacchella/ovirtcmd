import optparse
import time
from ovlib.template import VariableOption
from ovlib.context import ObjectExecutor
from ovirtsdk.infrastructure.common import Base
from ovlib import OVLibErrorNotFound, is_id
from ovirtsdk.xml import params

# Find the best implementation available on this platform
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

class Verb(object):
    """A abstract class, used to implements actual verb"""
    def __init__(self, api, broker=None):
        self.api = api
        self.broker = broker

    def fill_parser(self, parser):
        pass

    def validate(self):
        """try to validate the object needed by the commande, should be overriden if the no particular object is expected"""
        if self.broker is None:
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

    def wait_for(self, status, wait=1):
        while True:
            self.broker = self.contenaire.get(id=self.broker.id)
            if self.broker.status.state == status:
                return
            else:
                time.sleep(wait)

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
        if isinstance(common, ObjectExecutor):
            return common.broker
        elif isinstance(common, Base):
            return common
        elif common is not None and is_id(common):
            id = common
            name = None
        elif common is not None and isinstance(common, basestring):
            id = None
            name = common

        if isinstance(source, basestring):
            source = getattr(self.api, source)

        # reach this point, so still needs resolution
        # but name and id contains expect type
        found = source.get(name=name, id=id)
        if found is None:
            raise OVLibErrorNotFound("%s(name='%s', id=%s) not found" % (source, name, id))
        else:
            return found

    def status(self):
        """A default status command to run on success"""
        return 0;

    def _export(self, object):
        output = StringIO()
        object.export_(output, 0)
        return output.getvalue()


class List(Verb):
    verb = "list"
    template = "%(name)s %(id)s"

    def validate(self,  *args, **kwargs):
        return True

    def fill_parser(self, parser):
        super(List, self).fill_parser(parser)
        parser.add_option("-q", "--query", dest="query")
        parser.add_option("-t", "--template", dest="template", help="template for output formatting")

    def execute(self, *args, **kwargs):
        self.template = kwargs.pop('template', self.template)
        for i in self.contenaire.list(**kwargs):
            yield i

    def to_str(self, status):
        values = {}
        values.update(vars(status.superclass))
        values.update(vars(status))
        return (self.template + "\n") % (values)


class XmlExport(Verb):
    verb = "export"

    def execute(self, *args, **kwargs):
        if len(args) > 0:
            elem =  getattr(self.broker, args[0])
            if hasattr(elem, 'list'):
                def sublist():
                    for i in elem.list():
                        yield self._export(i)
                return sublist()
        else:
            return self._export(self.broker)


class Statistics(Verb):
    verb = "statistics"

    def execute(self, *args, **kwargs):
        for s in self.broker.statistics.list():
            yield s

    def to_str(self, stat):
        return "%s: %s %s (%s)\n" % (stat.name, stat.values.get_value()[0].get_datum(), stat.unit, stat.get_type())

class Create(Verb):
    verb = "create"

    def validate(self):
        return True


class Delete(Verb):
    verb = "delete"

    def execute(self, *args, **kwargs):
        return self.broker.delete()


class DeleteForce(Delete):

    def fill_parser(self, parser):
        parser.add_option("-f", "--force", dest="force", help="Force", default=False, action='store_true')


    def execute(self, *args, **kwargs):
        action_params = params.Action(
            # force a True/False content
            force=kwargs['force'] is True,
        )
        return self.broker.delete(action_params)
