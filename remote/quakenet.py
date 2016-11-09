import hashlib
import hmac
import random
import handlers
import remotes
from config.quakenet import settings


# based on https://www.quakenet.org/development/challengeauth
def challengeauth(lcusername, truncpassword, challenge, digest=hashlib.sha256):
    lcusername = lcusername.encode("utf-8")
    truncpassword = truncpassword.encode("utf-8")
    unamepw = lcusername + b":" + digest(truncpassword).hexdigest().encode("utf-8")
    challenge = challenge.encode("utf-8")
    return hmac.HMAC(digest(unamepw).hexdigest().encode("utf-8"), challenge, digestmod=digest).hexdigest()


# pause between auth attempts in seconds
AUTHDELAY = 5 * 60


class Connect(remotes.Remote):
    @handlers.onconnect
    def connecthandler(self):
        self.authwait = True
        self.cmd.timer("retryauth", AUTHDELAY, 0, self.retryauth)
        self.cmd.mode(self.id.me(), "+x")
        self.cmd.msg("q@cserve.quakenet.org", "CHALLENGE")

    def retryauth(self):
        self.cmd.msg("q@cserve.quakenet.org", "CHALLENGE")

    @handlers.onnotice("^CHALLENGE ", "")
    def noticehandler(self, nick, target, msg):
        if self.authwait and nick.equals("Q"):
            words = msg.split()
            if "HMAC-SHA-256" in words[2:]:
                username = settings["authname"]
                lcusername = self.id.irclower(username)
                truncpassword = settings["password"][:10]
                response = challengeauth(lcusername, truncpassword, words[1])

                command = "CHALLENGEAUTH {} {} HMAC-SHA-256"
                self.cmd.msg("q@cserve.quakenet.org", command.format(username, response))

    @handlers.raw("396", "")
    def hiddenhosthandler(self, *args):
        if self.authwait:
            self.authwait = False
            self.cmd.timerdel("retryauth")
            channels = settings["channels"]

            if channels:
                self.cmd.join(channels)

# --------------------------------------------------


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
        self.timer = False

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

        # start/stop timer as necessary
        if self.unauthed and not self.timer:
            self.timer = True
            self.cmd.timer("authwho", WHODELAY, 0, self.checkunauthed)
        elif not self.unauthed and self.timer:
            self.timer = False
            self.cmd.timerdel("authwho")

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
