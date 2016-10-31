import logging

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