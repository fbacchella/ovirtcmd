import ovlib.verb

from ovlib import OVLibErrorNotFound
from ovlib.eventslib import EventsCode
from ovlib.dispatcher import dispatcher, command, Dispatcher
from ovlib.wrapper import ObjectWrapper, ListObjectWrapper, wrapper

from ovirtsdk4.types import Event
from ovirtsdk4.services import EventService, EventsService
from ovirtsdk4.writers import EventWriter


@wrapper(writer_class=EventWriter, type_class=Event, service_class=EventService, other_attributes=['description', 'severity'])
class EventWrapper(ObjectWrapper):
    def __init__(self, api, type=None, service=None):
        super(EventWrapper, self).__init__(api, service=service, type=type)
        if type is not None:
            try:
                self._code_enum = EventsCode(self.type.code)
            except ValueError:
                self._code_enum = EventsCode.UNDEFINED

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
        try:
            found_events = self.get(max=1)
            return int(found_events.id)
        except OVLibErrorNotFound:
            return 0


@dispatcher(object_name="event", wrapper=EventWrapper, list_wrapper=EventsWrapper)
class EventDispatcher(Dispatcher):

    def fill_parser(self, parser):
        super(EventDispatcher, self).fill_parser(parser)
        parser.add_option("-f", "--from", dest="from_", help="Start searching from", default=None, type=int)


@command(EventDispatcher)
class EventsList(ovlib.verb.List):
    template = "{id!s} {description!s}"

    def fill_parser(self, parser):
        super(EventsList, self).fill_parser(parser)
        parser.add_option("-f", "--from", dest="from_", help="Start searching from", default=None, type=int)


@command(EventDispatcher)
class EventExport(ovlib.verb.XmlExport):
    pass
