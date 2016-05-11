class_ref_mac_pool = []
import ovlib.verb
from ovlib import Object_Context, add_command
from ovirtsdk.xml import params
from ovirtsdk.infrastructure.brokers import MacPool


@add_command(class_ref_mac_pool)
class List(ovlib.verb.List):
    pass


@add_command(class_ref_mac_pool)
class XmlExport(ovlib.verb.XmlExport):
    pass


@add_command(class_ref_mac_pool)
class Delete(ovlib.verb.Delete):
    pass


@add_command(class_ref_mac_pool)
class Create(ovlib.verb.Create):

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


macpool = Object_Context(api_attribute ="macpools", object_name ="macpool", commands = class_ref_mac_pool, broker_class=MacPool)
