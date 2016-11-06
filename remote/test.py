import handlers
import remotes

class MyRemote(remotes.Remote):
    @handlers.onconnect
    def connecthandler(self):
        self.cmd.join("#pwnagedeluxe")

    @handlers.ontext(":test", "#")
    def texthandler(self, nick, target, msg):
        modestring = "".join(nick.chanmodes(target))
        self.cmd.msg(target, "hi, your channel modes are: +{}".format(modestring))
