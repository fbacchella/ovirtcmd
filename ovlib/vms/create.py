import time

from ovirtsdk4 import types

from ovlib.vms import VmDispatcher
from ovlib import command, parse_size, is_id, event_waiter, EventsCode
from ovlib.verb import Verb

os_settings = {
    'rhel_7x64': {
        'time_zone': 'Etc/GMT',
        'architecture': 'X86_64',
        'soundcard_enabled': False,
        'type': 'server',
        'network_interface': types.NicInterface.VIRTIO,
        'network_name': 'eth%d',
        'disk_interface': types.DiskInterface.VIRTIO_SCSI,
    }
}

@command(VmDispatcher, verb='create')
class VmCreate(Verb):

    def uses_template(self):
        return True

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="VM name", default=None)
        parser.add_option("-m", "--memory", dest="memory", help="VM name", default=None)
        parser.add_option("-c", "--cluster", dest="cluster", help="VM name", default=None)
        parser.add_option("-t", dest="template", help="VM name", default='Blank')
        parser.add_option("--pxe", dest="boot_pxe", help="Can boot pxe", default=True, action="store_false")
        parser.add_option("--cpu", dest="cpu", help="Number of cpu", default=None)
        parser.add_option("--ostype", dest="ostype", help="Server type", default=None)
        parser.add_option("--network", dest="networks", help="networks", default=[], action='append')
        parser.add_option("--disk", dest="disks", help="disk", default=[], action='append')

    def validate(self):
        return True

    def execute(self, **kwargs):
        waiting_events = [EventsCode.USER_ADD_VM]
        cluster = None
        if 'memory' in kwargs:
            kwargs['memory'] = parse_size(kwargs['memory'])
        if 'memory_policy' not in kwargs:
            kwargs['memory_policy'] = types.MemoryPolicy(guaranteed=kwargs['memory'], ballooning=False)
        if 'cluster' in kwargs:
            cluster = self.api.clusters.get(name=kwargs.pop('cluster'))
            kwargs['cluster'] = types.Cluster(id=cluster.id)
        if 'template' in kwargs:
            kwargs['template'] = types.Template(id=self.get(self.api.templates, kwargs.pop('template')).id)
        if 'time_zone' in kwargs:
            kwargs['time_zone'] = types.TimeZone(name=kwargs['time_zone'])
        if 'bios' in kwargs:
            bios_params = {}
            if 'boot_menu' in kwargs['bios']:
                bios_params['boot_menu'] = types.BootMenu(enabled = kwargs['bios']['boot_menu'])
            kwargs['bios'] = types.Bios(**bios_params)
        boot_devices = [types.BootDevice['HD']]

        boot_pxe = kwargs.pop('boot_pxe', False)
        if boot_pxe:
            boot_devices.append(types.BootDevice['NETWORK'])

        ostype = kwargs.pop('ostype')
        if ostype in os_settings:
            settings = os_settings[ostype]
            if not 'time_zone' in kwargs:
                kwargs['time_zone'] = settings['time_zone']

            if not 'soundcard_enabled' in kwargs:
                kwargs['soundcard_enabled'] = settings['soundcard_enabled']
            if not 'type' in kwargs:
                kwargs['type'] = settings['type']
        if 'type' in kwargs:
            kwargs['type'] = types.VmType(kwargs.pop('type'))

        cpu = kwargs.pop('cpu', None)
        if cpu is not None:
            architecture = types.Architecture[cpu.pop('architecture', settings['architecture'])]
        else:
            architecture = types.Architecture[settings['architecture']]

        if cpu is None:
            cpu_topology = {'cores': 1, 'threads': 1, 'sockets': 1}
        # if plain cpu argument was given, it's a number of socket, single core, single thread
        elif isinstance(cpu, (int, basestring)):
            cpu_topology = {}
            cpu_topology['cores'] = 1
            cpu_topology['threads'] = 1
            cpu_topology['sockets'] = int(cpu)
        elif isinstance(cpu, dict):
            if 'architecture' in cpu:
                architecture = types.Architecture[cpu.pop('architecture')]
            if 'topology' in cpu:
                cpu_topology ={k: int(v) for k, v in cpu.pop('topology').items()}
            else:
                cpu_topology = cpu

        kwargs['cpu'] = types.Cpu(architecture=architecture, topology=types.CpuTopology(**cpu_topology))

        os_info = kwargs.pop('os', {})
        if len(boot_devices) > 0:
            os_info['boot'] = types.Boot(devices=boot_devices)
        os_info['type'] = ostype
        kwargs['os'] = types.OperatingSystem(**os_info)

        osi = self.api.operatingsystems.get(name=ostype)
        if  not 'large_icon' in kwargs:
            kwargs['large_icon'] = osi.large_icon
        if not 'small_icon' in kwargs:
            kwargs['small_icon'] = osi.small_icon

        storage_domain_common = kwargs.pop('storage_domain', None)
        disk_interface = kwargs.pop('disk_interface', settings.get('disk_interface', None))

        disks = []
        disks_event = []
        for disk_information in kwargs.pop('disks', []):
            disk_args = {
                'provisioned_size': 0,
                'interface': disk_interface,
                'format': types.DiskFormat.RAW,
                'sparse': False,
                'storage_domain': storage_domain_common,
                'suffix': 'sys' if len(disks) == 0 else len(disks),
                # first disk is the boot and system disk
                'bootable': True if len(disks) == 0 else False,
            }

            #If a id to an existing disk was given
            if is_id(disk_information):
                disk_args = {'id': disk_information}
            elif isinstance(disk_information, (basestring, list, tuple)):
                if isinstance(disk_information, basestring):
                    disk_information_array = disk_information.split(",")
                else:
                    disk_information_array = disk_information

                if len(disk_information_array) > 0:
                    disk_args['provisioned_size'] = disk_information_array[0]
                if len(disk_information_array) > 1 and len(disk_information_array[1]) > 0:
                    disk_args['suffix'] = disk_information_array[1]
                if len(disk_information_array) > 2  and len(disk_information_array[2]) > 0:
                    disk_args['storage_domain'] = disk_information_array[2]
            elif isinstance(disk_information, dict):
                disk_args.update(disk_information)

            disk_size = disk_args.pop('provisioned_size', None)
            if disk_size is not None:
                disk_args['provisioned_size'] = parse_size(disk_size)

            if 'format' in disk_args and isinstance(disk_args['format'], (str, unicode)):
                disk_args['format'] = types.DiskFormat[disk_args['format']]
            if 'interface' in disk_args and isinstance(disk_args['interface'], (str, unicode)):
                disk_args['interface'] = types.DiskInterface[disk_args['interface']]

            storage_domain = disk_args.pop('storage_domain', None)
            if storage_domain is not None and not 'storage_domain' in disk_args:
                #storage_domain = self.get(self.api.storagedomains, storage_domain)
                disk_args['storage_domains'] = [types.StorageDomain(name=storage_domain)]

            disk_name_suffix = disk_args.pop('suffix', None)
            if disk_name_suffix is not None and not 'name' in disk_args:
                disk_args['name'] = "%s_%s" % (kwargs['name'], disk_name_suffix)
            interface = disk_args.pop('interface', None)
            bootable = disk_args.pop('bootable', None)

            disks.append(types.DiskAttachment(disk=types.Disk(**disk_args), interface=interface, bootable=bootable, active=True))

            #Add events to wait for each disks
            waiting_events += [EventsCode.USER_ADD_DISK_TO_VM_FINISHED_SUCCESS, EventsCode.USER_ADD_DISK_TO_VM]

        nics = []
        if_name = kwargs.pop('network_name', settings['network_name'])
        if_interface = kwargs.pop('network_interface', settings['network_interface'])

        dc = self.api.wrap(self.api.datacenters.get(id=cluster.data_center.id))

        for net_info in kwargs.pop('networks', []):
            net_args = {
                'name': if_name % len(nics),
                'interface': if_interface,
            }
            if isinstance(net_info, basestring):
                net_args['network'] = net_info
            elif isinstance(net_info, dict):
                net_args.update(net_info)

            net_name = net_args.pop('network', None)
            if net_name is not None:
                net_args['network'] = dc.networks.get(name=net_name).type

            if 'interface' in net_args and isinstance(net_args['interface'], (str, unicode)):
                net_args['interface'] = types.NicInterface[net_args['interface']]

            nics.append(types.Nic(**net_args))
            waiting_events += [EventsCode.NETWORK_ACTIVATE_VM_INTERFACE_SUCCESS]

        events_returned = []
        with event_waiter(self.api, "vm.name=%s" % kwargs['name'], events_returned,
                          wait_for=waiting_events,
                          break_on=[EventsCode.USER_ADD_VM_FINISHED_FAILURE,
                                    EventsCode.USER_FAILED_ADD_VM,
                                    EventsCode.USER_ADD_DISK_TO_VM_FINISHED_FAILURE,
                                    EventsCode.NETWORK_ACTIVATE_VM_INTERFACE_FAILURE],
                          verbose=True):
            newvm = self.api.wrap(self.api.vms.add(types.Vm(**kwargs)))
            map(lambda x: newvm.nics.add(x), nics)
            map(lambda x: newvm.disk_attachments.add(x), disks)
        return newvm
