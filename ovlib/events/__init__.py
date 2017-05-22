import ovlib.verb

from ovlib import Dispatcher, ListObjectWrapper, ObjectWrapper, command, dispatcher, wrapper, EventsCode

from ovirtsdk4.types import Event
from ovirtsdk4.services import EventService, EventsService
from ovirtsdk4.writers import EventWriter


@wrapper(writer_class=EventWriter, type_class=Event, service_class=EventService, other_attributes=['description', 'severity'])
class EventWrapper(ObjectWrapper):
    def __init__(self, api, type=None, service=None):
        super(EventWrapper, self).__init__(api, service=service, type=type)
        if type is not None:
            self._code_enum = EventsCode(self.type.code)

    @property
    def code(self):
        if self.dirty:
            self.type = self.api.follow_link(self.type)
            self.dirty = False
            self._code_enum = EventsCode(self.type.code)
        return self.type.code

    @property
    def code_enum(self):
        if self.dirty:
            self.type = self.api.follow_link(self.type)
            self.dirty = False
            self._code_enum = EventsCode(self.type.code)
        return self._code_enum


@wrapper(service_class=EventsService, service_root="events")
class EventsWrapper(ListObjectWrapper):

    def get_last(self):
        found_events = self.list(max=1)
        if len(found_events) > 0:
            return int(found_events[0].id)
        else:
            return 0


@dispatcher(object_name="event", wrapper=EventWrapper, list_wrapper=EventsWrapper)
class EventDispatcher(Dispatcher):
    pass


@command(EventDispatcher)
class EventsList(ovlib.verb.List):
    template = "{id!s} {description!s}"

    def fill_parser(self, parser):
        super(EventsList, self).fill_parser(parser)
        parser.add_option("-f", "--from", dest="from_", help="Start searching from", default=None, type=int)

#    def execute(self, from_=None, template=self.template, ):
#        if template is not None:
#            self.template = template#
#
#        for i in self.object.list(search=search):
#            yield i#
#
#        self.template = kwargs.pop('template', self.template)
#        for e in self.object.list(from_=from_):
#            yield e


@command(EventDispatcher)
class EventExport(ovlib.verb.XmlExport):
    pass


