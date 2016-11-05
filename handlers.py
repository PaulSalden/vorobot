import re

def onconnect(handler):
    def wrapped(self, prefix, command, args):
        return handler(self)

    wrapped.ishandler = True
    wrapped.command = "001"

    return wrapped

def ontext(matchtext, target):
    def wrap(handler):
        def wrapped(self, prefix, command, args):
            if re.match(target, args[0]) and re.match(matchtext, args[1]):
                newargs = (self, prefix, args[0], args[1])
                return handler(*newargs)

        wrapped.ishandler = True
        wrapped.command = "PRIVMSG"
        return wrapped

    return wrap