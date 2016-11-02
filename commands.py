class CommandSet(object):
    def __init__(self, sendcommand, timers):
        self.send = sendcommand
        self.timers = timers

    # --- basis commands ---

    def timer(self, name, delay, reps, command):
        self.timers.addtimer(name, delay, reps, command)

    def timerdel(self, name):
        return self.timers.deltimer(name)

    def raw(self, command):
        self.send(command)

    # --- specialized commands ---

    def join(self, channels, keys):
        self.send("JOIN {} {}".format(channels, keys))

    def msg(self, target, msg):
        self.send("PRIVMSG {} :{}".format(target, msg))