import ovlib.verb

from ovlib import Dispatcher, ListObjectWrapper, ObjectWrapper, command, dispatcher, wrapper, parse_size

from ovirtsdk4.types import Event
from ovirtsdk4.services import EventService, EventsService
from ovirtsdk4.writers import EventWriter


@wrapper(writer_class=EventWriter, type_class=Event, service_class=EventService, other_attributes=['description', 'code', 'severity'])
class EventWrapper(ObjectWrapper):
    pass


@wrapper(service_class=EventsService, service_root="events")
class EventsWrapper(ListObjectWrapper):
    pass


@dispatcher(object_name="event", wrapper=EventWrapper, list_wrapper=EventsWrapper)
class EventDispatcher(Dispatcher):
    pass


@command(EventDispatcher)
class EventsList(ovlib.verb.List):
    template = "{id!s} {description!s}"

    def fill_parser(self, parser):
        parser.add_option("-f", "--from", dest="from_", help="Start searching from", default=None, type=int)

    def execute(self, from_=None):
        for e in self.object.list(from_=from_):
            yield e


@command(EventDispatcher)
class EventExport(ovlib.verb.XmlExport):
    pass


