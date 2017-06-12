oVirtCmd
=====

oVirtCmd is a CLI tool and sdk to manage an ovirt server.

It's written in python and uses the [python SDK from ovirt](http://www.ovirt.org/develop/release-management/features/infra/python-sdk/) version 4.

More documentation about the sdk can be found at [ovirtsdk4 doc](http://ovirt.github.io/ovirt-engine-sdk/master/) or 
[REST API GUIDE for RHV 4.1](https://access.redhat.com/documentation/en-us/red_hat_virtualization/4.1/html/rest_api_guide/)

Howto install in a virtualenv
-----------------------------

    VENV=...
    export PYCURL_SSL_LIBRARY=..
    virtualenv $VENV
    $VENV/bin/python setup.py install
    
On a RedHat familly distribution, the following packages are needed:

    yum install python-virtualenv gcc openssl-devel libcurl-devel libyaml-devel libxml2-devel

and `PYCURL_SSL_LIBRARY` must be set to `nss`. If missing, installation will not be able to detect the good ssl library used. 

For keytab support (see later), one should also run:

    $VENV/bin/pip install gssapi

Usage
=====

CLI
---
oVirtCmd can be used a CLI for oVirt. Each command does a single action. Many of them maps directly to usual
oVirt command, but some are specific to oVirtCmd or try to add functionnality to existing one.

The general command line is

    ovcmd [args] noun [args] verb [args]

The section 'noun' match a generic oVirt object that can be managed using oVirtCmd.

For each noun, there is a set of verbs that can apply to it. Each args section
apply to the preceding term. So `ovcmd -c someting vm` is different from `ovcmd vm -c someting`.

To get a list of noun that can be used, try `ovcmd -h`. For a list ov verb that
can be used with an object, try `ovcmd <noun> -h`.

The verbs are usually taken from the python sdk, but not all are implemented and some are added.

Config file
===========

oVirtCmd use a `ini` file to store settings, a example is given in `sample_config.ini`.

It the environnement variable `OVCONFIG` is given, it will be used to find the config file.


Generic options
===============

The generic options for all noun and verbs are

    -h, --help            show this help message and exit
    -c CONFIG_FILE, --config=CONFIG_FILE
                          an alternative config file
    -d, --debug           The debug level

Noun options
============

Usually a noun option take a filter option that can define on what object it applies.

    -h, --help            show this help message and exit
    -i ID, --id=ID        object ID
    -n NAME, --name=NAME  object tag 'Name'
    -s SEARCH, --search=SEARCH
                        Filter using a search expression

The option id and name obvioulsy return single object. But search can return many. Usually verb will then fail but some 
(like export or list) will operate on each of them.

Templates
=========

Some command that take a import number of arguments like `ovcmd vm create` can take a template as an argument.

A template is a yaml file that provides many settings, they usually duplicate
command line settings, but they can be more detailled. A template can used variables
written as ${variable_name}`.

To use a template, give the argument `-T template_file` to the file and each variables is declared
with `-V variable_name value`.

For example, to create a vm, one can use the template `vm_create.yaml` with

    ovcmd vm create -T vm_create.yaml -V memory 2G -V cores 4 -V cluster cluster01 -V ostype rhel_7x64

Exporting
=========

Many nouns support the export verb, to generate an xml dump of it's setting.

To export sub entries, this verb can take an argument being the sub object name to export.

For example if one exports an host, the command will dump:

    $ ./ovcmd host -n host_name export
    <Host href="/api/hosts/db240f83-9266-4892-a6d2-8ac406cadfb1" id="db240f83-9266-4892-a6d2-8ac406cadfb1">
        <actions>
        ...
        </actions>
        <name>host_name</name>
        <comment></comment>
        <link href="/api/hosts/db240f83-9266-4892-a6d2-8ac406cadfb1/storage" rel="storage"/>
        <link href="/api/hosts/db240f83-9266-4892-a6d2-8ac406cadfb1/nics" rel="nics"/>
        <link href="/api/hosts/db240f83-9266-4892-a6d2-8ac406cadfb1/numanodes" rel="numanodes"/>
        <link href="/api/hosts/db240f83-9266-4892-a6d2-8ac406cadfb1/tags" rel="tags"/>
        <link href="/api/hosts/db240f83-9266-4892-a6d2-8ac406cadfb1/permissions" rel="permissions"/>
        ...
    </Host>

To get the nics sub entrie, the command needs to be

    $ ./ovcmd host -n host_name export nics
    <HostNIC href="/api/hosts/db240f83-9266-4892-a6d2-8ac406cadfb1/nics/958c40cd-9ddb-4548-8bd8-79f454021c35" id="958c40cd-9ddb-4548-8bd8-79f454021c35">
        ...
    </HostNIC>
    ...

The sub entry option can be repeated:

    $ ./ovcmd system export summary vms active
    40

Associated with filter, it can extract the names of all virtual machine running on a given hosts:

    ./ovcmd vm -s 'host=host01' export name

Scripting
---------

oVirtCmd can also be used to script oVirt actions, using python. It mimics closely the usual oVirt's API but try
to hide parts of it's complexity.

In this case, the command line is

    ovcmd eval [-V variable value]* script.py

Scripting is explained with more details at [Scripting in ovirtcmd](https://github.com/fbacchella/ovirtcmd/wiki/Scripting-in-ovirtcmd).

A sample script then looks like:

    mac_pool = context.macpool.get(name="pool_name")
    if mac_pool is None:
        mac_pool = context.macpool().create(name="pool_name", range=('00:1A:4A:16:02:01', '00:1A:4A:16:02:FE'))

    dc = context.datacenter(name="dc_name")
    if dc is None:
        dc = context.datacenter.create(name="dc_name", local=False, storage_format="v3", macpool=mac_pool)


    cluster = context.cluster(name="cl_name")
    if cluster is None:
        cluster = context.cluster.create(name="cl_name}", cpu_type="Intel Haswell-noTSX Family", datacenter=dc,
                             memory_policy={'guaranteed': True, 'overcommit': 100, 'transparent_hugepages': False},
                             ballooning_enabled=True)

Or to get a dump of some elements:

    for i in context.cluster.list():
        print i.export()

    for i in context.host.list():
        for j in i.export("nics"):
            print j

A sample that create a bunch of VM:

    cluster = context.cluster(name="cl_name")

    vms = {}
    for (name, memory, cores, lun_id) in [
                ('vm1', '24G', 12, '1e57ecea-1afd-49b9-9e44-99c119938acc'),
                ('vm2', '24G', 12, '1fe74758-c521-40ed-b8e5-d02d80188088'),
                ('vm3', '64G', 16, '7ea2c97c-251d-434f-b5aa-2efb224b5b8e'),
                ('vm4', '16G',  2, 'f7f7f659-3a41-47c1-bce0-fc0b881562d2'),
                ('vm5', '16G',  8, '966640fd-813b-4ebf-b943-ba7fc1fbafc1'),
                ('vm6', '16G',  8, 'df7b3089-fc9a-46c9-ab95-7820e8ccbfc2'),
        ]:
        new_vm = context.vm(name=name)
        if new_vm is None:
            context.vm().create(name=name,
                                memory=memory,
                                cpu={'architecture': 'X86_64',
                                     'topology': {'cores': cores},
                                     },
                                soundcard_enabled=False,
                                cluster=cluster,
                                timezone='Etc/GMT',
                                bios={'boot_menu': True},
                                type='server',
                                boot_pxe=True,
                                ostype='rhel_7x64',
                                networks=['ovirtmgmt'],
                                disks=[
                                    ['16G', 'vmsys01'],
                                    lun_id,
                                ],
                                template='Blank',
                                disk_interface='virtio_scsi',
                                )
        vms[name] = new_vm

Kerberos support
----------------

The ovirt's sdk natively support kerberos, but oVirtCmd add improved support of keytab. It's configured in [kerberos] section
in the ini file:

    [kerberos]
    ccache=
    keytab=
    principal=

It allows oVirtCmd to load a kerberos identity from a keytab, using a custom principal. The ccache define where tickets will
be stored and can use alternative credential cache, for more information see [MIT's ccache types](http://web.mit.edu/Kerberos/krb5-latest/doc/basic/ccache_def.html#ccache-types).

It uses [Python's GSSAPI](https://pypi.python.org/pypi/gssapi) but it's imported only if needed, so installation is not mandatory.


List of Nouns
=============

### Capabilites

oVirtCmd can enumerate and search capabilities.

The noun associated is `capabilities`.

Usage:

    ovcmd [options] capabilities [object_args] verb [verbs_args]
    verbs are:
        export
        list

    Options:
      -h, --help            show this help message and exit
      -i ID, --id=ID        object ID
      -n VERSION, --name=VERSION
                            capabilities version major.minor

-c return the current capabilities used, -v expect a oVirt version like 3.0 or 3.6, -i is
the UUID for the requested version.

`capabilities list` enumerates all the supported capabilities, returning their version.


### Virtual machines

The noun associated is `vm`.

Know verbs are

 * autoinstall
 * statistics
 * viewer
 * list
 * create
 * stop
 * start
 * export
 * ticket
 * migrating

    Options:
      -h, --help            show this help message and exit
      -i ID, --id=ID        object ID
      -n NAME, --name=NAME  object tag 'Name'

#### Autoinstall

Automaticaly boot on the specified kernel, using a custom command line, it expect this command line to execute an
autoinstallation command. It then wait for the installation to finish and restart the server with the old boot settings.

    Options:
      -h, --help            show this help message and exit
      -V YAMLVARIABLES, --variable=YAMLVARIABLES
      -T YAMLTEMPLATE, --template=YAMLTEMPLATE
      -k KERNEL, --kernel=KERNEL
                            Kernel path
      -i INITRD, --initrd=INITRD
                            Initrd path
      -c CMDLINE, --cmdline=CMDLINE
                            Command line for the kernel

#### ticket

It's used to generate a URL to connect to the console of a virtual machine. It resolve the IP and port information and
also generate a ticket.

#### viewer

Generate a file that can be open by a [SPICE viewer](https://www.spice-space.org/page/Main_Page) to connect to a console.


#### migrating

Show the vm that are actually in migration and show progress.

    Options:
      -h, --help            show this help message and exit
      -f, --follow          Follows status
      -p PAUSE, --pause=PAUSE
                            Pause in seconds between each status


### Hosts

The noun associated is `host`.

Know verbs are

 * upgrade
 * statistics
 * list
 * reboot
 * remove
 * upgradecheck
 * activate
 * export
 * maintenance
 * bond
 * reinstall
 * discoverdomain
 
#### bond

It's used to automatically bond some interfaces from an hosts.

Options:

    -V YAMLVARIABLES, --variable=YAMLVARIABLES
    -T YAMLTEMPLATE, --template=YAMLTEMPLATE
    -i INTERFACES, --interface=INTERFACES
                          Interface to add to bonding
    -m MTU, --mtu=MTU     MTU for the interface
    -n NETWORK, --network=NETWORK
                          Networks to bond
    -o BOND_OPTIONS, --bond_option=BOND_OPTIONS
                          Used as '-o name value'
    -b BOND_NAME, --bond_name=BOND_NAME

This verb encapsulated the given networks on a bonding. If no networks where given, it defaults to 'ovirtmgmt'. The
default bond name is `bond0`, but can be changed if bonded interfaces already exists.

The argument -o is used to specify custom bonding options. They are given as `-o name value` for example `-o xmit_hash_policy "layer2+3"`.

So the full bonding command, for a newly created hosts, and with one additionnal network called `VLAN100` and setting an MTU of 9000 for this new bond0
is:

    ovcmd host -n newhost bond -i eth0 -i eth1 -o miimon 100 -o mode 4 -o xmit_hash_policy "layer2+3" -m 9000

#### upgrade

Used to start the upgrade of a server. It can refresh the upgrade status using `-r`. If a host 
is not already in maintenance status, it will put it in that mode, waiting for it to finish
migration of the all vms. It's default is to wait for the end of the upgrade and leave the host in 
maintenance state.

    Options:
      -h, --help     show this help message and exit
      -a, --async    Don't wait for completion state
      -r, --refresh  Refresh the upgrade status


### datacenter
### network
### os
### system
### cluster
### user
### template
### storagedomain
### disk
### macpool
### event

oVirtCmd internals
===============

### Events enum

A few events are defined in ovlib as symbolic value in a python3's enum, for easier to read code.
More will be added as needed.

### Wrapper object

In oVirtCmd, types, services and writter object are packed together in a simple object with attributes
usually taken from the type object and method taken from the service object. Some can also provide
a few missing helper functions.

The services object than return a list are improved in to way. They are 

### Context

Context is a wrapping function to the api connection.

It provides some resolver that can wrap types, services and list object from the sdk in ovcmd's
object object that increase functionnalites.

In a context object, each top level services can be accessed as a simple attribute like `ctx.vms`or
`ctx.hosts`

### event_waiter

The function event_waiter can be used to wrap some command in a python's `with` clause that will wait for some events.
There is two kind of waiting. Firt it can wait for any event in the given list, using the `break_on` argument. 
It can be also given a list of event that each one must be seen exactly once, using the `wait_for` argument.

For example, if some disks are created and one wait to wait until disks creation is finished:

    from ovlib import event_waiter, EventsCode
    from ovirtsdk4.types import DiskAttachment
    from ovlib.context import Context
    
        ctx = Context(**context_args)
        vm = ctx.vms.get(name='vmname')

        wait_for = []
        for i in newdisks:
            ...
            disks.append(DiskAttachment(...))
            waiting_events += [EventsCode.USER_ADD_DISK_TO_VM_FINISHED_SUCCESS, EventsCode.USER_ADD_DISK_TO_VM]
            
        with event_waiter(ctx, "vm.name=%s" % kwargs['name'], events_returned,
                          wait_for=waiting_events,
                          break_on=[EventsCode.USER_ADD_DISK_TO_VM_FINISHED_FAILURE],
                          verbose=True):
            map(lambda x: vm.disk_attachments.add(x), disks)

It will make event_waiter for one USER_ADD_DISK_TO_VM_FINISHED_SUCCESS and one USER_ADD_DISK_TO_VM for each requested disk
and stop waiting if one fails.
