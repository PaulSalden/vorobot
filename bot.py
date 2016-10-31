import logging
import select
import socket
from config import settings as defaultsettings
from errno import WSAEWOULDBLOCK#EINPROGRESS
from strings import encode, decode

# flood control setting
RECEIVE_QUEUE_SIZE = 1024

class Bot(object):
    def __init__(self, settings):
        self.settings = settings

        self.s = None

        self.buffer_in = b""
        self.buffer_out = b""
        self.send_queue = []

        self.allow_send = True
        self.bytes_buffered = 0

    def process_timers(self):
        # temp
        return None

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

        # deal with response to anti-flood check
        if len(args) == 3 and (command, args[1]) == ("421", "SPLIDGEPLOIT"):
            self.bytes_buffered = 0
            self.allow_send = True
            return

        # respond to ping
        if command == "PING":
            self.send("PONG :{}".format(args[0]))

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
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setblocking(0)

        try:
            self.s.connect((self.settings['server'], int(self.settings['port'])))

        except socket.error as e:
            message = e.args[0]
            if message != WSAEWOULDBLOCK:
                logging.critical("Could not make connection: {}".format(message))
                return

        self.send("USER {} * * :{}".format(self.settings['username'], self.settings['realname']))
        self.send("NICK {}".format(self.settings['desired_nick']))

    def loop(self):
        inputtest = [self.s]
        excepttest = inputtest

        # the main loop
        while True:
            outputtest = [self.s] if self.send_queue else []
            timeout = self.process_timers()

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
    bot.connect()
    bot.loop()


if __name__ == "__main__":
    runbot(defaultsettings)
