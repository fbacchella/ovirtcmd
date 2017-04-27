class_ref_mac_pool = []
class_ref_mac_qos = []

import ovlib.verb
from ovlib import Dispatcher, command
from ovirtsdk.xml import params
from ovirtsdk.infrastructure.brokers import MacPool, DataCenterQoS, StorageDomainDiskProfile, VMCdRoms


@command(class_ref_mac_pool)
class List(ovlib.verb.List):
    pass


@command(class_ref_mac_pool)
class XmlExport(ovlib.verb.XmlExport):
    pass


@command(class_ref_mac_pool)
class Delete(ovlib.verb.Delete):
    pass


@command(class_ref_mac_pool)
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


macpool = Dispatcher(api_attribute ="macpools", object_name="macpool", commands=class_ref_mac_pool, broker_class=MacPool)

class_ref_mac_qos = []
@command(class_ref_mac_qos)
class List(ovlib.verb.List):
    pass


@command(class_ref_mac_qos)
class XmlExport(ovlib.verb.XmlExport):
    pass


@command(class_ref_mac_qos)
class Delete(ovlib.verb.Delete):
    pass


qos = Dispatcher(api_attribute="qoss", object_name=None, commands=class_ref_mac_qos, broker_class=DataCenterQoS)


class_ref_mac_diskprofile = []
@command(class_ref_mac_diskprofile)
class List(ovlib.verb.List):
    pass


@command(class_ref_mac_diskprofile)
class XmlExport(ovlib.verb.XmlExport):
    pass


@command(class_ref_mac_diskprofile)
class Delete(ovlib.verb.Delete):
    pass


diskprofile = Dispatcher(api_attribute="diskprofiles", object_name='diskprofile', commands=class_ref_mac_diskprofile, broker_class=StorageDomainDiskProfile)

class_ref_cdroms = []

@command(class_ref_cdroms)
class List(ovlib.verb.List):
    pass


@command(class_ref_cdroms)
class XmlExport(ovlib.verb.XmlExport):
    pass


cdroms = Dispatcher(api_attribute="cdroms", object_name=None, commands=class_ref_cdroms, broker_class=VMCdRoms)
