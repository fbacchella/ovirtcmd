import ovlib.verb
from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.types import MacPool, Range
from ovirtsdk4.writers import MacPoolWriter, RangeWriter
from ovirtsdk4.services import MacPoolService, MacPoolsService


@wrapper(writer_class=RangeWriter, type_class=Range)
class RangeWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=MacPoolWriter, type_class=MacPool, service_class=MacPoolService)
class MacPoolWrapper(ObjectWrapper):
    pass

@wrapper(service_class=MacPoolsService, service_root="macpools")
class MacPoolsWrapper(ListObjectWrapper):
    pass


@dispatcher(object_name="macpool", wrapper=MacPoolWrapper, list_wrapper=MacPoolsWrapper)
class MacPoolDispatcher(Dispatcher):
    pass

@command(MacPoolDispatcher)
class MacPoolList(ovlib.verb.List):
    pass


@command(MacPoolDispatcher)
class MacPoolExport(ovlib.verb.XmlExport):
    pass


@command(MacPoolDispatcher)
class MacPoolRemove(ovlib.verb.Remove):
    pass


@command(MacPoolDispatcher)
class MacPoolCreate(ovlib.verb.Create):

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="Network name")
        parser.add_option("-a", "--allow_duplicates", dest="allow_duplicates", help="Allow Duplicates", default=False, action='store_true')
        parser.add_option("-f", "--from", dest="from", help="From")
        parser.add_option("-t", "--to", dest="to", help="To")
        parser.add_option("-r", "--range", dest="ranges", help="From-To", default=[], action='append')

    def do_range(self, from_to=None, from_mac=None, to_mac=None):
        if isinstance(from_to, str) or isinstance(from_to, unicode):
            (from_mac, to_mac) = from_to.split('-')[0:2]
        elif isinstance(from_to, list) or isinstance(from_to, tuple):
            (from_mac, to_mac) = from_to[0:2]
        return params.Range(from_mac, to_mac)

    def execute(self, *args, **kwargs):
        ranges = []
        for r in kwargs.pop('ranges', []):
            ranges.append(self.do_range(r))
        range = kwargs.pop('range', None)
        if range is not None:
            ranges.append(self.do_range(range))
        from_mac = kwargs.pop('from', None)
        to_mac = kwargs.pop('to', None)
        if from_mac is not None and to_mac is not None:
            from_to = ranges.append(self.do_range(from_mac=from_mac, to_mac=to_mac))
            ranges.append(from_to)
        kwargs['ranges'] = params.Ranges(ranges)
        new_mac_pool = params.MacPool(**kwargs)
        return self.contenaire.add(new_mac_pool)




