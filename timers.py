import datetime
import logging


class TimerSet(object):
    def __init__(self):
        self.timers = []

    def process(self):
        # process timers that have expired and return the timeout based on the first non-expired timer
        now = datetime.datetime.now()

        for i in range(len(self.timers)):
            if self.timers[i].isafter(now):
                return self.timers[i].secsremaining()

            logging.debug("Executing timer {!r} ".format(self.timers[i].getname()))
            self.timers[i].docommand()
            name, delay, reps, command = self.timers.pop(i).getdata()

            if reps > 0:
                reps -= 1

            # re-add timer if required
            # note: delay is only re-applied after command has been executed and timer is re-added
            if reps != 0:
                logging.debug("Re-adding timer {!r} with {} repetitions.".format(name, reps))
                self.addtimer(name, delay, reps, command)

        # no timers left, so no timeout required
        return None

    def addtimer(self, name, delay, reps, command):
        logging.debug("Adding timer {!r} with {} seconds delay and {} repetitions.".format(name, delay, reps))
        time = datetime.datetime.now() + datetime.timedelta(seconds=delay)

        # insert timer such that timers are sorted by datetime, ascending
        inserted = False
        for i in range(len(self.timers)):
            if self.timers[i].isafter(time):
                self.timers.insert(i, Timer(name, time, delay, reps, command))
                inserted = True
                break

        if not inserted:
            self.timers.append(Timer(name, time, delay, reps, command))

    def deltimer(self, name):
        logging.debug("Deleting timer {!r}.".format(name))
        for i in range(len(self.timers)):
            if self.timers[i].isnamed(name):
                self.timers.pop(i)
                return

        logging.warning("Timer {!r} not found.".format(name))


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
