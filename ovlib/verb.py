import optparse
import time
from ovlib.template import VariableOption

from ovlib import OVLibError

# Find the best implementation available on this platform
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

class Verb(object):
    """A abstract class, used to implements actual verb"""
    def __init__(self, api):
        self.api = api

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
        if value == True:
            print "success"
        else:
            print value

    def status(self):
        """A default status command to run on success"""
        return 0;

    def _export(self, object):
        output = StringIO()
        object.export_(output, 0)
        return output.getvalue()


class List(Verb):

    def validate(self,  *args, **kwargs):
        return True

    def execute(self, *args, **kwargs):
        for i in self.contenaire.list():
            yield i

    def to_str(self, status):
        return "%s %s\n" %(status.get_name(), status.get_id())


class XmlExport(Verb):

    def execute(self, *args, **kwargs):
        if len(args) > 0:
            elem =  getattr(self.broker, args[0])
            if hasattr(elem, 'list'):
                for i in elem.list():
                    yield  self._export(i)
        else:
            yield self._export(self.broker)
