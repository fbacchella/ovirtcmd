from ovlib import OVLibError, load_template, dispatchers


def command(dispatcher_class, verb=None):
    def decorator(command_class):
        if verb is not None:
            command_class.verb = verb
        dispatchers[dispatcher_class.object_name].verbs[command_class.verb] = command_class
        return command_class
    return decorator


def dispatcher(object_name, wrapper, list_wrapper):
    def decorator(dispatcher_class):
        dispatcher_class.object_name = object_name
        dispatcher_class.list_wrapper = list_wrapper
        dispatcher_class.wrapper = wrapper
        list_wrapper.wrapper = wrapper
        wrapper.dispatcher = dispatcher_class
        list_wrapper.dispatcher = dispatcher_class
        setattr(dispatcher_class, 'verbs', {})
        dispatchers[object_name] = dispatcher_class

        return dispatcher_class
    return decorator


class Dispatcher(object):

    def __init__(self):
        self._api = None

    def add_command(self, new_command):
        self.verbs[new_command.verb] = new_command

    def fill_parser(self, parser):
        parser.add_option("-i", "--id", dest="id", help="object ID")
        parser.add_option("-n", "--name", dest="name", help="object tag 'Name'")
        parser.add_option("-s", "--search", dest="search", help="Filter using a search expression")

    def execute(self, name, method_args=[], method_kwargs={}):
        NameError('Not implemented')

    def get_cmd(self, verb):
        if verb in self.verbs:
            cmd_class = self.verbs[verb]
            cmd = cmd_class(self)
            return cmd
        else:
            # Everything failed so return false
            return False

    def fill_template(self, template, variables):
        if template is None:
            if len(variables) > 0:
                raise OVLibError("YAML template not found")
            return {}
        else:
            return load_template(template, variables)

    def run_phrase(self, verb, object_options={}, object_args=[]):
        cmd = self.get_cmd(verb)
        if cmd:
            (verb_options, verb_args) = cmd.parse(object_args)

            # transform options to a dict and removed undeclared arguments or empty enumerations
            # but keep empty string
            verb_options = {k: v for k, v in list(vars(verb_options).items())
                            if v is not None and (isinstance(v, str) or not hasattr(v, '__len__') or len(v) != 0)}
            return self.execute_phrase(cmd, object_options, verb_options, verb_args)
        else:
            raise OVLibError("unknown verb %s" % verb)


    def execute_phrase(self, cmd, object_options={}, verb_options={}, verb_args=[]):
        if cmd.object is None:
            cmd.object = cmd.get(self._lister, **object_options)

        if cmd.validate():
            if cmd.uses_template():
                yamltemplate = verb_options.pop('yamltemplate', None)
                yamlvariables = verb_options.pop('yamlvariables', {})
                template = self.fill_template(yamltemplate, yamlvariables)
                for (k, v) in list(template.items()):
                    if k not in verb_options and v is not None:
                        verb_options[k] = v
            return (cmd, cmd.execute(*verb_args, **verb_options))
        else:
            raise OVLibError("validation failed")

    @property
    def api(self):
        return self._api

    @api.setter
    def api(self, api):
        self._api = api
        self._lister = api.register_root_service(self.__class__.list_wrapper)


