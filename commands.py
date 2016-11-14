class CommandSet(object):
    def __init__(self, sendcommand, tasks):
        self.send = sendcommand
        self.tasks = tasks

    def raw(self, command):
        self.send(command)

    # --- specialized commands ---

    def away(self, message=None):
        if message:
            self.raw("AWAY {}".format(message))
        else:
            self.raw("AWAY")

    def invite(self, nick, channel):
        self.raw("INVITE {} {}".format(nick, channel))

    def ison(self, nicks):
        self.raw("ISON {}".format(nicks))

    def join(self, channels, keys=None):
        if keys:
            self.send("JOIN {} {}".format(channels, keys))
        else:
            self.send("JOIN {}".format(channels))

    def kick(self, channel, nick, msg=None):
        if msg:
            self.raw("KICK {} {} :{}".format(channel, nick, msg))
        else:
            self.raw("KICK {} {}".format(channel, nick))

    def mode(self, target, flags, args=None):
        if args:
            self.raw("MODE {} {} {}".format(target, flags, args))
        else:
            self.raw("MODE {} {}".format(target, flags))

    def names(self, channels):
        self.raw("NAMES {}".format(channels))

    def nick(self, nick):
        self.raw("NICK {}".format(nick))

    def notice(self, target, msg):
        self.raw("NOTICE {} :{}".format(target, msg))

    def part(self, channels):
        self.raw("PART {}".format(channels))

    def msg(self, target, msg):
        self.send("PRIVMSG {} :{}".format(target, msg))

    def quit(self, msg=None):
        if msg:
            self.raw("QUIT :{}".format(msg))
        else:
            self.raw("QUIT")

    def time(self):
        self.raw("TIME")

    def topic(self, channel, topic=None):
        if topic:
            self.raw("TOPIC {} :{}".format(channel, topic))
        else:
            self.raw("TOPIC {}".format(channel))

    def userhost(self, nicks):
        self.raw("USERHOST {}".format(nicks))

    def version(self):
        self.raw("VERSION")

    def wallops(self, msg):
        self.raw("WALLOPS :{}".format(msg))

    def wallusers(self, msg):
        self.raw("WALLUSERS :{}".format(msg))

    def who(self, targets, flags=None):
        if flags:
            self.raw("WHO {} {}".format(targets, flags))
        else:
            self.raw("WHO {}".format(targets))

    def whois(self, nicks):
        self.raw("WHOIS {}".format(nicks))

    def whowas(self, nicks, count=None):
        if count:
            self.raw("WHOWAS {} {}".format(nicks, count))
        else:
            self.raw("WHOWAS {}".format(nicks))

    # --- special messages ---

    def describe(self, target, msg):
        self.msg(target, "\001ACTION {}\001".format(msg))

    def ctcp(self, target, request):
        self.msg(target, "\001{}\001".format(request.upper()))

    def ctcpreply(self, target, request, msg):
        self.notice(target, "\001{} {}\001".format(request.upper(), msg))

    # --- task commands ---

    def timer(self, *args):
        self.tasks.addtimer(*args)
        pass

    def timerdel(self, *args):
        self.tasks.removetimer(*args)

    def bgprocess(self, command):
        self.tasks.dobgprocess(command)
