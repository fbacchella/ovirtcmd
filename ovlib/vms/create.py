from ovirtsdk4 import types, Error

from ovlib import parse_size, is_id, OVLibError
from ovlib.eventslib import EventsCode, event_waiter
from ovlib.dispatcher import command
from ovlib.vms import VmDispatcher
from ovlib.verb import Create


default_settings = {
    'architecture': 'X86_64',
    'soundcard_enabled': False,
    'type': 'server',
    'template': 'Blank',
    'cpu': {'topology': {'cores': 1, 'threads': 1, 'sockets': 1}, 'architecture': 'X86_64'}
}


os_settings = {
    'rhel_7x64': {
        'time_zone': 'Etc/GMT',
        'soundcard_enabled': False,
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
        parser.add_option("--nopxe", dest="boot_pxe", help="Cant't boot pxe", default=True, action="store_false")
        parser.add_option("--cpu", dest="cpu", help="Number of cpu", default=None)
        parser.add_option("--ostype", dest="ostype", help="Server type", default=None)
        parser.add_option("--network", dest="networks", help="networks (network/vnicprofile?)", default=[], action='append')
        parser.add_option("--storage_domain", dest="storage_domain", help="Default storage domain", default=None)
        parser.add_option("--disk", dest="disks", help="disk (size,suffix?,storage_domain?)", default=[], action='append')
        parser.add_option("--role", dest="roles", help="roles to create (role:[u|g]:name_or_id)", default=[], action='append')

    def uses_template(self):
        return True

    def execute(self, name, **kwargs):
        self.api.generate_services()

        vm_settings = default_settings.copy()
        ostype = kwargs.pop('ostype', None)
        if ostype is not None and ostype in os_settings:
            vm_settings.update(os_settings[ostype])
            vm_settings.update(kwargs)
        vm_settings['name'] = name
        waiting_events = [EventsCode.USER_ADD_VM]
        if 'memory' in vm_settings:
            vm_settings['memory'] = parse_size(vm_settings['memory'])
        if 'memory_policy' not in vm_settings:
            vm_settings['memory_policy'] = types.MemoryPolicy(guaranteed=vm_settings['memory'], ballooning=False)
        if 'cluster' in vm_settings:
            vm_settings['cluster'] = self.api.clusters.get(name=vm_settings.pop('cluster'))
        if 'bios' in vm_settings:
            bios_params = {}
            if 'boot_menu' in vm_settings['bios']:
                bios_params['boot_menu'] = types.BootMenu(enabled = vm_settings['bios']['boot_menu'])
            vm_settings['bios'] = types.Bios(**bios_params)
        if 'io' in vm_settings:
            vm_settings['io'] = types.Io(**vm_settings['io'])
        boot_devices = [types.BootDevice['HD']]

        boot_pxe = vm_settings.pop('boot_pxe', False)
        if boot_pxe:
            boot_devices.append(types.BootDevice['NETWORK'])

        # Try to resolve the cpu topology
        cpu = vm_settings.pop('cpu')
        architecture = vm_settings.pop('architecture')
        if isinstance(cpu, (int, str)):
            cpu_topology = {}
            cpu_topology['cores'] = 1
            cpu_topology['threads'] = 1
            cpu_topology['sockets'] = int(cpu)
            cpu = {'architecture': architecture, 'topology': cpu_topology}
        elif isinstance(cpu, dict):
            if 'architecture' not in cpu:
                cpu['architecture'] = architecture
            if 'topology' in cpu:
                cpu['topology'] = {k: int(v) for k, v in cpu.pop('topology').items()}
            else:
                cpu['topology'] = {'cores': 1, 'threads': 1, 'sockets': 1}
        vm_settings['cpu'] = cpu

        os_info = vm_settings.pop('os', {})
        if len(boot_devices) > 0:
            os_info['boot'] = types.Boot(devices=boot_devices)
        os_info['type'] = ostype
        vm_settings['os'] = os_info

        osi = self.api.operatingsystems.get(name=ostype)
        if  not 'large_icon' in vm_settings:
            vm_settings['large_icon'] = osi.large_icon
        if not 'small_icon' in vm_settings:
            vm_settings['small_icon'] = osi.small_icon

        storage_domain_default = vm_settings.pop('storage_domain', None)
        disk_interface = vm_settings.pop('disk_interface', None)

        disks = []
        for disk_information in vm_settings.pop('disks', []):
            disk_args = {
                'provisioned_size': 0,
                'interface': disk_interface,
                'format': types.DiskFormat.RAW,
                'sparse': False,
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
            pass_discard = True
            if storage_domain is not None and not 'storage_domain' in disk_args:
                # retreive the storage domain and ensure that it supports discard
                sd = self.api.storagedomains.get(name=storage_domain)
                disk_args['storage_domains'] = [sd.type]
                pass_discard = sd.supports_discard
            disk_name_suffix = disk_args.pop('suffix', None)
            if disk_name_suffix is not None and not 'name' in disk_args:
                disk_args['name'] = "%s_%s" % (vm_settings['name'], disk_name_suffix)
            interface = disk_args.pop('interface', None)
            bootable = disk_args.pop('bootable', None)

            disks.append(self.api.wrap(types.DiskAttachment(disk=types.Disk(**disk_args), interface=interface, bootable=bootable, active=True, pass_discard=pass_discard)))
            #Add events to wait for each disks
            waiting_events += [EventsCode.USER_ADD_DISK_TO_VM_FINISHED_SUCCESS, EventsCode.USER_ADD_DISK_TO_VM]

        nics = []
        if_name = vm_settings.pop('network_name', None)
        if_interface = vm_settings.pop('network_interface', None)

        dc = self.api.wrap(self.api.datacenters.get(id=vm_settings['cluster'].data_center.id))

        for net_info in vm_settings.pop('networks', []):
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
        for role_info in vm_settings.pop('roles', []):
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
        with event_waiter(self.api, "vm.name=%s" % vm_settings['name'], events_returned,
                          wait_for=waiting_events,
                          break_on=[EventsCode.USER_ADD_VM_FINISHED_FAILURE,
                                    EventsCode.USER_FAILED_ADD_VM,
                                    EventsCode.USER_ADD_DISK_TO_VM_FINISHED_FAILURE,
                                    EventsCode.NETWORK_ACTIVATE_VM_INTERFACE_FAILURE],
                          verbose=True):
            # Create the VM
            newvm = self.api.wrap(self.api.vms.add(vm=vm_settings))
            futurs = []
            for x in nics:
                try:
                    futurs.append(newvm.nics.add(x, wait=False))
                except Error as e:
                    raise OVLibError('Unable to add nic to new VM')
            for x in roles:
                futurs.append(newvm.permissions.add(wait=False, permission=x))
            newvm.refresh()
            newvm.disk_attachments.refresh()
            for x in disks:
                try:
                    newvm.disk_attachments.add(x.type, wait=True)
                except Error as e:
                    raise OVLibError('Unable to add disk to new VM', exception=e)
            for f in futurs:
                try:
                    f.wait()
                except Error as e:
                    raise OVLibError('Futur failure with new VM: ' % e, exception=e)

        return newvm
