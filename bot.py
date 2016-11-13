import asyncio
import logging
import socket
import remotes
from config.bot import settings as defaultsettings
from errno import WSAEWOULDBLOCK  # EINPROGRESS
from strings import encode, decode

# flood control setting
RECEIVE_QUEUE_SIZE = 1024


class Bot(object):
    def __init__(self, loop, settings):
        self.settings = settings
        self.remoteset = remotes.RemoteSet(self.send)

        self.loop = loop
        self.reader = None
        self.writer = None

        self.readbuffer = b""
        self.send_queue = []

        self.allow_send = True
        self.bytes_buffered = 0

        self.connect_success = False

    # --- make and maintain connection ---

    async def connect(self):
        # make sure queues, buffers, etc. are reset
        self.readbuffer = b""
        self.buffer_out = b""
        self.send_queue = []

        self.allow_send = True
        self.bytes_buffered = 0

        self.connect_success = False

        try:
            self.reader, self.writer = await asyncio.open_connection(self.settings['server'],
                                                                     int(self.settings['port']),
                                                                     loop=self.loop)

        except socket.error as e:
            message = e.args[0]
            if message != WSAEWOULDBLOCK:
                logging.warning("Could not make connection: {}".format(message))
                return False

        self.send("USER {} * * :{}".format(self.settings['username'], self.settings['realname']))
        self.send("NICK {}".format(self.settings['desired_nick']))

        return True

    async def mainloop(self):
        failed = 0
        # keep on trying to connect
        while True:
            # try to connect and loop while connected
            if await self.connect():
                while True:
                    connected = await self.do_receive()

                    if not connected:
                        logging.warning("Disconnected.")
                        self.writer.close()
                        break

                    await self.do_send()

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
                await asyncio.sleep(delay)

    # --- receive and send data ---

    async def do_receive(self):
        data = await self.reader.read(8192)

        if not data:
            # assume disconnect
            return False

        self.readbuffer += data
        encoded_lines = self.readbuffer.split(b"\r\n")
        # leave incomplete lines in buffer
        self.readbuffer = encoded_lines.pop(-1)

        for encoded_line in encoded_lines:
            line = decode(encoded_line)
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

        return True

    async def do_send(self):
        buffer_out = b""
        while self.send_queue and self.allow_send:
            line = self.send_queue.pop(0)
            encoded_line = encode("{}\r\n".format(line))
            encoded_line_len = len(encoded_line)

            # wait for my commands to be processed after I have sent a critical amount of bytes
            # note: I do not control the amount of bytes the server separately queues up to send me
            if self.bytes_buffered + encoded_line_len > RECEIVE_QUEUE_SIZE:
                self.allow_send = False
                logging.info("-> SPLIDGEPLOIT")
                buffer_out += encode("SPLIDGEPLOIT\r\n")

            else:
                logging.info("-> {}".format(line))
                buffer_out += encoded_line
                self.bytes_buffered += encoded_line_len

        self.writer.write(buffer_out)
        await self.writer.drain()

    # --- further interaction ---

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
            self.send("NICK {}`".format(args[1]))
            return

    def send(self, line):
        self.send_queue.append(line)

    def loadmodules(self):
        for m in self.settings["modules"]:
            self.remoteset.loadremote(m)


def runbot(settings):
    loop = asyncio.get_event_loop()

    bot = Bot(loop, settings)
    bot.loadmodules()

    loop.run_until_complete(bot.mainloop())
    loop.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    runbot(defaultsettings)
