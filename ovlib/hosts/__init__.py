import ovlib.verb
from ovlib.storages import StorageDomainWrapper

from ovirtsdk4 import List
from ovirtsdk4.types import Host, HostStatus, \
    HostNic, Bonding, NetworkAttachment, IpAddressAssignment, MacPool, \
    VmSummary, VolumeGroup, LogicalUnit, PowerManagement, \
    HostStorage, StorageType, Ssh, \
    PmProxy, PmProxyType, FencingPolicy, Agent, HardwareInformation
from ovirtsdk4.services import HostService, HostsService, NetworkAttachmentService, NetworkAttachmentsService, HostNicsService, HostNicService, \
    HostStorageService, StorageService, AttachedStorageDomainService, AttachedStorageDomainsService, \
    FenceAgentService, FenceAgentsService
from ovirtsdk4.writers import HostWriter, HostNicWriter, BondingWriter, NetworkAttachmentWriter, IpAddressAssignmentWriter, VmSummaryWriter, VolumeGroupWriter, LogicalUnitWriter, \
    HostStorageWriter, \
    PowerManagementWriter, FencingPolicyWriter, AgentWriter

from ovlib.eventslib import EventsCode, event_waiter
from ovlib.dispatcher import dispatcher, command, Dispatcher
from ovlib.wrapper import ObjectWrapper, ListObjectWrapper, wrapper


@wrapper(type_class=HardwareInformation, writer_class=HardwareInformation, other_attributes=['product_name'])
class HardwareInformationWrapper(ObjectWrapper):
    pass


@wrapper(type_class=FencingPolicy, writer_class=FencingPolicyWriter)
class FencingPolicyWrapper(ObjectWrapper):
    pass


@wrapper(service_class=FenceAgentService, type_class=Agent, writer_class=AgentWriter)
class FenceAgentWrapper(ObjectWrapper):
    pass


@wrapper(service_class=FenceAgentsService, name_type_mapping={'agent': Agent})
class FenceAgentsWrapper(ListObjectWrapper):
    pass


@wrapper(type_class=PmProxy, name_type_mapping={'type': PmProxyType})
class PmProxyWrapper(ObjectWrapper):
    pass


@wrapper(type_class=PowerManagement,
         writer_class=PowerManagementWriter,
         name_type_mapping={'pm_proxies': PmProxy})
class PowerManagementWrapper(ObjectWrapper):
    pass


@wrapper(type_class=LogicalUnit, writer_class=LogicalUnitWriter, other_attributes=['logical_units'])
class LogicalUnitWrapper(ObjectWrapper):
    pass


@wrapper(type_class=VolumeGroup, writer_class=VolumeGroupWriter, other_attributes=['logical_units'],
         name_type_mapping={'logical_units': LogicalUnit})
class VolumeGroupWrapper(ObjectWrapper):
    pass


@wrapper(type_class=HostStorage, writer_class=HostStorageWriter, service_class=StorageService,
         other_attributes=['logical_units', 'type'],
         name_type_mapping={'type': StorageType, 'volume_group': VolumeGroup})
class HostStorageWrapper(ObjectWrapper):
    pass


@wrapper(service_class=HostStorageService, other_attributes=['volume_group'])
class HostStoragesWrapper(ListObjectWrapper):
    # it's not a real list, hide the default one
    def list(self, *args, **kwargs):
        return self.service.list(*args, **kwargs)


@wrapper(writer_class=VmSummaryWriter,
         type_class=VmSummary)
class VmSummaryWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=IpAddressAssignmentWriter,
         type_class=IpAddressAssignment)
class IpAddressWrapper(ObjectWrapper):
    pass


@wrapper(writer_class=Bonding,
         type_class=Bonding)
class BondingWrapper(ObjectWrapper):
    pass

@wrapper(writer_class=HostNicWriter,
         service_class=HostNicService,
         type_class=HostNic,
         other_attributes=['bonding']
         )
class HostNicWrapper(ObjectWrapper):
    pass


@wrapper(service_class=HostNicsService)
class HostNicsWrapper(ListObjectWrapper):
    pass


@wrapper(service_class=AttachedStorageDomainsService)
class AttachedStorageDomainsWrapper(ListObjectWrapper):
    pass


@wrapper(service_class=AttachedStorageDomainService,
         other_attributes=[])
class AttachedStorageDomainWrapper(StorageDomainWrapper):
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
         other_attributes=['update_available', 'network_attachments', 'cluster', 'hardware_information'],
         name_type_mapping={'mac_pool': MacPool, 'power_management': PowerManagement, 'ssh': Ssh, 'pm_proxies': PmProxy})
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


@wrapper(service_class=HostsService, service_root = "hosts",
         name_type_mapping={'host': Host, 'power_management': PowerManagement, 'ssh': Ssh})
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
            for i in [self.api.wrap(x) for x in value]:
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


@command(HostDispatcher, verb='upgrade')
class Upgrade(ovlib.verb.Verb):

    """A abstract class, used to implements actual verb"""
    def __init__(self, dispatcher):
        super(Upgrade, self).__init__(dispatcher)
        self._status = 0

    def fill_parser(self, parser):
        parser.add_option("-a", "--async", dest="async", help="Don't wait for completion state", default=False, action='store_true')
        parser.add_option("-r", "--refresh", dest="refresh_update", help="Refresh the upgrade status", default=False, action='store_true')
        parser.add_option("-b", "--reboot", dest="reboot", help="Reboot the host after upgrade", default=False, action='store_true')

    def execute(self, async=False, refresh_update=False, reboot=False):
        self.api.generate_services()

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
                self.object.upgrade(async=async, reboot=reboot)
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


@command(HostDispatcher)
class VmPermission(ovlib.verb.Permission):
    pass


from . import create
from . import bond
