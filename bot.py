import asyncio
import collections
import logging
import socket
import remotes
import tasks
from config.bot import settings as defaultsettings
from errno import WSAEWOULDBLOCK  # EINPROGRESS
from strings import encode, decode

# flood control setting
RECEIVE_QUEUE_SIZE = 1024


class Bot(object):
    def __init__(self, loop, settings):
        self.loop = loop

        self.settings = settings
        self.tasks = tasks.TaskSet(self.loop)
        self.remoteset = remotes.RemoteSet(self.send, self.tasks)

        self.reader = None
        self.writer = None
        self.read_buffer = b""
        self.send_queue = asyncio.Queue(loop=loop)
        self.send_buffer = collections.deque()

        self.allow_send = True
        self.bytes_buffered = 0

        self.connect_success = False

    # --- connection handling ---

    async def mainloop(self):
        failed = 0
        # keep on trying to connect
        while True:
            # try to connect and keep on receiving while connected
            if await self.connect():
                send_future = asyncio.ensure_future(self.sendloop(), loop=self.loop)
                while True:
                    connected = await self.receive_data()

                    if not connected:
                        logging.warning("Disconnected.")
                        send_future.cancel()
                        self.writer.close()

                        # send _DISCONNECT pseudo-command for all loaded modules
                        self.remoteset.process("", "_DISCONNECT", "")

            # exponentially delay reconnect if previous attempt(s) was/were unsuccessful
            if self.connect_success:
                failed = 0
                logging.info("Reconnecting.")

            else:
                failed += 1
                delay = 10 ** failed
                logging.info("Reconnecting in {} seconds.".format(delay))
                await asyncio.sleep(delay)

    async def connect(self):
        # make sure queues, buffers, etc. are reset
        self.reader = None
        self.writer = None
        self.read_buffer = b""
        self.send_queue = asyncio.Queue(loop=self.loop)

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

    async def sendloop(self):
        data = b""
        while True:
            data += await self.send_queue.get()

            if self.send_queue.empty():
                self.writer.write(data)
                await self.writer.drain()
                data = b""

    async def receive_data(self):
        data = await self.reader.read(8192)

        if not data:
            # assume disconnect
            return False

        self.read_buffer += data
        encoded_lines = self.read_buffer.split(b"\r\n")
        # leave incomplete lines in buffer
        self.read_buffer = encoded_lines.pop(-1)

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

    # --- interaction ---

    def basic_responses(self, command, args):
        # deal with response to anti-flood check
        if len(args) == 3 and (command, args[1]) == ("421", "SPLIDGEPLOIT"):
            self.bytes_buffered = 0
            self.allow_send = True

            while len(self.send_buffer) > 0:
                line = self.send_buffer.pop()
                encoded_line = encode("{}\r\n".format(line))
                encoded_line_len = len(encoded_line)

                if self.bytes_buffered + encoded_line_len <= RECEIVE_QUEUE_SIZE:
                    logging.info("-> {}".format(line))
                    self.send_queue.put_nowait(encoded_line)
                    self.bytes_buffered += encoded_line_len
                else:
                    self.send_buffer.append(line)
                    self.allow_send = False
                    logging.info("-> SPLIDGEPLOIT")
                    self.send_queue.put_nowait(encode("SPLIDGEPLOIT\r\n"))
                    break

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
        encoded_line = encode("{}\r\n".format(line))
        encoded_line_len = len(encoded_line)

        if self.allow_send:
            # wait for my commands to be processed after I have sent a critical amount of bytes
            # note: I do not control the amount of bytes the server separately queues up to send me
            if self.bytes_buffered + encoded_line_len <= RECEIVE_QUEUE_SIZE:
                logging.info("-> {}".format(line))
                self.send_queue.put_nowait(encoded_line)
                self.bytes_buffered += encoded_line_len
                return

            self.allow_send = False
            logging.info("-> SPLIDGEPLOIT")
            self.send_queue.put_nowait(encode("SPLIDGEPLOIT\r\n"))

        self.send_buffer.appendleft(line)

    # ----------

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
