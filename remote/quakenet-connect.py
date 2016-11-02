import modules


class Remote(modules.Module):
    def onconnect(self, *args):
        self.cmd.join("#pwnagedeluxe")
