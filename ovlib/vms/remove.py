import time
import ovlib.verb
from ovirtsdk4.types import VmStatus

from ovlib.vms import VmDispatcher
from ovlib.dispatcher import command

@command(VmDispatcher)
class Remove(ovlib.verb.Remove):

    def fill_parser(self, parser):
        parser.add_option("-d", "--detach_only", dest="detach_only", help="Detach only the disks, don't destroy", default=False, action='store_true')

    def execute(self, detach_only=False, *args, **kwargs):
        if self.object.status != VmStatus.DOWN:
            self.object.stop()
            self.object.wait_for(VmStatus.DOWN)

        self.object.remove(detach_only=detach_only)

        return True
