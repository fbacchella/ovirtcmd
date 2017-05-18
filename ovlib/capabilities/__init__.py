import ovlib.verb

from ovlib import Dispatcher, ObjectWrapper, ListObjectWrapper, command, dispatcher, wrapper

from ovirtsdk4.types import ClusterLevel, Permit, CpuType
from ovirtsdk4.writers import ClusterLevelWriter, PermitWriter, CpuTypeWriter
from ovirtsdk4.services import ClusterLevelsService, ClusterLevelService

@wrapper(service_root="clusterlevels", service_class=ClusterLevelsService)
class ClusterLevelsWrapper(ListObjectWrapper):
    pass


@wrapper(writer_class=ClusterLevelWriter, type_class=ClusterLevel, service_class=ClusterLevelService)
class ClusterLevelWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=PermitWriter, type_class=Permit)
class PermitWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=CpuTypeWriter, type_class=CpuType)
class CpuTypeWrapper(ObjectWrapper):
    pass


@dispatcher(object_name="capabilities", wrapper=ClusterLevelWrapper, list_wrapper=ClusterLevelsWrapper)
class ClusterLevelDispatcher(Dispatcher):

    def get(self, name=None, id=None):
        if id is None and name is not None:
            id=name
        return super(ClusterLevelDispatcher, self).get(id=id)


@command(ClusterLevelDispatcher)
class List(ovlib.verb.List):
    template = "{id!s}"

    def execute(self, *args, **kwargs):
        print self.object
        self.template = kwargs.pop('template', self.template)

        for i in self.object.list(**kwargs):
            yield i


@command(ClusterLevelDispatcher)
class XmlExport(ovlib.verb.XmlExport):
    pass

