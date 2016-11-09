class IdentifierSet(object):
    def __init__(self, userdata):
        self.userdata = userdata

    def nick(self, nickname, host=""):
        return self.userdata.getnick(nickname, host)

    def channel(self, channelname):
        return self.userdata.getchannel(channelname)

    def channels(self):
        return self.userdata.getchannels()

    def me(self):
        return self.userdata.getme()
