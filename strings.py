import re
import logging


# text decoding / encoding

def decode(line):
    # try utf-8
    try:
        return line.decode("utf-8", "strict")
    except UnicodeDecodeError:
        # try iso-8859-1
        try:
            return line.decode("iso-8859-1", "strict")
        except UnicodeDecodeError:
            logging.warning("Could not decode line.")
            return None


def encode(line):
    # encode in utf-8
    return line.encode("utf-8")


# hostmask conversion

def getnick(prefix):
    return prefix.split("!")[0]


# sting recognition

def isaction(msg):
    return re.match("^\\001ACTION.*\\001$", msg)


def isctcp(msg):
    return re.match("^\\001.*\\001$", msg)


def ischannel(name):
    channelprefixes = "#&"
    return name[0] in channelprefixes


# mode parsing

def parsechannelmodes(modestring, args=None):
    argmodes = "abhkloqv"
    signs = {"+": "add", "-": "remove"}

    # avoid a mutable default argument
    if not args:
        args = []

    sign = ""
    modechanges = {"add": {}, "remove": {}}
    for c in modestring:
        if c in signs:
            sign = signs[c]
        elif c in argmodes and not (sign == "remove" and c == "l"):
            modechanges[sign][c] = args.pop(0)
        else:
            modechanges[sign][c] = ""

    return modechanges


def parseusermodes(modestring):
    signs = {"+": "add", "-": "remove"}

    sign = ""
    modechanges = {"add": set(), "remove": set()}
    for c in modestring:
        if c in signs:
            sign = signs[c]
        else:
            modechanges[sign].add(c)

    return modechanges
