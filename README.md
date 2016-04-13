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

The general command line is

    ovcmd [args] object [args] verb [args]

The section 'object' match a generic Ovirt object that can be managed using
ovcmd.

For each object, there is a set of verbs that can apply to it. Each args section
apply to the preceding term. So `` ovcmd -c someting vm`` is different from ``ovcmd vm -c someting``.

To get a list of object that can be used, try ``ovcmd -h``. For a list ov verb that
can be used with an object, try ``ovcmd <object> -h``.

The verbs are usually taken from the python sdk, but not all are implemented
and some are added.

Config file
===========

ovcmd use a ``ini`` file to store settings, a example is given in ``sample_config.ini``/

It the environnement variable ``OVCONFIG`` is given, it will be used to find the config file.


Templates
=========

Some command that take a import number of arguments like ``ovcmd vm create`` can take a template as an argument.

A template is a yaml file that provides many settings, they usually duplicate
command line settings, but they can be smarter too. A template can used variabes
written as ${variable_name}.

To use a template, give the argument ``-T template_file`` to the file and each variables is declared
with ``-V variable_name value``.

For example, to create a vm, one can use the template ``vm_create.yaml`` with

    ovcmd vm create -T vm_create.yaml -V memory 2G -V cores 4 -V cluster cluster01 -V ostype rhel_7x64


Capabilites
===========

ovcmd can enumerate and search capabilities.

The noun associated is ``capa``

Usage:

    Usage: ovcmd [options] capa [object_args] verb [verbs_args]
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
