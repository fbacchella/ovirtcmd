import optparse
import sys
from ovlib.template import VariableOption, load_template

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
            print "needed object not found"
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
        if value == True:
            print "success"
        else:
            print value

    def status(self):
        """A default status command to run on success"""
        return 0;

class List(Verb):

    def validate(self,  *args, **kwargs):
        return True

    def execute(self, *args, **kwargs):
        for i in self.contenaire.list():
            yield "%s %s " %(i.get_name(), i.get_id())

class XmlExport(Verb):

    def execute(self, *args, **kwargs):
        output = StringIO()
        self.broker.export_(output, 0)
        return output.getvalue()
