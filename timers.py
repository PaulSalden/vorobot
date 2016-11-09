import datetime
import logging


class TimerSet(object):
    def __init__(self):
        self.timers = []

    def process(self):
        # process timers that have expired and return the timeout based on the first non-expired timer

        # account for adding timers during loop
        i = 0
        while i < len(self.timers):
            now = datetime.datetime.now()
            if self.timers[i].isafter(now):
                timeout = self.timers[i].secsremaining()
                return timeout if timeout > 0 else None

            logging.debug("Executing timer {!r} ".format(self.timers[i].getname()))
            timer = self.timers.pop(i)
            try:
                timer.docommand()
            except Exception as e:
                logging.warning("Failed to execute timer {!r}: {}".format(self.timers[i].getname(), e))
            name, delay, reps, command = timer.getdata()

            if reps > 0:
                reps -= 1

            # re-add timer if required
            # note: delay is only re-applied after command has been executed and timer is re-added
            if reps != 0:
                logging.debug("Re-adding timer {!r} with {} repetitions.".format(name, reps))
                inserti = self.add(name, delay, reps, command, True)

                # jump back if necessary
                if inserti <= i:
                    i = inserti
                    continue

            i += 1

        # no timers left, so no timeout required
        return None

    def add(self, name, delay, reps, command, returnpos=False):
        logging.debug("Adding timer {!r} with {} seconds delay and {} repetitions.".format(name, delay, reps))
        time = datetime.datetime.now() + datetime.timedelta(seconds=delay)

        # insert timer such that timers are sorted by datetime, ascending
        i = 0
        while i < len(self.timers):
            if self.timers[i].isafter(time):
                self.timers.insert(i, Timer(name, time, delay, reps, command))
                return i if returnpos else True

            i += 1

        self.timers.append(Timer(name, time, delay, reps, command))
        return len(self.timers) - 1 if returnpos else True

    def delete(self, name):
        logging.debug("Deleting timer {!r}.".format(name))
        i = 0
        while i < len(self.timers):
            if self.timers[i].isnamed(name):
                self.timers.pop(i)
                return True

            i += 1

        logging.warning("Timer {!r} not found.".format(name))
        return False


class Timer(object):
    def __init__(self, name, time, delay, reps, command):
        # keep delay to potentially re-add timer
        self.name = name
        self.delay = delay
        self.datetime = time
        # mIRC's value 0 for indefinite timers is inconvenient
        self.repeats = reps if reps != 0 else -1
        self.command = command

    def isafter(self, time):
        return time < self.datetime

    def isnamed(self, name):
        return self.name == name

    def secsremaining(self):
        delta = self.datetime - datetime.datetime.now()
        return delta.total_seconds()

    def getname(self):
        return self.name

    def docommand(self):
        self.command()

    def getdata(self):
        return self.name, self.delay, self.repeats, self.command
