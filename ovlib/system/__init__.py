import ovlib.verb
from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.services import SystemService
from ovirtsdk4.writers import ApiWriter, ProductInfoWriter, ApiSummaryWriter, ApiSummaryItemWriter
from ovirtsdk4.types import Api, ProductInfo, ApiSummary, ApiSummaryItem


@wrapper(type_class=ApiSummaryItem, writer_class=ApiSummaryItemWriter)
class ApiSummaryItemWrapper(ObjectWrapper):
    pass


@wrapper(type_class=ApiSummary, writer_class=ApiSummaryWriter)
class ApiSummaryWrapper(ObjectWrapper):
    pass


@wrapper(type_class=ProductInfo, writer_class=ProductInfoWriter)
class ProductInfoWrapper(ObjectWrapper):
    pass


@wrapper(type_class=Api, writer_class=ApiWriter)
class ApiWrapper(ObjectWrapper):
    pass


@wrapper(service_class=SystemService, other_methods=['reload_configurations'])
class SystemWrapper(ObjectWrapper):

    def __init__(self, api, type=None, service=None):
        super(SystemWrapper, self).__init__(api, service=api.service(""))

    def export(self, path=[]):
        return self.api.wrap(self.service.get()).export(path)

    def get(self, search=None, **kwargs):
        return self


@dispatcher(object_name="system", wrapper=SystemWrapper, list_wrapper=SystemWrapper)
class SystemDispatcher(Dispatcher):
    pass

@command(SystemDispatcher)
class SystemExport(ovlib.verb.XmlExport):
    pass


@command(SystemDispatcher, verb='reload')
class ReloadSystem(ovlib.verb.Create):

    def fill_parser(self, parser):
        parser.add_option("-a", "--async", dest="async", help="Don't wait for completion state", default=False, action='store_true')

    def execute(self, async=False):
        return self.object.reload_configurations(async=async)
