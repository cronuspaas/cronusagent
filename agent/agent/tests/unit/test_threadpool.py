from unittest import TestCase
from agent.lib.thread_pool import ThreadPool
from random import randrange
from time import sleep

import logging
LOG = logging.getLogger(__name__)

class TestThreadPool(TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testThreadPool(self):
        delays = [randrange(1, 10) for i in range(100)]

        def wait_delay(d):
            print 'sleeping for (%.2f)sec' % d
            sleep(d)

        pool = ThreadPool(5)
        for i, d in enumerate(delays):
            print '%.2f%c' % ((float(i) / float(len(delays))) * 100.0, '%')
            pool.addTask(wait_delay, float(d) / 10)

        pool.waitCompletion()
