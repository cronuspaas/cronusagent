
import unittest
import logging
LOG = logging.getLogger(__name__)

from agent.lib.agent_thread.agent_thread import AgentThread
from agent.lib.agent_thread.threadmgr import ThreadMgr
import time
import pylons
from agent.lib.agent_globals import stopAgentGlobals

class TestThreadManager(unittest.TestCase):

    def setUp(self):
        stopAgentGlobals()
        self.threadMgr = ThreadMgr(garbageFreq = pylons.config['threadMgr_garbage_freq'],
                                   maxThreadAge = pylons.config['threadMgr_thread_age'])

    def tearDown(self):
        self.threadMgr.stop()

    def testMgr(self):
        testTh = TestThread(self.threadMgr, ['service/test'])
        testTh.start()

        # for the thread to register itself
        tm = time.time()
        while (len(self.threadMgr.getUuids()) == 0 and tm + 10 > time.time()):
            pass
        assert len(self.threadMgr.getUuids()) == 1

        thread = self.threadMgr.getThreadByUuid('foobar')
        assert thread == None

        # test getting uuid
        uuid = testTh.getUuid()
        thread = self.threadMgr.getThreadByUuid(uuid)
        print self.threadMgr.getUuids()
        assert thread != None
        assert thread.getUuid() == testTh.getUuid()

        # test getting by cat
        testTh2 = TestThread(self.threadMgr, ['service/test2'])
        testTh2.start()

        tm = time.time()
        while (testTh2.isAlive() and tm + 1 > time.time()):
            pass

        testTh3 = TestThread(self.threadMgr, ['service/test2'])
        testTh3.start()

        # wait for the thread to register itself
        tm = time.time()
        while (len(self.threadMgr.getUuids()) != 3 and tm + 10 > time.time()):
            pass

        threadList = self.threadMgr.getThreadByCat('service/test', False, False)
        self.assertEqual(len(threadList), 1)
        self.assertEqual(threadList[0].getUuid(), testTh.getUuid())

        threadList = self.threadMgr.getThreadByCat('service/test2', False, False)
        assert len(threadList) == 2
        assert threadList[0].getUuid() == testTh2.getUuid() or threadList[0].getUuid() == testTh3.getUuid()
        assert threadList[1].getUuid() == testTh2.getUuid() or threadList[1].getUuid() == testTh3.getUuid()
        assert threadList[0].getUuid() != threadList[1].getUuid()

    def testMultipleCatMutualExclusion(self):
        LOG.debug('*************** Multiple Cat Test ')

        testTh1 = WaitThread(self.threadMgr, 'cat/test')
        testTh2 = WaitThread(self.threadMgr, 'cat/test')
        testTh1.start()

        tm = time.time()
        while (len(self.threadMgr.getUuids()) != 1 and tm + 5 > time.time()):
            time.sleep(0.1)
        assert len(self.threadMgr.getUuids()) == 1

        testTh2.start()
        tm = time.time()
        while (testTh2.isAlive() == True and tm + 10 > time.time()):
            time.sleep(0.1)

        assert testTh2.isAlive() == False

        testTh1.stop()


    def testRejectResourceThread(self):
        LOG.debug('*************** Reject resource thread Test ')

        testTh1 = ResourceThread(self.threadMgr, 'name/test')
        testTh2 = ResourceThread(self.threadMgr, 'name/test1')
        testTh3 = ResourceThread(self.threadMgr, 'name/test')

        testTh1.start()
        tm = time.time()
        while (len(self.threadMgr.getUuids()) != 1 and tm + 5 > time.time()):
            time.sleep(0.1)
        assert len(self.threadMgr.getUuids()) == 1

        testTh2.start()
        tm = time.time()
        while (len(self.threadMgr.getUuids()) != 2 and tm + 5 > time.time()):
            time.sleep(0.1)
        assert len(self.threadMgr.getUuids()) == 2


        testTh3.start()
        tm = time.time()
        while (testTh3.isAlive() == True and tm + 5 > time.time()):
            time.sleep(0.1)

        assert testTh3.isAlive() == False

        testTh1.stop()
        testTh2.stop()





    def testGarbageCollection(self):

        LOG.debug('*************** GC tests')

        self.threadMgr.stop()
        self.threadMgr = ThreadMgr(garbageFreq = 0.1, maxThreadAge = 0.5)
        self.threadMgr.start()

        testTh1 = WaitThread(self.threadMgr)
        testTh2 = WaitThread(self.threadMgr)
        testTh3 = WaitThread(self.threadMgr)
        testTh1.start()
        testTh2.start()
        testTh3.start()

        tm = time.time()
        while (len(self.threadMgr.getUuids()) != 3 and tm + 10 > time.time()):
            pass
        self.assertEqual(len(self.threadMgr.getUuids()), 3)

        t = testTh1.stop()
        LOG.info('should stop %s' % testTh1.getUuid())
        tm = time.time()
        while (len(self.threadMgr.getUuids()) != 2 and tm + 10 > time.time()):
            pass
        self.assertEqual(len(self.threadMgr.getUuids()), 2)

        t = testTh2.stop()
        tm = time.time()
        while (len(self.threadMgr.getUuids()) != 1 and tm + 10 > time.time()):
            pass
        self.assertEqual(len(self.threadMgr.getUuids()), 1)

        t = testTh3.stop()
        tm = time.time()
        while (len(self.threadMgr.getUuids()) != 0 and tm + 10 > time.time()):
            pass
        self.assertEqual(len(self.threadMgr.getUuids()), 0)

        self.threadMgr.stop()

class TestThread(AgentThread):
    def __init__(self, threadMgr, cat = ['service/test']):
        AgentThread.__init__(self, threadMgr, cat = cat)

    def doRun(self):
        pass

class WaitThread(AgentThread):
    def __init__(self, threadMgr, cat = None):
        AgentThread.__init__(self, threadMgr, cat)

    def doRun(self):
        while (True):
            self._checkStop()
            time.sleep(0.1)

class ResourceThread(WaitThread):
    MAX_INSTANCE = 2

    def __init__(self, threadMgr, name):
        WaitThread.__init__(self, threadMgr, name)
        self.setName(name)

