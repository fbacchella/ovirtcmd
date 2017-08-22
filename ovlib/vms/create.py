from ovirtsdk4 import types, Error

from ovlib import parse_size, is_id, OVLibError
from ovlib.eventslib import EventsCode, event_waiter
from ovlib.dispatcher import command
from ovlib.vms import VmDispatcher
from ovlib.verb import Create

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
class VmCreate(Create):

    def fill_parser(self, parser):
        parser.add_option("-n", "--name", dest="name", help="VM name", default=None)
        parser.add_option("-m", "--memory", dest="memory", help="VM name", default=None)
        parser.add_option("-c", "--cluster", dest="cluster", help="VM name", default=None)
        parser.add_option("-t", dest="template", help="VM name", default='Blank')
        parser.add_option("--pxe", dest="boot_pxe", help="Can boot pxe", default=True, action="store_false")
        parser.add_option("--cpu", dest="cpu", help="Number of cpu", default=None)
        parser.add_option("--ostype", dest="ostype", help="Server type", default=None)
        parser.add_option("--network", dest="networks", help="networks (network/vnicprofile?)", default=[], action='append')
        parser.add_option("--disk", dest="disks", help="disk (size,suffix?,storage_domain?)", default=[], action='append')
        parser.add_option("--role", dest="roles", help="roles to create (role:[u|g]:name_or_id)", default=[], action='append')

    def uses_template(self):
        return True

    def execute(self, **kwargs):
        self.api.generate_services()
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
            kwargs['template'] = types.Template(id=self.api.templates.get(name=kwargs.pop('template')).id)
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
        elif isinstance(cpu, (int, str)):
            cpu_topology = {}
            cpu_topology['cores'] = 1
            cpu_topology['threads'] = 1
            cpu_topology['sockets'] = int(cpu)
        elif isinstance(cpu, dict):
            if 'architecture' in cpu:
                architecture = types.Architecture[cpu.pop('architecture')]
            if 'topology' in cpu:
                cpu_topology ={k: int(v) for k, v in list(cpu.pop('topology').items())}
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

        storage_domain_default = kwargs.pop('storage_domain', None)
        disk_interface = kwargs.pop('disk_interface', settings.get('disk_interface', None))

        disks = []
        disks_event = []
        for disk_information in kwargs.pop('disks', []):
            disk_args = {
                'provisioned_size': 0,
                'interface': disk_interface,
                'format': types.DiskFormat.COW,
                'sparse': True,
                'storage_domain': storage_domain_default,
                # first disk is the boot and system disk
                'suffix': 'sys' if len(disks) == 0 else len(disks),
                'bootable': True if len(disks) == 0 else False,
            }

            if is_id(disk_information):
                # If a id to an existing disk was given
                disk_args = {'id': disk_information}
            elif isinstance(disk_information, (str, list, tuple)):
                if isinstance(disk_information, str):
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

            if 'format' in disk_args and isinstance(disk_args['format'], str):
                disk_args['format'] = types.DiskFormat[disk_args['format']]
            if 'interface' in disk_args and isinstance(disk_args['interface'], str):
                disk_args['interface'] = types.DiskInterface[disk_args['interface']]

            storage_domain = disk_args.pop('storage_domain', None)
            if storage_domain is not None and not 'storage_domain' in disk_args:
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
            if isinstance(net_info, str):
                net_args['network'] = net_info
            elif isinstance(net_info, dict):
                net_args.update(net_info)

            net_name = net_args.pop('network', None)
            if net_name is not None:
                net_infos = net_name.split('/')
                if len(net_infos) == 2:
                    vnic_name = net_infos[1]
                    net_name = net_infos[0]
                else:
                    vnic_name = net_name
                    net_name = net_name
                print(net_name,vnic_name)
                network = dc.networks.get(name=net_name)
                network = self.api.networks.get(network.id)
                vnic = network.vnic_profiles.get(name=vnic_name)
                net_args['vnic_profile'] = vnic.type
            if 'interface' in net_args and isinstance(net_args['interface'], str):
                net_args['interface'] = types.NicInterface[net_args['interface']]
            nics.append(types.Nic(**net_args))
            waiting_events += [EventsCode.NETWORK_ACTIVATE_VM_INTERFACE_SUCCESS]

        # Role is either given as the string role:[u|g]:name_or_id
        # Or a dict: {'role': name_or_id, 'group': name_or_id, 'user: name_or_id} with 'group' and 'user' mutually exclusive
        roles = []
        for role_info in kwargs.pop('roles', []):
            user = None
            group = None
            if isinstance(role_info, str):
                (role, type, information) = role_info.split(":")
                if len(information) == 0:
                    continue
                if type[0].lower() == 'u':
                    user = information
                elif type[0].lower() == 'g':
                    group = information
                else:
                    raise OVLibError("Invalid role defintion line given: %s" % role_info)
            elif isinstance(role_info, dict) and len(role_info) == 2:
                role = role_info['role']
                user = role_info.get('user', None)
                group = role_info.get('group', None)
            else:
                raise OVLibError("Invalid role defintion given: %s" % role_info)

            if role is not None:
                role = self.api.roles.get(role)
            if user is not None:
                user = self.api.users.get(user)
            if group is not None:
                group = self.api.groups.get(group)

            role_kwargs = {'role': role, 'user': user, 'group': group}
            roles.append(role_kwargs)

        events_returned = []
        with event_waiter(self.api, "vm.name=%s" % kwargs['name'], events_returned,
                          wait_for=waiting_events,
                          break_on=[EventsCode.USER_ADD_VM_FINISHED_FAILURE,
                                    EventsCode.USER_FAILED_ADD_VM,
                                    EventsCode.USER_ADD_DISK_TO_VM_FINISHED_FAILURE,
                                    EventsCode.NETWORK_ACTIVATE_VM_INTERFACE_FAILURE],
                          verbose=True):
            # Create the VM
            newvm = self.api.wrap(self.api.vms.add(vm=kwargs))
            futurs = []
            for x in nics:
                try:
                    futurs.append(newvm.nics.add(x, wait=False))
                except Error as e:
                    raise OVLibError('Unable to add nic to new VM')
            for x in disks:
                try:
                    futurs.append(newvm.disk_attachments.add(x, wait=False))
                except Error as e:
                    print(e)
                    raise OVLibError('Unable to add disk to new VM', exception=e)
            for x in roles:
                futurs.append(newvm.permissions.add(wait=False, permission=x))
            for f in futurs:
                try:
                    f.wait()
                except Error as e:
                    print(e)
                    raise OVLibError('Futur failure with new VM: ' % e, exception=e)

        return newvm
