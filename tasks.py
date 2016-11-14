import asyncio
import logging


class TaskSet(object):
    def __init__(self, loop):
        self.loop = loop
        self.timers = {}

    def addtimer(self, name, delay, reps, command):
        message = "Adding timer {!r} with {} seconds delay and {} repetitions."
        logging.debug(message.format(name, delay, reps))

        async def timerprocess():
            # treat unlimited reps as a negative number
            i = reps if reps != 0 else -1
            while i != 0:
                await asyncio.sleep(delay)

                logging.debug("Executing timer {!r} ".format(name))
                try:
                    command()
                except Exception as e:
                    logging.warning("Failed to execute timer {!r}: {}".format(name, e))

                if i > 0:
                    i -= 1

            if name in self.timers:
                del self.timers[name]

        self.timers[name] = asyncio.ensure_future(timerprocess(), loop=self.loop)

    def removetimer(self, name):
        if name not in self.timers:
            logging.warning("Timer {!r} not found.".format(name))
            return

        logging.debug("Deleting timer {!r}.".format(name))
        timer = self.timers.pop(name)
        timer.cancel()

    def dobgprocess(self, command):
        message = "Executing background process."
        logging.debug(message)

        async def bgprocess():
            try:
                command()
            except Exception as e:
                logging.warning("Failed to execute background process: {}".format(e))

        self.loop.run_in_executor(None, bgprocess())
