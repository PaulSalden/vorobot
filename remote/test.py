import handlers
import remotes


class MyRemote(remotes.Remote):
    @handlers.ontext(":test", "#")
    def texthandler(self, nick, target, msg):
        #modestring = "".join(nick.chanmodes(target))
        #self.cmd.msg(target, "hi, your channel modes are: +{}".format(modestring))
        self.cmd.msg(target, "hi, you're authed as {}".format(nick.account))
