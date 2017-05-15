import time
import ovlib.verb

from ovirtsdk4 import List
from ovirtsdk4.types import Host, HostStatus, HostNic, NetworkAttachment, IpAddressAssignment, VmSummary, Ssh
from ovirtsdk4.services import HostService, HostsService, NetworkAttachmentService, NetworkAttachmentsService, HostNicsService, HostNicService
from ovirtsdk4.writers import HostWriter, HostNicWriter, NetworkAttachmentWriter, IpAddressAssignmentWriter, VmSummaryWriter, SshWriter

from ovlib import wrapper, ObjectWrapper, ListObjectWrapper, Dispatcher, dispatcher, command, event_waiter, EventsCode


@wrapper(writer_class=SshWriter,
         type_class=Ssh)
class SshWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=VmSummaryWriter,
         type_class=VmSummary)
class VmSummaryWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=IpAddressAssignmentWriter,
         type_class=IpAddressAssignment)
class IpAddressWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=HostNicWriter,
         service_class=HostNicService,
         type_class=HostNic)
class HostNicWrapper(ObjectWrapper):
    pass


@wrapper(service_class=HostNicsService)
class HostNicsWrapper(ListObjectWrapper):
    pass


@wrapper(service_class=NetworkAttachmentsService)
class NetworkAttachmentsWrapper(ListObjectWrapper):
    pass


@wrapper(writer_class=NetworkAttachmentWriter,
         type_class=NetworkAttachment,
         service_class=NetworkAttachmentService,
         other_attributes=['ip_address_assignments', 'in_sync', 'host_nic', 'network', 'dns_resolver_configuration'])
class NetworkAttachmentWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=HostWriter,
         type_class=Host,
         service_class=HostService,
         other_methods=['deactivate', 'activate', 'fence', 'upgrade', 'upgrade_check', 'unregistered_storage_domains_discover',
                        'setup_networks', 'commit_net_config'],
         other_attributes=['update_available', 'network_attachments'])
class HostWrapper(ObjectWrapper):

    def upgrade_check(self, async=True):
        if not async:
            events_returned = []
            with event_waiter(self.api, "host.name=%s" % self.name, events_returned,
                              break_on=[EventsCode.HOST_AVAILABLE_UPDATES_FINISHED,
                                        EventsCode.HOST_AVAILABLE_UPDATES_PROCESS_IS_ALREADY_RUNNING,
                                        EventsCode.HOST_AVAILABLE_UPDATES_SKIPPED_UNSUPPORTED_STATUS,
                                        EventsCode.HOST_AVAILABLE_UPDATES_FAILED]):
                self.dirty = True
                self.service.upgrade_check()
            return events_returned
        else:
            self.dirty = True
            return self.service.upgrade_check()


@wrapper(service_class=HostsService, service_root = "hosts")
class HostsWrapper(ListObjectWrapper):
    pass

@dispatcher(object_name = "host", wrapper=HostWrapper, list_wrapper=HostsWrapper)
class HostDispatcher(Dispatcher):
    pass

@command(HostDispatcher)
class HostStatistics(ovlib.verb.Statistics):
    pass


@command(HostDispatcher)
class HostList(ovlib.verb.List):
    pass


@command(HostDispatcher)
class HostExport(ovlib.verb.XmlExport):
    pass


@command(HostDispatcher)
class HostRemove(ovlib.verb.Remove):

    def execute(self, *args, **kwargs):
        if self.broker.status.state != "maintenance":
            self.broker.deactivate()
            self.wait_for("maintenance")
        self.broker.delete()


