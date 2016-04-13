#!/usr/bin/env python

import os
import sys
import optparse
import ovlib
from ovlib.context import Context, ConfigurationError

def print_run_phrase(ov_object, verb, object_options={}, object_args=[]):
    (cmd, executed) = ov_object.run_phrase(verb, object_options, object_args)
    if cmd is None:
        print "invalid phrase '%s %s'" % (ov_object.object_name, verb)
        return 255
    # If execute return a generator, iterate other it
    if executed.__class__.__name__ == 'generator':
        for s in executed:
            if s != None:
                string = cmd.to_str(s)
                if string:
                    print string,
                    sys.stdout.flush()
        return cmd.status()
    # Else if it return something, just print it
    elif executed != None and executed:
        string = cmd.to_str(executed)
        if string:
            print string,
        return cmd.status()
    #It return false, something went wrong
    elif executed != None:
        print "'%s %s' failed" % (ov_object.object_name, verb)
    return 255

def main():

    context = None
    default_config = None
    if 'OVCONFIG' in os.environ:
        default_config = os.environ['OVCONFIG']

    usage_common = "usage: %prog [options] object [object_args] verb [verbs_args]"
    #The first level parser
    parser = optparse.OptionParser(usage="%s\nobjects are:\n    %s" % (usage_common, "\n    ".join(ovlib.objects.keys())))
    parser.disable_interspersed_args()
    parser.add_option("-c", "--config", dest="config_file", help="an alternative config file", default=default_config)
    parser.add_option("-d", "--debug", dest="debug", help="The debug level", default=False, action="store_true")

    (options, args) = parser.parse_args()

    #Extract the context from the first level arguments
    kwargs = {}
    for option_name in ('config_file', 'debug'):
        value = getattr(options, option_name, None)
        if value:
            kwargs[option_name] = value
    if len(args) > 0:
        #A object is found try to resolve the verb

        object_name = args.pop(0)

        if object_name in ovlib.objects:
            ov_object = ovlib.objects[object_name]
        else:
            ov_object = None

        if ov_object is None:
            print 'unknonw object: %s' % object_name
            return 253
        #The object parser
        parser_object = optparse.OptionParser()
        parser_object.disable_interspersed_args()
        parser_object.add_option("-i", "--id", dest="id", help="object ID")
        parser_object.add_option("-n", "--name", dest="name", help="object tag 'Name'")
        parser_object.set_usage("%s\nverbs are:\n    %s" % (usage_common, "\n    ".join(ov_object.verbs.keys())))

        (object_options, object_args) = parser_object.parse_args(args)

        if len(object_args) > 0:
            verb = object_args.pop(0)
            try:
                context = Context(**kwargs)
            except (ConfigurationError) as e:
                print e.error_message
                return 253
            try:
                context.connect()
                ov_object.api = context.api
                object_options = vars(object_options)
                for k,v in object_options.items():
                    if v is None:
                        del object_options[k]

                # run the found command and print the result
                status = print_run_phrase(ov_object, verb, object_options, object_args)
                sys.exit(status)
            except (ovlib.OVLibError) as e:
                print "The action \"%s %s\" failed with \"%s\"" % (ov_object.object_name, verb, e.error_message)
            finally:
                if context is not None:
                    context.disconnect()
        else:
            print 'verb missing'
    else:
        print 'object missing'
    return 253


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
