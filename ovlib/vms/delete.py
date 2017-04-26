import time
import ovlib.verb
from ovirtsdk4 import types

class Delete(ovlib.verb.Verb):
    verb = "delete"

    def fill_parser(self, parser):
        parser.add_option("-d", "--detach_only", dest="detach_only", help="Detach only the disks, don't destroy", default=False, action='store_true')


    def execute(self, *args, **kwargs):
        if self.broker.status.state != 'down':
            self.broker.stop()
            while self.api.vms.get(id=self.broker.id).status.state != 'down':
                time.sleep(1)
                print '.',

        detach_only = kwargs.pop('detach_only', False)
        action_params = types.Action(
            vm=types.VM(
                disks=types.Disks(detach_only=detach_only is True),
            ),
        )

        self.broker.delete(action = action_params)

        return True
