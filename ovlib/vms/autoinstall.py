import time

import ovlib.verb
from ovlib import parse_size
from ovirtsdk.xml import params

class Autoinstall(ovlib.verb.List):
    """Automaticaly boot on the specified kernel, using a custom command line, it expected to execute an autoinstallation command"""
    verb = "autoinstall"

    def fill_parser(self, parser):
        parser.add_option("-k", "--kernel", dest="kernel", help="Kernel path", default=None)
        parser.add_option("-i", "--initrd", dest="initrd", help="Initrd path", default=None)
        parser.add_option("-c", "--cmdline", dest="cmdline", help="Command line for the kernel", default=None)

    def validate(self):
        return True

    def uses_template(self):
        return True

    def execute(self, *args, **kwargs):
        # removed undeclared arguments
        for (k, v) in kwargs.items():
            if v is None:
                del kwargs[k]

        if self.broker.status.state != 'down':
            self.broker.stop()
            while True:
                self.broker = self.api.vms.get(id=self.broker.id)
                if self.broker.status.state == 'down':
                    break
                time.sleep(1)


        old_os_params =  self.broker.get_os()
        old_kernel = old_os_params.get_kernel()
        old_initrd = old_os_params.get_initrd()
        old_cmdline = old_os_params.get_cmdline()
        old_os_params.set_kernel(kwargs.get('kernel', None))
        old_os_params.set_initrd(kwargs.get('initrd', None))
        old_os_params.set_cmdline(kwargs.get('cmdline', None))

        self.broker.set_os(old_os_params)
        self.broker.update()
        self.broker.start()
        while True:
            self.broker = self.api.vms.get(id=self.broker.id)
            if self.broker.status.state == 'up':
                break
            yield "."
            time.sleep(1)
        yield "booted, run installing\n"
        while True:
            self.broker = self.api.vms.get(id=self.broker.id)
            if self.broker.status.state == 'down':
                break
            yield "."
            time.sleep(1)
        os_params =  params.OperatingSystem()
        os_params.set_boot(old_os_params.get_boot())
        os_params.set_type(old_os_params.get_type())
        os_params.set_kernel(old_kernel)
        os_params.set_initrd(old_initrd)
        os_params.set_cmdline(old_cmdline)
        self.broker.set_os(os_params)
        self.broker.update()
        self.broker.start()
        yield "done\n"
