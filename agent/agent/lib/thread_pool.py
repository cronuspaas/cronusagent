#pylint: disable=W0142,W0105
'''
Org: http://code.activestate.com/recipes/577187-python-thread-pool/
'''

from Queue import Queue, Full
from threading import Thread
import time

import logging
LOG = logging.getLogger(__name__)


class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks):
        """ constructor """
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.lastStartedTime = 0
        self.lastRunTime = 0
        self.start()

    def run(self):
        """ real work function"""
        while True:
            func, args, kargs = self.tasks.get()
            try:
                self.lastStartedTime = time.time()
                func(*args, **kargs)
            except BaseException as excp:
                LOG.error('Exception in thread worker: %s' % excp)

            self.lastRunTime = time.time() - self.lastStartedTime
            self.lastStartedTime = 0
            self.tasks.task_done()

    def getRunningTime(self):
        """ get time(seconds) spent since the thread picked up the job"""
        if self.lastStartedTime:
            return time.time() - self.lastStartedTime
        elif self.lastStartedTime:
            return self.lastStartedTime
        else:
            return 0

class ThreadPool(object):
    """
    Nonblock Pool of threads consuming tasks from a queue
    """
    def __init__(self, numThreads):
        self.numThreads = numThreads
        self.workers = []

        self.tasks = Queue(numThreads)
        for _ in range(numThreads):
            self.workers.append(Worker(self.tasks))

    def addTask(self, func, *args, **kargs):
        """
        Add a task to the queue
        if Queue is full already when adding task, return false
        """
        try:
            self.tasks.put_nowait((func, args, kargs))
            return True
        except Full:
            LOG.error("Thread pool of size %s is full" % self.numThreads)
            return False

    def getWorkerRunningTime(self):
        """ get info for all threads """
        runningTime = []
        for _, worker in enumerate(self.workers):
            runningTime.append("%.2fms" % (1000 * worker.getRunningTime()))
        return runningTime

    def waitCompletion(self):
        """Wait for completion of all the tasks in the queue"""
        self.tasks.join()
