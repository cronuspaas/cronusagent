from agent.tests import *
import pylons
import os
import shutil
import logging
import json
import time
from Queue import Queue

from agent.lib.agent_thread.agent_thread import AgentThread
from agent.lib.agent_thread.threadmgr import ThreadMgr
from agent.lib.agent_globals import stopAgentGlobals
from agent.lib.agent_globals import startAgentGlobals

LOG = logging.getLogger(__name__)

class TestStatusController(TestController):

    def setUp(self):
        stopAgentGlobals()
        startAgentGlobals()

    def tearDown(self):
        stopAgentGlobals()

    def testDone(self):
        LOG.debug('********* testing: ' + url(controller = 'status', action = 'done'))
        response = self.app.get(url(controller = 'status', action = 'done'))

        # test the response object
        assert response.status_int == 200, 'HTTP response'
        LOG.debug('response body = ' + response.body)
        res = json.loads(response.body)
        assert res['progress'] == 100, 'response body progress'
        assert res['status'] == '/status/done', 'reponse body status'

    def testGet(self):
        # setup the status

        LOG.debug('*** Test getting status for a non-existent thread')
        response = self.app.get(url(controller = 'status', action = 'get', uuid = 'foobar'), expect_errors = True)
        LOG.debug('Failed status get response http_status = ' + str(response.status_int))
        assert response.status_int == 500, 'HTTP response - 500'


        LOG.debug('*** Test getting status for increasing progress')
        appGlobal = pylons.config['pylons.app_globals']
        progress_queue = Queue()

        LOG.debug('got thread mgr ' + str(appGlobal.threadMgr))

        testTh = TestThread(appGlobal.threadMgr, progress_queue)
        testTh.start()
        LOG.debug('Test Thread uuid = %s' % testTh.getUuid())

        for x in range(10, 101, 10):
            LOG.debug('Testing progress x = %d' % x)

            progress_queue.put(x)
            progress = -1
            tm = time.time()
            while (progress != x and tm + 5 > time.time()):
                response = self.app.get(url(controller = 'status', action = 'get', uuid = testTh.getUuid()), expect_errors = True)
                if (response.status_int != 200):
                    continue
                LOG.debug('respsonse body ' + response.body)
                res = json.loads(response.body)
                progress = int(res['progress'])
                LOG.debug('wanted progress %d, got progress %d' % (x, progress))

            assert progress == x, 'Never got progress to match internal(%d), response(%d)' % (x, progress)


class TestThread(AgentThread):

    def __init__(self, threadMgr, progress_queue):
        AgentThread.__init__(self, threadMgr, cat = ['Service/test_status'])
        self.progress_queue = progress_queue

    def doRun(self):
        progress = 0
        while (progress != 100):
            progress = self.progress_queue.get(block = True)
            self._updateStatus(progress = progress)
            LOG.debug('Got new progress = ' + str(progress))





