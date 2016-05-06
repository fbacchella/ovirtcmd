import time
import ovlib.verb
from ovirtsdk.xml import params

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
        action_params = params.Action(
            vm=params.VM(
                disks=params.Disks(detach_only=detach_only == True),
            ),
        )

        self.broker.delete(action = action_params)

        return True
