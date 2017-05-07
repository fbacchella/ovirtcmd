import ovlib.verb
from ovlib import Dispatcher, ObjectWrapper, command, dispatcher, wrapper, ListObjectWrapper

from ovirtsdk4.types import Template, TemplateVersion
from ovirtsdk4.writers import TemplateVersionWriter, TemplateWriter
from ovirtsdk4.services import TemplateService, TemplatesService

@wrapper(writer_class=TemplateWriter, type_class=Template, service_class=TemplateService)
class TemplateWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=TemplateVersionWriter, type_class=TemplateVersion)
class TemplateVersionWrapper(ObjectWrapper):
    pass


@wrapper(service_class=TemplatesService, service_root="templates")
class TemplatesWrapper(ListObjectWrapper):
    pass


@dispatcher(object_name="template", wrapper=TemplateWrapper, list_wrapper=TemplatesWrapper)
class TemplateDispatcher(Dispatcher):
    pass


@command(TemplateDispatcher)
class TemplaterList(ovlib.verb.List):
    pass


@command(TemplateDispatcher)
class TemplateExport(ovlib.verb.XmlExport):
    pass


@command(TemplateDispatcher)
class TemplateRemove(ovlib.verb.Remove):
    pass
