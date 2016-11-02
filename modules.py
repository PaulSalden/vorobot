import importlib
import logging
import commands
import timers

MODULEPATH = "remote."


class ModuleSet(object):
    def __init__(self, send):
        self.modules = {}
        self.remotes = {}

        self.cmd = commands.CommandSet(send)
        self.timers = timers.TimerSet()
        self.aliases = {}
        self.variables = {}

    def loadmodule(self, module):
        # allows for reloading too!

        # import python module
        if module not in self.modules:
            try:
                self.modules[module] = importlib.import_module(MODULEPATH + module)
            except Exception as e:
                warning = "Could not import module !r}: {}".format(module, e)
                logging.warning(warning)
                return warning
        else:
            try:
                importlib.reload(self.modules[module])
            except Exception as e:
                warning = "Could not reload module {!r}: {}".format(module, e)
                logging.warning(warning)
                return warning

        # instantiate and store Remote object
        try:
            self.remotes[module] = self.modules[module].Remote(self.cmd, self.variables, self)
            logging.info("Loaded module {!r}.".format(module))
        except Exception as e:
            warning = "Could not instantiate Remote object from module {!r}: {}".format(module, e)
            logging.warning(warning)
            return warning

        # execute onload()
        try:
            self.remotes[module].onload()
        except Exception as e:
            warning = "Could not execute onload() for module {!r}: {}".format(module, e)
            logging.warning(warning)
            return warning

        return True

    def unloadmodule(self, module):
        # module stays imported
        if module in self.remotes:
            # execute onunload()
            try:
                self.remotes[module].onunload()
            except Exception as e:
                warning = "Could not execute onunload() for module {!r}: {}".format(module, e)
                logging.warning(warning)
                return warning

            del self.remotes[module]
            logging.info("Unloaded module {!r}.".format(module))
        else:
            warning = "No module {!r} for unloading.".format(module)
            logging.warning(warning)
            return warning

    def process(self, prefix, command, args):
        for n, r in self.remotes.items():
            try:
                r.process_(prefix, command, args)
            except Exception as e:
                logging.warning("Could not process command {!r} for module {!r}: {}".format(command, n, e))

    def processtimers(self):
        return self.timers.process()


class Module(object):
    # module blueprint
    def __init__(self, cmd, variables, moduleset):
        self.cmd = cmd
        self.variables = variables
        # allow modules to load/unload modules
        self.moduleset = moduleset

        self.irc_events = {
            "PRIVMSG": self.ontext,
            "001": self.onconnect,
            "BOTQUIT": self.ondisconnect,
        }

    def process_(self, prefix, command, args):
        self.onraw(prefix, command, args)

        if command in self.irc_events:
            if "!" in prefix:
                # if a nickname is present, send it along
                nick = prefix.split("!")[0]
                self.irc_events[command](nick, *args)
            else:
                self.irc_events[command](*args)

    # --- internal events ---

    def onload(self): pass

    def onunload(self): pass

    def ondisconnect(self, *args): pass

    # --- IRC events ---

    def onraw(self, prefix, command, args): pass

    def onconnect(self, *args): pass

    def ontext(self, nick, target, msg): pass
