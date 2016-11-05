import handlers
import remotes

class MyRemote(remotes.Remote):
    @handlers.onconnect
    def connecthandler(self):
        self.cmd.join("#pwnagedeluxe")

    @handlers.ontext(":test", "")
    def texthandler(self, host, target, msg):
        self.cmd.msg(target, "hi!")