@command(HostDispatcher, verb='maintenance')
class Maintenance(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-r", "--reason", dest="reason", help="Reason for maintenance", default=None)
        parser.add_option("-a", "--async", dest="async", help="Don't wait for maintenance state", default=False, action='store_true')

    def execute(self, reason=None, async=False, *args, **kwargs):
        if self.object.status != HostStatus.MAINTENANCE:
            self.object.deactivate(reason=reason, async=async)
            if not async:
                self.object.wait_for(HostStatus.MAINTENANCE)
        return True


@command(HostDispatcher, verb='upgradecheck')
class UpgradeCheck(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-a", "--async", dest="async", help="Don't wait for maintenance state", default=False, action='store_true')

    def execute(self, async=False, *args, **kwargs):
        return self.object.upgrade_check(async)

    def to_str(self, value):
        if isinstance(value, List):
            for i in map(lambda x: self.api.wrap(x), value):
                return i.description
        else:
            return str(self.api.wrap(value))


@command(HostDispatcher, verb='activate')
class Activate(ovlib.verb.Verb):

    def fill_parser(self, parser):
        parser.add_option("-a", "--async", dest="async", help="Don't wait for maintenance state", default=False, action='store_true')

    def execute(self, *args, **kwargs):
        if self.object.status == HostStatus.MAINTENANCE:
            self.object.activate()
            self.object.wait_for(HostStatus.UP)
        return True


@command(HostDispatcher, verb='discoverdomain')
class DiscoverDomain(ovlib.verb.Verb):

    def execute(self, *args, **kwargs):
        return self.object.unregistered_storage_domains_discover()

    def to_str(self, value):
        for i in value:
            return i.export()


def get_uptime(host):
    uptime_stat = host.statistics.get(name="boot.time")
    return uptime_stat.values.get_value()[0].get_datum()


@command(HostDispatcher, verb='reinstall')
class ReInstall(ovlib.verb.Verb):
    """Broken, do not use"""

    def fill_parser(self, parser):
        parser.add_option("-i", "--dont_override_iptables", dest="override_iptables", help="Automatically configure host firewall", default=True, action="store_false")

    def execute(self, *args, **kwargs):
        if self.broker.status.state != "maintenance":
            self.broker.deactivate()
            self.wait_for("maintenance")
        ssh_old_params = vars(self.broker.ssh)
        ssh_new_params = {}
        ssh_new_params['authentication_method'] = 'publickey'
        for p in ('authentication_method', 'port', 'fingerprint', 'user'):
            if p in ssh_old_params and ssh_old_params[p] is not None:
                ssh_new_params[p] = ssh_old_params[p]

        print ssh_new_params
        action = params.Action(ssh=params.SSH(**ssh_new_params),
                               host=params.Host(override_iptables=kwargs.pop('override_iptables', True)))
        self.broker.install(action)


@command(HostDispatcher, verb='reboot')
class Reboot(ovlib.verb.Verb):
    """Broken, do not use"""
    verb = ""

    def execute(self, *args, **kwargs):
        last_boot = get_uptime(self.broker)

        if self.object.status != HostStatus.MAINTENANCE:
            self.object.deactivate(reason='For reboot', async=False)
            self.object.wait_for(HostStatus.MAINTENANCE)
        self.object.fence(params.Action(fence_type='restart'))
        # needs to be activated before checking for up, otherwise it will return maintenance forever
        doactivate=True
        while doactivate:
            try:
                self.broker = self.contenaire.get(id=self.broker.id)
                current_last_boot = get_uptime(self.broker)
                print "%s %s" % (last_boot, current_last_boot)
                #self.broker.activate()
            except RequestError as e:
                print e.detail
                time.sleep(5)
        self.wait_for("up")
        return True


@command(HostDispatcher, verb='upgrade')
class Upgrade(ovlib.verb.Verb):

    """A abstract class, used to implements actual verb"""
    def __init__(self, dispatcher):
        super(Upgrade, self).__init__(dispatcher)
        self._status = 0

    def fill_parser(self, parser):
        parser.add_option("-a", "--async", dest="async", help="Don't wait for completion state", default=False, action='store_true')
        parser.add_option("-r", "--refresh", dest="refresh_update", help="Refresh the upgrade status", default=False, action='store_true')

    def execute(self, async=False, refresh_update=False):
        if refresh_update:
            events = self.object.upgrade_check(async=False)
            if isinstance(events, (List, list)):
                if events[0].code_enum != EventsCode.HOST_AVAILABLE_UPDATES_FINISHED:
                    self._status = 5
                    raise ovlib.OVLibError(events[0].description, value={'event': events[0]})

        if self.object.update_available:
            if self.object.status != HostStatus.MAINTENANCE:
                self.object.deactivate(reason='For upgrade', async=True)
                self.object.wait_for(HostStatus.MAINTENANCE)
            events_returned = []
            break_on = [EventsCode.HOST_UPGRADE_FAILED]
            if async:
                break_on.append(EventsCode.HOST_UPGRADE_STARTED)
            else:
                break_on.append(EventsCode.HOST_UPGRADE_FINISHED)

            with event_waiter(self.api, "host.name=%s" % self.object.name, events_returned,
                              break_on=break_on):
                self._status = 2
                self.object.upgrade(async=async)
            if len(events_returned) == 0:
                raise ovlib.OVLibError("upgrade interrupted")
            if events_returned[0].code_enum == EventsCode.HOST_UPGRADE_FINISHED:
                self._status = 1
            elif not async:
                self._status = 4
                raise ovlib.OVLibError(events_returned[0].description, value={'event': events_returned[0]})
        else:
            self._status = 3
        return self._status

    def to_str(self, value):
        if value == 0:
            return "Nothing to do, up to date"
        elif value == 1:
            return "Upgraded succeeded"
        elif value == 2:
            return "Upgrade in progress"
        elif value == 3:
            return "Upgrade not needed"
        else:
            return str(value)

    def status(self):
        if self._status >= 4:
            return self._status - 3
        else:
            return 0


import create
import bond
