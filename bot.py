import logging
import select
import socket
import time
import remotes
from config.bot import settings as defaultsettings
from errno import WSAEWOULDBLOCK  # EINPROGRESS
from strings import encode, decode

# flood control setting
RECEIVE_QUEUE_SIZE = 1024


class Bot(object):
    def __init__(self, settings):
        self.settings = settings
        self.remoteset = remotes.RemoteSet(self.send)

        self.s = None

        self.buffer_in = b""
        self.buffer_out = b""
        self.send_queue = []

        self.allow_send = True
        self.bytes_buffered = 0

        self.connect_success = False

    def process_timers(self):
        return self.remoteset.processtimers()

    def split_received(self, data):
        self.buffer_in += data
        encoded_lines = self.buffer_in.split(b"\r\n")
        # leave incomplete lines in buffer
        self.buffer_in = encoded_lines.pop(-1)

        for encoded_line in encoded_lines:
            line = decode(encoded_line)
            self.handle_line(line)

    def handle_line(self, line):
        logging.info("<- {}".format(line))

        # split up line in prefix, command, args
        prefix = ''
        trailing = []

        if line[0] == ':':
            prefix, line = line[1:].split(' ', 1)

        if line.find(' :') != -1:
            line, trailing = line.split(' :', 1)
            args = line.split()
            args.append(trailing)

        else:
            args = line.split()

        command = args.pop(0)

        self.basic_responses(command, args)
        self.remoteset.process(prefix, command, args)

    def basic_responses(self, command, args):
        # deal with response to anti-flood check
        if len(args) == 3 and (command, args[1]) == ("421", "SPLIDGEPLOIT"):
            self.bytes_buffered = 0
            self.allow_send = True
            return

        # respond to ping
        if command == "PING":
            self.send("PONG :{}".format(args[0]))
            return

        # make sure initial nickname is obtained
        if self.connect_success:
            return

        if command == "001":
            self.connect_success = True
            return

        if command == "433":
            self.send("NICK {}".format(args[1] + "`"))
            return

    def send_lines(self):
        while self.send_queue and self.allow_send:
            encoded_line = encode("%s\r\n" % self.send_queue[0])

            # wait for my commands to be processed after I have sent a critical amount of bytes
            # note: I do not control the amount of bytes the server separately queues up to send me
            if self.bytes_buffered + len(encoded_line) > RECEIVE_QUEUE_SIZE:
                self.allow_send = False
                logging.info("-> SPLIDGEPLOIT")
                self.buffer_out += encode("SPLIDGEPLOIT\r\n")

            else:
                logging.info("-> {}".format(self.send_queue.pop(0)))
                self.buffer_out += encoded_line
                self.bytes_buffered += len(encoded_line)

        # send as much of buffer as possible
        sent = self.s.send(self.buffer_out)
        self.buffer_out = self.buffer_out[sent:]

    def send(self, line):
        self.send_queue.append(line)

    def connect(self):
        # make sure queues, buffers, etc. are reset
        self.buffer_in = b""
        self.buffer_out = b""
        self.send_queue = []

        self.allow_send = True
        self.bytes_buffered = 0

        # create socket
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setblocking(0)

        self.connect_success = False

        try:
            self.s.connect((self.settings['server'], int(self.settings['port'])))

        except socket.error as e:
            message = e.args[0]
            if message != WSAEWOULDBLOCK:
                logging.critical("Could not make connection: {}".format(message))
                return False

        self.send("USER {} * * :{}".format(self.settings['username'], self.settings['realname']))
        self.send("NICK {}".format(self.settings['desired_nick']))

        return True

    def loadmodules(self):
        for m in self.settings["modules"]:
            self.remoteset.loadremote(m)

    def connectloop(self):
        failed = 0
        # keep on trying to connect
        while True:
            # try to connect and loop while connected
            if self.connect():
                self.mainloop()

            # send _DISCONNECT pseudo-command for all loaded modules
            self.remoteset.process("", "_DISCONNECT", "")

            # exponentially delay reconnect if previous attempt(s) was/were unsuccessful
            if self.connect_success:
                failed = 0
                logging.info("Reconnecting.")

            else:
                failed += 1
                delay = 10**failed
                logging.info("Reconnecting in {} seconds.".format(delay))
                time.sleep(delay)

    def mainloop(self):
        inputtest = [self.s]
        excepttest = inputtest

        while True:
            # start with processing timers, so potential new commands can be sent
            timeout = self.process_timers()
            outputtest = [self.s] if self.send_queue else []

            inputready, outputready, exceptready = select.select(inputtest, outputtest, excepttest, timeout)

            if exceptready:
                # assume fatal error
                logging.critical("Fatal error returned by select().")
                self.s.close()
                break

            if inputready:
                received = self.s.recv(8192)

                if not received:
                    # assume disconnect
                    logging.critical("Disconnected.")
                    self.s.close()
                    break

                self.split_received(received)

            if outputready:
                self.send_lines()


def runbot(settings):
    bot = Bot(settings)
    bot.loadmodules()
    bot.connectloop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    runbot(defaultsettings)
