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
        parser.add_option("--network", dest="network", help="network", default=[], action='append')
        parser.add_option("--disk", dest="disk", help="disk", default=[], action='append')

    def validate(self):
        return True

    def execute(self, *args, **kwargs):
        if 'memory' in kwargs:
            kwargs['memory'] = int(parse_size(kwargs['memory']))
        if 'memory_policy' not in kwargs:
            kwargs['memory_policy'] = params.MemoryPolicy(guaranteed=kwargs['memory'], ballooning=False)
        if 'cluster' in kwargs:
            kwargs['cluster'] = self.api.clusters.get(name=kwargs['cluster'])
        if 'template' in kwargs:
            kwargs['template'] = self.api.templates.get(name=kwargs.pop('template'))
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
            architecture = settings['architecture']
            if not 'soundcard_enabled' in kwargs:
                kwargs['soundcard_enabled'] = settings['soundcard_enabled']
            if not 'type' in kwargs:
                kwargs['type_'] = settings['type']
        if 'type' in kwargs:
            kwargs['type_'] = kwargs.pop('type')

        if not 'cpu' in kwargs:
            kwargs['cpu'] = {'topology': {'cores': 1, 'threads': 1, 'sockets': 1}, 'architecture': architecture}
        # if plain cpu argument was given, it's a number of socket, single core, single thread
        elif 'cpu' in kwargs and not isinstance(kwargs['cpu'], dict):
            num_cpu = int(kwargs.pop('cpu'))
            kwargs['cpu'] = {'topology': {}, 'architecture': architecture}
            kwargs['cpu']['topology']['cores'] = 1
            kwargs['cpu']['topology']['threads'] = 1
            kwargs['cpu']['topology']['sockets'] = num_cpu
        if not 'architecture' in kwargs['cpu']:
            kwargs['cpu']['architecture'] = architecture
        cpu_topology_params = kwargs['cpu'].pop('topology')
        topology = params.CpuTopology(**cpu_topology_params)
        kwargs['cpu'] = params.CPU(architecture=kwargs['cpu']['architecture'], topology=topology)

        os_info = kwargs.pop('os', {})
        if len(boot_devices) > 0:
            os_info['boot'] = boot_devices
        os_info['type_'] = ostype
        kwargs['os'] = params.OperatingSystem(**os_info)

        disks = []
        for disk_information in kwargs.pop('disk', []):
            if isinstance(disk_information, basestring):
                (disk_size, storage_domain) = disk_information.split(",")
            elif isinstance(disk_information, list) or isinstance(disk_information, tuple):
                (disk_size, storage_domain) = disk_information[0:2]
            if len(disks) == 0:
                disk_name = "%s_sys" % kwargs['name']
                disk_bootable = True
            else:
                disk_name = "%s_%d" % (kwargs['name'], len(disks))
                disk_bootable = False
            disks.append(params.Disk(name=disk_name,
                                     storage_domains=params.StorageDomains(storage_domain=[self.api.storagedomains.get(storage_domain)]),
                                     size=int(parse_size(disk_size)),
                                     status=None,
                                     interface=settings['disk_interface'],
                                     format='raw',
                                     sparse=False,
                                     bootable=disk_bootable))

        nics = []
        for network_name in kwargs.pop('network', []):
            nics.append(params.NIC(name=settings['network_name'] % len(nics), network=params.Network(name=network_name), interface=settings['network_interface']))

        newvm = self.api.vms.add(params.VM(**kwargs))

        osi = self.api.operatingsysteminfos.get(name=ostype)
        newvm.set_large_icon(osi.get_large_icon())
        newvm.set_small_icon(osi.get_small_icon())
        newvm.update()

        map(lambda x: newvm.nics.add(x), nics)
        map(lambda x: newvm.disks.add(x), disks)

        still_locked = True
        while still_locked:
            still_locked = False
            for i in self.api.vms.get(id=newvm.id).disks.list():
                still_locked |= (i.status.state == "locked")
            time.sleep(1)
        return newvm
