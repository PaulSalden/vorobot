import re
import strings
# properly split up messages and notices
#         if command == "PRIVMSG":
#             if isaction(args[0]):
#                 command = "ACTION"
#             elif isctcp(args[0]):
#                 command = "CTCP"
#
#         if command == "NOTICE":
#             if isctcp(args[0]):
#                 command = "CTCPREPLY"


def raw(numeric, argmatch):
    def wrap(handler):
        def wrapped(self, userdata, prefix, command, args):
            if command != numeric or not re.match(argmatch, " ".join(args)):
                return

            # (self, args1, args2, ...)
            return handler(*args)

        wrapped.ishandler = True
        wrapped.command = "RAW"
        return wrapped

    return wrap


def onconnect(handler):
    def wrapped(self, userdata, prefix, command, args):
        return handler(self)

    wrapped.ishandler = True
    wrapped.command = "001"

    return wrapped


def onjoin(channelmatch):
    def wrap(handler):
        def wrapped(self, userdata, prefix, command, args):
            if not re.match(channelmatch, args[0]):
                return

            nick = userdata.getnick(strings.getnick(prefix), prefix)

            # (self, nick, channel)
            newargs = (self, nick, args[0])
            return handler(*newargs)

        wrapped.ishandler = True
        wrapped.command = "JOIN"
        return wrapped

    return wrap


def ontext(textmatch, targetmatch):
    def wrap(handler):
        def wrapped(self, userdata, prefix, command, args):
            if strings.isctcp(args[1]):
                return

            if not (re.match(targetmatch, args[0]) and re.match(textmatch, args[1])):
                return

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
