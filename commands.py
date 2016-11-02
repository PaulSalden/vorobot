import logging


class CommandSet(object):
    def __init__(self, sendcommand, timers):
        self.send = sendcommand
        self.timers = timers
        self.aliases = {}

    # --- basic commands ---

    def timer(self, name, delay, reps, command):
        self.timers.addtimer(name, delay, reps, command)

    def timerdel(self, name):
        return self.timers.deltimer(name)

    def alias(self, name, *args):
        if name in self.aliases:
            try:
                return self.aliases["name"](*args)
            except Exception as e:
                logging.warning("Failed to execute alias {!r}: {}".format(name, e))
        else:
            logging.warning("Alias {!r} to be executed not found.".format(name))

    def addalias(self, name, command):
        self.aliases[name] = command
        logging.info("Added alias {!r}.".format(name))

    def delalias(self, name):
        if name in self.aliases:
            del self.aliases[name]
            logging.info("Deleted alias {!r}.".format(name))
        else:
            logging.warning("Alias {!r} to be deleted not found.".format(name))

    def raw(self, command):
        self.send(command)

    # --- specialized commands ---

    def join(self, channels, keys=None):
        if keys:
            self.send("JOIN {} {}".format(channels, keys))
        else:
            self.send("JOIN {}".format(channels))

    def msg(self, target, msg):
        self.send("PRIVMSG {} :{}".format(target, msg))