from ovirtsdk4 import types

from ovlib.vms import VmDispatcher
from ovlib import command
from ovlib.verb import Verb

@command(VmDispatcher, verb='autoinstall')
class Autoinstall(Verb):
    """Automaticaly boot on the specified kernel, using a custom command line, it expected to execute an autoinstallation command"""

    def fill_parser(self, parser):
        parser.add_option("-k", "--kernel", dest="kernel", help="Kernel path", default=None)
        parser.add_option("-i", "--initrd", dest="initrd", help="Initrd path", default=None)
        parser.add_option("-c", "--cmdline", dest="cmdline", help="Command line for the kernel", default=None)

    def uses_template(self):
        return True

    def execute(self, *args, **kwargs):
        if self.type.status != types.VmStatus.DOWN:
            self.service.stop()
            self.wait_for(types.VmStatus.DOWN)

        old_os_params =  self.type.os
        old_kernel = old_os_params.kernel
        if old_kernel is None:
            old_kernel = ''
        old_initrd = old_os_params.initrd
        if old_initrd is None:
            old_initrd = ''
        old_cmdline = old_os_params.cmdline
        if old_cmdline is None:
            old_cmdline = ''
        old_os_params.kernel = kwargs.get('kernel', None)
        old_os_params.initrd = kwargs.get('initrd', None)
        old_os_params.cmdline = kwargs.get('cmdline', None)

        self.service.update(
            types.Vm(
                os=types.OperatingSystem(
                    kernel=kwargs.get('kernel', None),
                    initrd = kwargs.get('initrd', None),
                    cmdline=kwargs.get('cmdline', None)
            )
        ))

        self.service.start()
        self.wait_for(types.VmStatus.UP)
        yield "booted, run installing\n"
        self.wait_for(types.VmStatus.DOWN)

        self.service.update(
            types.Vm(
                os=types.OperatingSystem(
                    kernel=old_kernel,
                    initrd=old_initrd,
                    cmdline=old_cmdline
                )
            ))

        self.service.start()
        yield "done\n"
