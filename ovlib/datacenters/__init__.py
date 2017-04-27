import ovlib.verb
from ovlib import Dispatcher, command
from ovirtsdk.xml import params
from ovirtsdk.infrastructure.brokers import DataCenter

class_ref = []

@command(class_ref)
class List(ovlib.verb.List):
    pass


@command(class_ref)
class XmlExport(ovlib.verb.XmlExport):
    pass

@command(class_ref)
class Delete(ovlib.verb.DeleteForce):
    pass


@command(class_ref)
class Attach(ovlib.verb.Verb):
    verb = "attach"

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="Domain name", default=None)
        parser.add_option("-i", "--id", dest="id", help="Domain id", default=None)

    def execute(self, *args, **kwargs):
        sd = self.api.storagedomains.get(**kwargs)
        self.broker.storagedomains.add(params.StorageDomain(id=sd.id))


@command(class_ref)
class Create(ovlib.verb.Create):

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="New datecenter name", default=None)
        parser.add_option("-m", "--macpool", dest="macpool", help="Mac Pool", default=None)

    def execute(self, *args, **kwargs):
        macpool = kwargs.pop('macpool', None)
        if macpool is not None:
            kwargs['mac_pool'] = self.get('macpools', macpool)

        return self.contenaire.add(params.DataCenter(**kwargs))


@command(class_ref)
class Create(ovlib.verb.Verb):
    verb = "addqos"

    def execute(self, *args, **kwargs):
        kwargs['type_'] = kwargs.pop('type', None)
        return self.broker.qoss.add(params.QoS(**kwargs))


oc = Dispatcher(api_attribute="datacenters", object_name="datacenter", commands=class_ref, broker_class=DataCenter)
