import time

from enum import IntEnum
from contextlib import contextmanager

from ovlib import OVLibError

# See
# https://bugzilla.redhat.com/show_bug.cgi?id=1453170
# and
# https://github.com/oVirt/ovirt-engine/blob/master/backend/manager/modules/common/src/main/java/org/ovirt/engine/core/common/AuditLogType.java
class EventsCode(IntEnum):
    UNDEFINED = -1
    # When a host is up
    VDS_DETECTED = 13
    VDS_NO_SELINUX_ENFORCEMENT = 25
    IRS_DISK_SPACE_LOW = 26
    USER_RUN_VM = 32
    USER_STOP_VM = 33
    USER_ADD_VM = 34
    USER_UPDATE_VM = 35
    USER_ADD_VM_STARTED = 37
    USER_ADD_VM_FINISHED_SUCCESS = 53
    USER_FAILED_ADD_VM = 57
    USER_ADD_VM_FINISHED_FAILURE = 60
    VM_DOWN = 61
    USER_ADD_DISK_TO_VM = 78
    USER_ADD_DISK_TO_VM_FINISHED_SUCCESS = 97
    USER_ADD_DISK_TO_VM_FINISHED_FAILURE = 98
    VM_MIGRATION_TRYING_RERUN = 128
    VM_PAUSED_ENOSPC = 138
    USER_STARTED_VM = 153
    VM_SET_TICKET = 164
    VM_CONSOLE_CONNECTED = 167
    VM_CONSOLE_DISCONNECTED = 168
    VM_RECOVERED_FROM_PAUSE_ERROR = 196
    IRS_HOSTED_ON_VDS = 204
    VDS_INSTALL_IN_PROGRESS_ERROR = 511
    VDS_INITIALIZING = 514
    VDS_DOMAIN_DELAY_INTERVAL =524
    HOST_AVAILABLE_UPDATES_FAILED = 839
    HOST_UPGRADE_STARTED = 840
    HOST_UPGRADE_FAILED = 841
    HOST_UPGRADE_FINISHED = 842
    HOST_UPDATES_ARE_AVAILABLE_WITH_PACKAGES = 843
    HOST_UPDATES_ARE_AVAILABLE = 844
    HOST_AVAILABLE_UPDATES_FINISHED = 885
    HOST_AVAILABLE_UPDATES_PROCESS_IS_ALREADY_RUNNING = 886
    HOST_AVAILABLE_UPDATES_SKIPPED_UNSUPPORTED_STATUS = 887
    HOST_UPGRADE_FINISHED_MANUAL_HA = 890
    NETWORK_ADD_VM_INTERFACE = 932
    SYSTEM_CHANGE_STORAGE_POOL_STATUS_PROBLEMATIC = 980
    NETWORK_ACTIVATE_VM_INTERFACE_SUCCESS = 1012
    NETWORK_ACTIVATE_VM_INTERFACE_FAILURE = 1013
    VM_PAUSED = 1025
    NUMA_ADD_VM_NUMA_NODE_SUCCESS = 1300
    USER_SPARSIFY_IMAGE_START = 1325
    USER_SPARSIFY_IMAGE_FINISH_SUCCESS = 1326
    USER_HOTUNPLUG_DISK = 2002
    USER_FINISHED_REMOVE_DISK = 2014
    USER_ATTACH_DISK_TO_VM = 2016
    USER_FAILED_ATTACH_DISK_TO_VM = 2017
    USER_ADD_DISK = 2020
    USER_ADD_DISK_FINISHED_SUCCESS = 2021
    USER_ADD_DISK_FINISHED_FAILURE = 2022
    USER_FAILED_ADD_DISK = 2023
    USER_FINISHED_REMOVE_DISK_ATTACHED_TO_VMS = 2042
    VDS_HOST_NOT_RESPONDING_CONNECTING = 9008
    ENGINE_BACKUP_STARTED = 9024
    ENGINE_BACKUP_COMPLETED = 9025
    DWH_STARTED = 9700
    AFFINITY_RULES_ENFORCEMENT_MANAGER_START = 10780
    STORAGE_POOL_LOWER_THAN_ENGINE_HIGHEST_CLUSTER_LEVEL = 10812


@contextmanager
def event_waiter(api, object_filter, events, wait_for=[], break_on=[], timeout=1000, wait=1, verbose=False):
    # Works on copy, as we don't know where the arguments are coming from.
    break_on=[x.value for x in break_on]
    wait_for=[x.value for x in wait_for]
    last_event = api.events.get_last()
    yield
    end_of_wait =  time.time() + timeout
    while True:
        search = '%s and %s' % (object_filter, " or ".join(["type=%s" % x for x in set(wait_for + break_on)]))
        if time.time() > end_of_wait:
            raise OVLibError("Timeout will waiting for events", value={'ids': wait_for})
        founds = list(api.events.list(
            from_= last_event,
            search=search,
        ))
        if len(founds) > 0:
            last_event = int(founds[-1].id)
            for j in founds:
                j_wrapped = api.wrap(j)
                events += [j_wrapped]
                if verbose:
                    print(("%s" % j_wrapped.export(['description']).strip()))
            stop_id = [x for x in [int(x.code) for x in founds] if x in break_on]
            if len(stop_id) > 0:
                break
            for x in founds:
                try:
                    wait_for.remove(int(x.code))
                except ValueError:
                    pass
            if len(wait_for) == 0:
                break
        time.sleep(wait)


