from ovirtsdk4.types import VmStatus

from ovlib.vms import VmDispatcher
from ovlib.dispatcher import command
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

    def execute(self, kernel=None, initrd=None, cmdline=None, *args, **kwargs):
        if self.object.status != VmStatus.DOWN:
            self.object.stop()
            self.object.wait_for(VmStatus.DOWN)

        old_os_params =  self.object.os
        old_kernel = old_os_params.kernel
        if old_kernel is None:
            old_kernel = ''
        old_initrd = old_os_params.initrd
        if old_initrd is None:
            old_initrd = ''
        old_cmdline = old_os_params.cmdline
        if old_cmdline is None:
            old_cmdline = ''

        self.object.update(
            vm = {
                'os': {
                    'kernel': kernel.strip(),
                    'initrd': initrd.strip(),
                    'cmdline': cmdline.strip()
                }
            }
        )

        self.object.start()
        self.object.wait_for(VmStatus.UP)
        yield "booted, run installing\n"
        self.object.wait_for(VmStatus.DOWN)

        self.object.update(
            vm = {
                'os': {
                    'kernel': old_kernel,
                    'initrd': old_initrd,
                    'cmdline': old_cmdline
                }
            }
        )

        self.object.start()
        yield "done\n"
