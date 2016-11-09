import random
import handlers
import remotes


# specify a maximum amount of targets to include in a WHO command
# (note: It would be better to calculate the command length, but that would then also require combining
# the optimal nicks etc. It is chosen to keep this simple.)
MAXTARGETS = 20
# delay in seconds between WHO commands on previously unauthed users
WHODELAY = 60


class Auths(remotes.Remote):
    @handlers.onload
    def loadhandler(self):
        self.whoid = random.randint(1, 999)
        self.whos = set()
        self.unauthed = set()

    @handlers.onconnect
    def connecthandler(self):
        self.cmd.timer("authwho", WHODELAY, 0, self.checkunauthed)

    @handlers.onjoin("#")
    def joinhandler(self, nick, channel):
        if nick.isme():
            self.who(channel)
        elif not nick.account:
            self.who(nick)

    @handlers.raw("315", "")
    def endofwhohandler(self, *args):
        whoid = args[0].split(",")[-1]
        self.whos.discard(whoid)

    @handlers.raw("354", "")
    def whohandler(self, *args):
        if args[1] in self.whos:
            username, host, nickname, account, realname = args[2:]
            nick = self.id.nick(nickname)

            nick.host = "{}!{}@{}".format(nickname, username, host)
            nick.realname = realname

            if account != "0":
                nick.account = account
            else:
                nick.account = None
                self.unauthed.add(nick)

    def checkunauthed(self):
        # see if efficient checks can be done using channels
        for channel in self.id.channels():
            if len(self.unauthed) < MAXTARGETS:
                break

            common = self.unauthed.intersection(channel.getnicks())
            if len(common) >= MAXTARGETS:
                self.unauthed.difference_update(common)
                self.who(channel)

        # WHO the remaining nicks in chunks
        unauthed = list(self.unauthed)
        for i in range(0, len(unauthed), MAXTARGETS):
            nicks = unauthed[i:i + MAXTARGETS]
            self.unauthed.difference_update(nicks)
            self.who(",".join([n.name for n in nicks]))

    def who(self, targets):
        self.whos.add(str(self.whoid))
        # returns (user name, host, nick, account name, real name)
        self.cmd.who("{},{}".format(targets, self.whoid), "n%tuhnar,{}".format(self.whoid))
        self.whoid = (self.whoid + 1) % 1000
