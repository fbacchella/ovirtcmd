import time

import ovlib.verb
from ovlib import parse_size
from ovirtsdk.xml import params

os_settings = {
    'rhel_7x64': {
        'timezone': 'Etc/GMT',
        'architecture': 'X86_64',
        'soundcard_enabled': False,
        'type': 'server',
        'network_interface': 'virtio',
        'network_name': 'eth%d',
        'disk_interface': 'virtio',
    }
}

class Create(ovlib.verb.Verb):
    verb = "create"

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
        cluster = None
        if 'memory' in kwargs:
            kwargs['memory'] = parse_size(kwargs['memory'])
        if 'memory_policy' not in kwargs:
            kwargs['memory_policy'] = params.MemoryPolicy(guaranteed=kwargs['memory'], ballooning=False)
        if 'cluster' in kwargs:
            cluster = self.get(self.api.clusters, kwargs.pop('cluster'))
            kwargs['cluster'] = params.Cluster(id=cluster.id)
        if 'template' in kwargs:
            kwargs['template'] = params.Template(id=self.get(self.api.templates, kwargs.pop('template')).id)
        if 'bios' in kwargs:
            bios_params = {}
            if 'boot_menu' in kwargs['bios']:
                bios_params['boot_menu'] = params.BootMenu(enabled = kwargs['bios']['boot_menu'])
            kwargs['bios'] = params.Bios(**bios_params)
        boot_devices = [params.Boot(dev='hd')]

        boot_pxe = kwargs.pop('boot_pxe', False)
        if boot_pxe:
            boot_devices.append(params.Boot(dev='network'))

        ostype = kwargs.pop('ostype')
        if ostype in os_settings:
            settings = os_settings[ostype]
            if not 'timezone' in kwargs:
                kwargs['timezone'] = settings['timezone']

            if not 'soundcard_enabled' in kwargs:
                kwargs['soundcard_enabled'] = settings['soundcard_enabled']
            if not 'type' in kwargs:
                kwargs['type_'] = settings['type']
        if 'type' in kwargs:
            kwargs['type_'] = kwargs.pop('type')

        cpu = kwargs.pop('cpu', None)
        architecture = kwargs.pop('architecture', None)

        if architecture is None:
            architecture = settings['architecture']

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
                architecture = cpu.pop('architecture')
            if 'topology' in cpu:
                cpu_topology = cpu.pop('topology')
            else:
                cpu_topology = cpu

        kwargs['cpu'] = params.CPU(architecture=architecture, topology=params.CpuTopology(**cpu_topology))

        os_info = kwargs.pop('os', {})
        if len(boot_devices) > 0:
            os_info['boot'] = boot_devices
        os_info['type_'] = ostype
        kwargs['os'] = params.OperatingSystem(**os_info)


        osi = self.api.operatingsysteminfos.get(name=ostype)
        if  not 'large_icon' in kwargs:
            kwargs['large_icon'] = osi.get_large_icon()
        if not 'small_icon' in kwargs:
            kwargs['small_icon'] = osi.get_small_icon()

        disks = []
        storage_domain_common = kwargs.pop('storage_domains', None)
        disk_interface = kwargs.pop('disk_interface', settings.get('disk_interface', None))
        for disk_information in kwargs.pop('disks', []):
            disk_args = {
                'size': 0,
                'interface': disk_interface,
                'format': 'raw',
                'sparse': False,
                'storage_domain': storage_domain_common,
                'suffix': 'sys' if len(disks) == 0 else len(disks),
                # first disk is the boot and system disk
                'bootable': True if len(disks) == 0 else False,
            }
            if ovlib.is_id(disk_information):
                disk_args = { 'id': disk_information, 'active': True}

            if isinstance(disk_information, (basestring, list, tuple)):
                if isinstance(disk_information, basestring):
                    disk_information_array = disk_information.split(",")
                else:
                    disk_information_array = disk_information

                if len(disk_information_array) > 0:
                    disk_args['size'] = disk_information_array[0]
                if len(disk_information_array) > 1 and len(disk_information_array[1]) > 0:
                    disk_args['storage_domain'] = disk_information_array[1]
                if len(disk_information_array) > 2  and len(disk_information_array[2]) > 0:
                    disk_args['suffix'] = disk_information_array[2]
            elif isinstance(disk_information, dict):
                disk_args.update(disk_information)

            disk_size = disk_args.pop('size', None)
            if disk_size is not None:
                disk_args['size'] = parse_size(disk_size)

            storage_domain = disk_args.pop('storage_domain', None)
            if storage_domain is not None and not 'storage_domains' in disk_args:
                storage_domain = self.get(self.api.storagedomains, storage_domain)
                disk_args['storage_domains'] = params.StorageDomains(storage_domain=[params.StorageDomain(id=storage_domain.id)])

            disk_name_suffix = disk_args.pop('suffix', None)
            if disk_name_suffix is not None and not 'name' in disk_args:
                disk_args['name'] = "%s_%s" % (kwargs['name'], disk_name_suffix)

            disks.append(params.Disk(**disk_args))

        nics = []
        if_name = kwargs.pop('network_name', settings['network_name'])
        if_type = kwargs.pop('network_interface', settings['network_interface'])
        dc = self.get(self.api.datacenters, id=cluster.data_center.id)
        for net_info in kwargs.pop('networks', []):
            net_args = {
                'name': if_name % len(nics),
                'interface': if_type,
            }
            if isinstance(net_info, basestring):
                net_args['network'] = net_info
            elif isinstance(net_info, dict):
                net_args.update(net_info)

            net_name = net_args.pop('network', None)
            if net_name is not None:
                net_args['network'] = params.Network(id=self.get(dc.networks, net_name).id)
            nics.append(params.NIC(**net_args))

        newvm = self.api.vms.add(params.VM(**kwargs))

        newvm.update()

        map(lambda x: newvm.nics.add(x), nics)
        map(lambda x: newvm.disks.add(x), disks)

        still_locked = True
        while still_locked:
            still_locked = False
            for i in self.api.vms.get(id=newvm.id).disks.list():
                if i.active == False:
                    i.set_active(True)
                    i.update()
                    continue
                # lun disks don't have status, skeep them
                still_locked |= (i.status is not None and i.status.state == "locked")
            time.sleep(1)
        return newvm
