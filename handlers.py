import re
import strings


def onconnect(handler):
    def wrapped(self, userdata, prefix, command, args):
        return handler(self)

    wrapped.ishandler = True
    wrapped.command = "001"

    return wrapped

def ontext(textmatch, targetmatch):
    def wrap(handler):
        def wrapped(self, userdata, prefix, command, args):
            if re.match(targetmatch, args[0]) and re.match(textmatch, args[1]):
                nick = userdata.getnick(strings.getnick(prefix), prefix)

                if strings.ischannel(args[0]):
                    target = userdata.getchannel(args[0])
                else:
                    target = userdata.getnick(args[0])

                # (self, nick, target, msg)
                newargs = (self, nick, target, args[1])
                return handler(*newargs)

        wrapped.ishandler = True
        wrapped.command = "PRIVMSG"
        return wrapped

    return wrap
