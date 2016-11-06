import importlib
import inspect
import logging
import re
import commands
import timers
import userdata

MODULEPATH = "remote."


# helper functions
def isaction(msg):
    return re.match("^\\001ACTION.*\\001$", msg)


def isctcp(msg):
    return re.match("^\\001.*\\001$", msg)


# NOTE: modules are the files remote classes reside in

class RemoteSet(object):
    def __init__(self, send):
        self.modules = {}
        self.handlers = {}

        self.cmd = commands.CommandSet(send)
        self.timers = timers.TimerSet()
        self.aliases = {}
        self.variables = {}
        self.userdata = userdata.UserData()

    def loadremote(self, modulename, remotenames=None):
        # allows for reloading too!
        loadedremotes = []

        if not self._loadmodule(modulename):
            return loadedremotes

        module = self.modules[modulename]

        # if remotenames is not specified, load all remotes in the module
        if not remotenames:
            for cname in dir(module):
                c = getattr(module, cname)
                if inspect.isclass(c) and issubclass(c, Remote):  # could use isinstance() but avoiding confusion
                    remote = c(self.cmd, self.aliases, self.variables)
                    self._loadhandlers(modulename, cname, remote)
                    loadedremotes.append(cname)
        else:
            for cname in remotenames:
                success = False
                if cname in dir(module):
                    c = getattr(module, cname)
                    if inspect.isclass(c) and issubclass(c, Remote):
                        remote = c(self.cmd, self.aliases, self.variables)
                        self._loadhandlers(modulename, cname, remote)
                        loadedremotes.append(cname)
                        success = True

                if not success:
                    warning = "Could not load remote {!r} from module {!r}."
                    logging.warning(warning.format(modulename, cname))

        return loadedremotes

    def _loadmodule(self, modulename):
        # not meant to be called directly
        if modulename not in self.modules:
            try:
                self.modules[modulename] = importlib.import_module(MODULEPATH + modulename)
            except Exception as e:
                warning = "Could not import module !r}: {}"
                logging.warning(warning.format(modulename, e))
                return False

            self.handlers[modulename] = {}
        else:
            try:
                importlib.reload(self.modules[modulename])
            except Exception as e:
                warning = "Could not reload module {!r}: {}"
                logging.warning(warning.format(modulename, e))
                return False

        return True

    def _loadhandlers(self, modulename, remotename, remote):
        # not meant to be called directly
        handlers = {}
        for cname in dir(remote):
            c = getattr(remote, cname)
            if hasattr(c, "ishandler"):
                command = getattr(c, "command")

                if command not in handlers:
                    handlers[command] = [c]
                else:
                    handlers[command].append(c)

        self.handlers[modulename][remotename] = handlers

        # execute onload()
        if "_LOAD" in handlers:
            for h in handlers["_LOAD"]:
                try:
                    h()
                except Exception as e:
                    warning = "Could not process onload handler for module {!r} / remote {!r}: {}"
                    logging.warning(warning.format(modulename, remotename, e))

        logging.info("Loaded module {!r} / remote {!r}.".format(modulename, remotename))

    def unloadremote(self, modulename, remotenames=None):
        # module stays imported
        unloadedremotes = []

        if modulename not in self.handlers:
            warning = "No loaded module {!r}."
            logging.warning(warning.format(modulename))
            return unloadedremotes

        # if remotenames is not specified, unload all remotes in the module
        if not remotenames:
            for remotename in self.handlers[modulename]:
                self._unloadhandlers(modulename, remotename)
                unloadedremotes.append(remotename)
        else:
            for remotename in remotenames:
                if remotename not in self.handlers[modulename]:
                    warning = "Remote {!r} for module {!r} not loaded."
                    logging.warning(warning.format(remotename, modulename))
                else:
                    self._unloadhandlers(modulename, remotename)
                    unloadedremotes.append(remotename)

        return unloadedremotes

    def _unloadhandlers(self, modulename, remotename):
        # not meant to be called directly

        # execute onunload()
        handlers = self.handlers[modulename][remotename]
        if "_UNLOAD" in handlers:
            for h in handlers["_UNLOAD"]:
                try:
                    h()
                except Exception as e:
                    warning = "Could not process onunload handler for module {!r} / remote {!r}: {}"
                    logging.warning(warning.format(modulename, remotename, e))

        del self.handlers[modulename][remotename]
        logging.info("Unloaded module {!r} / remote {!r}.".format(modulename, remotename))

    def process(self, prefix, command, args):
        self.userdata.process(prefix, command, args)

        # properly split up messages and notices
        if command == "PRIVMSG":
            if isaction(args[0]):
                command = "ACTION"
            elif isctcp(args[0]):
                command = "CTCP"

        if command == "NOTICE":
            if isctcp(args[0]):
                command = "CTCPREPLY"

        for modulename, remotedict in self.handlers.items():
            for remotename, handlers in remotedict.items():
                # process raw handlers
                if "RAW" in handlers:
                    for handler in handlers["RAW"]:
                        try:
                            handler(self.userdata, prefix, command, args)
                        except Exception as e:
                            msg = "Could not process raw handler for command {!r} in module {!r} / remote {!r}: {}"
                            logging.warning(msg.format(command, modulename, remotename, e))

                # process command specific handlers
                if command in handlers:
                    for handler in handlers[command]:
                        try:
                            handler(self.userdata, prefix, command, args)
                        except Exception as e:
                            msg = "Could not process command handler for {!r} in module {!r} / remote {!r}: {}"
                            logging.warning(msg.format(command, modulename, remotename, e))

    def processtimers(self):
        return self.timers.process()

    def signal(self, name, args):
        self.process("{}!".format(name), "_SIGNAL", args)


class Remote(object):
    # remote blueprint
    def __init__(self, cmd, aliases, variables):
        self.cmd = cmd
        self.aliases = aliases
        self.variables = variables
