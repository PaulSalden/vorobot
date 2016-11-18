import strings

# The bot does not issue a WHO command upon joining a channel, because of ircd-specific syntax. Hosts (and
# account names) are therefore not generally available.


prefixmodes = {
    "~": "q",
    "&": "a",
    "@": "o",
    "%": "h",
    "+": "v",
}


class UserData(object):
    def __init__(self):
        self.me = ""
        self.usermodes = set()
        self.channels = {}
        self.nicks = {}
        self.handlers = {
            "JOIN": self.handlejoin,
            "KICK": self.handlekick,
            "MODE": self.handlemode,
            "NICK": self.handlenick,
            "PART": self.handlepart,
            "QUIT": self.handlequit,
            "001": self.handleconnect,
            "353": self.handlenames,
            "366": self.handleeendofnames,
            "_DISCONNECT": self.handledisconnect,
        }

    def getchannels(self):
        return self.channels.values()

    def getchannel(self, channelname):
        if channelname in self.channels:
            return self.channels[channelname]

        return Channel(self, channelname)

    def getnick(self, nickname, host=""):
        if nickname in self.nicks:
            return self.nicks[nickname]

        return Nick(self, nickname, host)

    def getme(self):
        return self.getnick(self.me)

    def process(self, prefix, command, args):
        # modify channels and nicks if necessary
        if command in self.handlers:
            self.handlers[command](prefix, args)

    # --- helper methods ---

    def isme(self, prefix):
        return strings.getnick(prefix) == self.me

    def addtochannel(self, channelname, nickname, modes, host=""):
        if nickname not in self.nicks:
            self.nicks[nickname] = Nick(self, nickname, host)

        nick = self.nicks[nickname]
        nick.channels.add(channelname)

        channel = self.channels[channelname]
        channel.nicks[nickname] = modes

    def removechannel(self, channelname):
        channel = self.channels[channelname]
        for nickname in channel.nicks:
            nick = self.nicks[nickname]
            nick.channels.remove(channelname)

            # remove nicks without common channels
            if not nick.channels:
                del self.nicks[nick]
        del self.channels[channelname]

    def removenick(self, nickname):
        nick = self.nicks[nickname]
        for channelname in nick.channels:
            channel = self.channels[channelname]
            del channel.nicks[nickname]
        del self.nicks[nickname]

    def removefromchannel(self, channelname, nickname):
        channel = self.channels[channelname]
        del channel.nicks[nickname]

        nick = self.nicks[nickname]
        nick.channels.remove(channelname)

        # remove nick if no common channels are left
        if not nick.channels:
            del self.nicks[nickname]

    # --- handlers ---

    def handleconnect(self, prefix, args):
        # set initial bot nickname
        self.me = args[0]

    def handledisconnect(self, prefix, args):
        self.channels = {}
        self.nicks = {}

    def handleeendofnames(self, prefix, args):
        channel = self.channels[args[1]]
        channel._gettingnicks = False

    def handlejoin(self, prefix, args):
        if self.isme(prefix):
            self.channels[args[0]] = Channel(self, args[0])

        nickname = strings.getnick(prefix)
        self.addtochannel(args[0], nickname, set(), prefix)

    def handlekick(self, prefix, args):
        if args[1] == self.me:
            self.removechannel(args[0])
        else:
            self.removefromchannel(args[0], args[1])

    def handlemode(self, prefix, args):
        if args[0] == self.me:
            # handle change in bot user modes
            modechanges = strings.parseusermodes(args[1])
            self.usermodes.update(modechanges["add"])
            self.usermodes.difference_update(modechanges["remove"])
        else:
            # handle change in channel modes
            channel = self.channels[args[0]]
            modechanges = strings.parsechannelmodes(args[1], args[2:])
            for mode, arg in modechanges["add"].items():
                if arg in channel.nicks:
                    channel.nicks[arg].add(mode)

            for mode, arg in modechanges["remove"].items():
                if arg in channel.nicks:
                    channel.nicks[arg].discard(mode)

    def handlenames(self, prefix, args):
        for nickname in args[3].split():
            modes = set()
            if nickname[0] in prefixmodes:
                modes.add(prefixmodes[nickname[0]])
                nickname = nickname[1:]

            self.addtochannel(args[2], nickname, modes)

    def handlenick(self, prefix, args):
        if self.isme(prefix):
            # update bot nickname
            self.me = args[0]

        oldnick = strings.getnick(prefix)
        self.nicks[args[0]] = self.nicks[oldnick]
        del self.nicks[oldnick]

        for channelname in self.nicks[args[0]].channels:
            channel = self.channels[channelname]
            channel.nicks[args[0]] = channel.nicks[oldnick]
            del channel.nicks[oldnick]

    def handlepart(self, prefix, args):
        if self.isme(prefix):
            self.removechannel(args[0])
        else:
            nickname = strings.getnick(prefix)
            self.removefromchannel(args[0], nickname)

    def handlequit(self, prefix, args):
        nickname = strings.getnick(prefix)
        self.removenick(nickname)


class Channel(object):
    def __init__(self, userdata, name):
        self.userdata = userdata
        self.name = name
        self.topic = ""
        self.modes = ""
        # also contains modes
        self.nicks = {}
        self._gettingnicks = True

    def __str__(self):
        return self.name

    def ischannel(self):
        return True

    def equals(self, channelname):
        return channelname == self.name

    def getnicks(self):
        return [self.userdata.nicks[n] for n in self.nicks]


class Nick(object):
    def __init__(self, userdata, name, host=""):
        self.userdata = userdata
        self.name = name
        self.host = host
        self.channels = set()
        self.account = ""

    def __str__(self):
        return self.name

    def ischannel(self):
        return False

    def equals(self, nickname):
        return nickname == self.name

    def getchannels(self):
        return [self.userdata.channels[c] for c in self.channels]

    def comchan(self):
        return self.getchannels()

    def chanmodes(self, channel):
        return channel.nicks[self.name]

    def isme(self):
        return self.name == self.userdata.me
