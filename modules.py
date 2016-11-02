import commands
import importlib
import logging

MODULEPATH = "remote."


class ModuleSet(object):
    def __init__(self, sendcommand, variables):
        self.cmd = commands.CommandSet(sendcommand)
        self.variables = variables
        self.modules = {}
        self.remotes = {}

    def loadmodule(self, module):
        # allows for reloading too!

        # import python module
        if module not in self.modules:
            try:
                self.modules[module] = __import__(MODULEPATH + module)
            except Exception as e:
                logging.warning("Could not import module !r}: {}".format(module, e))
                return
        else:
            try:
                importlib.reload(self.modules[module])
            except Exception as e:
                logging.warning("Could not reload module {!r}: {}".format(module, e))

        # instantiate and store Remote object
        try:
            self.remotes[module] = self.modules[module].Remote(self.cmd, self.variables, self)
            logging.info("Loaded module {!r}.".format(module))
        except Exception as e:
            logging.warning("Could not instantiate Remote object from module {!r}: {}".format(module, e))

        # execute onload()
        try:
            self.remotes[module].onload()
        except Exception as e:
            logging.warning("Could not execute onload() for module {!r}: {}".format(module, e))

    def unloadmodule(self, module):
        # module stays imported
        if module in self.remotes:
            # execute onunload()
            try:
                self.remotes[module].onunload()
            except Exception as e:
                logging.warning("Could not execute onunload() for module {!r}: {}".format(module, e))

            del self.remotes[module]
            logging.info("Unloaded module {!r}.".format(module))
        else:
            logging.warning("No module {!r} for unloading.".format(module))

    def process(self, prefix, command, args):
        for n, r in self.remotes.items():
            try:
                r.process(prefix, command, args)
            except Exception as e:
                logging.warning("Could not process command {!r} for module {!r}: {}".format(command, n, e))


class Module(object):
    # module blueprint
    def __init__(self, cmd, variables, moduleset):
        self.cmd = cmd
        self.variables = variables
        # allow modules to load/unload modules
        self.moduleset = moduleset

    def process(self, prefix, command, args):
        # distribute to appropriate methods here, deal with custom BOTQUIT command
        pass

    def onload(self): pass

    def onunload(self): pass

    def onbotquit(self): pass
