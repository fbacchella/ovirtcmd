ovcmd
=====

A CLI tool to manage an ovirt server.

It's written in python and uses the [python SDK from ovirt](http://www.ovirt.org/develop/release-management/features/infra/python-sdk/)

Howto install venv

    virtualenv-2.7 venv
    . ./venv/bin/activate
    pip install --upgrade pip
    pip uninstall pycurl
    PYCURL_SSL_LIBRARY=openssl easy_install pycurl
    easy_install ovirt-engine-sdk-python PyYaml

Usage
=====

CLI
---
ovcmd can be used a CLI for oVirt. Each command does a single action. Many of them maps directly to usual
oVirt command, but some are specific to ovcmd or try to add functionnality to existing one.

The general command line is

    ovcmd [args] noun [args] verb [args]

The section 'noun' match a generic Ovirt object that can be managed using
ovcmd.

For each noun, there is a set of verbs that can apply to it. Each args section
apply to the preceding term. So `` ovcmd -c someting vm`` is different from ``ovcmd vm -c someting``.

To get a list of noun that can be used, try ``ovcmd -h``. For a list ov verb that
can be used with an object, try ``ovcmd <noun> -h``.

The verbs are usually taken from the python sdk, but not all are implemented
and some are added.

Scripting
---------

ovcmd can also be used to script oVirt actions, using python. It mimics closely the usual oVirt's API but try
to hide parts of it's complexity.

In this case, the command line is

    ovcmd eval [-V variable value]* script.py

A sample script then looks like:

    dc = context.datacenter(name="${dc_name}")
    if dc is not None:
        dc.delete(force=True)
    context.datacenter().create(name="${dc_name}", local=False, storage_format="v3", mac_pool_name="MoreMac")

    cluster = context.cluster(name="${cl_name}")
    if cluster is not None:
        cluster.delete(force=True)
    context.cluster().create(name="${cl_name}", cpu_type="Intel Haswell-noTSX Family", dc_name="${dc_name}",
                             memory_policy={'guaranteed': True, 'overcommit': 100, 'transparent_hugepages': False},
                             ballooning_enabled=True)


Config file
===========

ovcmd use a ``ini`` file to store settings, a example is given in ``sample_config.ini``/

It the environnement variable ``OVCONFIG`` is given, it will be used to find the config file.


Templates
=========

Some command that take a import number of arguments like ``ovcmd vm create`` can take a template as an argument.

A template is a yaml file that provides many settings, they usually duplicate
command line settings, but they can be smarter too. A template can used variables
written as ${variable_name}.

To use a template, give the argument ``-T template_file`` to the file and each variables is declared
with ``-V variable_name value``.

For example, to create a vm, one can use the template ``vm_create.yaml`` with

    ovcmd vm create -T vm_create.yaml -V memory 2G -V cores 4 -V cluster cluster01 -V ostype rhel_7x64

Exporting
=========

Many noun support the export verb, to generate an xml dump of it's setting.

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

Capabilites
===========

ovcmd can enumerate and search capabilities.

The noun associated is ``capa``.

Usage:

    ovcmd [options] capa [object_args] verb [verbs_args]
    verbs are:
        export
        list

    Options:
      -h, --help            show this help message and exit
      -i ID, --id=ID        object ID
      -v VERSION, --version=VERSION
                            capabilities version major.minor
      -c, --current         Get the current capabilities

-c return the current capabilities used, -v expect a oVirt version like 3.0 or 3.6, -i is
the UUID for the requested version.

```capa list` enumerates all the supported capabilities, returning there version, the UUID and prefixing
the current one with a 'c'


Virtual machines
================

The noun associated is ``vm``.

Usage:

    ovcmd [options] object [object_args] verb [verbs_args]
    verbs are:
        autoinstall
        create
        list
        start
        export
        ticket
        delete

    Options:
      -h, --help            show this help message and exit
      -i ID, --id=ID        object ID
      -n NAME, --name=NAME  object tag 'Name'

Autoinstall
-----------

Usage: Automaticaly boot on the specified kernel, using a custom command line, it expected to execute an autoinstallation command

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
