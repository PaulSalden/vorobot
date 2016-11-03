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

    def signal(self, name, args):
        self.process("{}!".format(name), "_SIGNAL", args)


def ctcpsplit(msg):
    if msg[0] != "\001" or msg[-1] != "\001":
        return ()

    splitmsg = msg[1:-1].split(" ", 1)
    request = splitmsg[0]
    msg = " ".join(splitmsg[1:])

    return request, msg


class Module(object):
    # module blueprint
    def __init__(self, cmd, variables, moduleset):
        self.cmd = cmd
        self.variables = variables
        # allow modules to load/unload modules
        self.moduleset = moduleset

        self.irc_events = {
            "INVITE": self.oninvite,
            "JOIN": self.onjoin,
            "KICK": self.onkick,
            "MODE": self.onmode,
            "NICK": self.onnick,
            "NOTICE": self.relaynotice,
            "PART": self.onpart,
            "PRIVMSG": self.relaymsg,
            "QUIT": self.onquit,
            "TOPIC": self.ontopic,
            "001": self.onconnect,
            "_BOTQUIT": self.ondisconnect,
            "_SIGNAL": self.onsignal,
        }

    def process_(self, prefix, command, args):
        self.onraw(prefix, command, args)

        if command in self.irc_events:
            if "!" in prefix:
                # if prefix is a user, pass nick and address
                nick = prefix.split("!")[0]
                self.irc_events[command](nick, prefix, *args)
            else:
                self.irc_events[command](*args)

    def relaymsg(self, *args):
        # distinguish between ctcp requests, actions and messages
        ctcpdata = ctcpsplit(args[-1])
        if ctcpdata:
            request, msg = ctcpdata

            if request == "ACTION":
                newargs = args[:-1]
                newargs.append(msg)
                self.onaction(*newargs)
            else:
                newargs = args[:-1]
                newargs.extend(ctcpdata)
                self.onctcp(*newargs)
        else:
            self.ontext(*args)

    def relaynotice(self, *args):
        # distinguish between server notices, ctcp replies and user notices
        if len(args) == 2:
            self.onsnotice(*args)
            return

        ctcpdata = ctcpsplit(args[-1])
        if ctcpdata:
            newargs = args[:-1]
            newargs.extend(ctcpdata)
            self.onctcpreply(*newargs)
        else:
            self.onnotice(*args)

    # --- internal events ---

    def onload(self): pass

    def onunload(self): pass

    def ondisconnect(self, *args): pass

    def onsignal(self, name, args): pass

    # --- IRC events ---

    def onraw(self, prefix, command, args): pass

    def onaction(self, nick, address, target, msg): pass

    def onconnect(self, *args): pass

    def onctcp(self, nick, address, target, request, msg): pass

    def onctcpreply(self, nick, address, target, request, msg): pass

    def oninvite(self, nick, address, target, channel): pass

    def onjoin(self, nick, address, channel): pass

    def onkick(self, nick, address, channel, target, msg=None): pass

    def onmode(self, nick, address, channel, modes): pass

    def onnick(self, oldnick, oldaddress, nick): pass

    def onnotice(self, nick, address, target, msg): pass

    def onpart(self, nick, address, channel, msg=None): pass

    def onquit(self, nick, address, msg): pass

    def onsnotice(self, target, msg): pass

    def ontext(self, nick, address, target, msg): pass

    def ontopic(self, nick, address, channel, topic): pass

    def onwallops(self, nick, address, msg): pass
