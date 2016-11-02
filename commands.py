class CommandSet(object):
    def __init__(self, sendcommand):
        self.send = sendcommand

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