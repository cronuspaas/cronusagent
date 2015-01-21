from agent.lib.agent_globals import startAgentGlobals, stopAgentGlobals
from agent.lib.agent_thread.exec_thread import ExecThread
from agent.lib.errors import Errors
from agent.tests import *
import json
import logging
import os
import pylons
import re
import signal
import time
from agent.lib import utils


LOG = logging.getLogger(__name__)


class TestActionController(TestController):

    def setUp(self):
        stopAgentGlobals()
        startAgentGlobals()
        self.threadMgr = pylons.config['pylons.app_globals'].threadMgr

        path = os.path.realpath(__file__)
        self.scriptDir = os.path.join(os.path.dirname(path), 'scripts')

    def tearDown(self):
        stopAgentGlobals()

    def printStatus(self, status):
        print 'httpstatus = %s' % status['httpStatus']
        print 'result = %s' % status['result']
        print 'error = %s' % str(status['error'])
        print 'errorMsg = %s' % status['errorMsg']
        print 'progress = %d' % status['progress']

    def _test_progress(self):
        cmd = os.path.join(self.scriptDir, 'test.sh')
        LOG.debug('cmd = %s' % cmd)

        testExec = ExecThread(self.threadMgr, cmd)
        testExec.setTimeout(30)
        testExec.setProgressTimeout(10)

        testExec.start()

        # make sure the script is running
        tm = time.time()
        while (testExec.getCmdPid() == None and tm + 10 > time.time()):
            time.sleep(0.1)

        assert testExec.getCmdPid() != None
        print '****** cmd pid = %d' % testExec.getCmdPid()

        progress = 10
        # check that we increment the progress to 100
        tm = time.time()
        while (progress < 101 and tm + 5 > time.time()):
            LOG.debug('progress == %s: %s' % (str(testExec.getStatus()['progress']), str(progress)))
            if (int(testExec.getStatus()['progress']) == int(progress)):
                LOG.debug('sending sigint')
                try:
                    #The script itself traps the signal in increments its progress.
                    os.kill(testExec.getCmdPid(), signal.SIGINT)
                except OSError:
                    pass

                progress += 10
            time.sleep(0.05)

        self.printStatus(testExec.getStatus())
        assert int(testExec.getStatus()['progress']) == 100
            
    def test_process_exec_response(self):
        exeThread = ExecThread(None, 'dummy')
        exeThread.setTimeout(0)
        msg_header = '[AGENT_MESSAGE]{"errorMsg": "' 
        msg_line1 = 'line 1'
        msg_line2 = 'line 2'
        msg_line3 = 'line 3'
        msg_footer = '"}'
        exeThread.processExecResponse(msg_header)
        exeThread.processExecResponse(msg_line1)
        exeThread.processExecResponse(msg_line2)
        exeThread.processExecResponse(msg_line3)
        exeThread.processExecResponse(msg_footer)

    def test_nonending_script(self):
        cmd = os.path.join(self.scriptDir, 'test.sh')
        LOG.debug('cmd = %s' % cmd)

        testExec = ExecThread(self.threadMgr, cmd)
        testExec.setTimeout(1)
        testExec.setProgressTimeout(10)
        testExec.start()

        # make sure the script is running
        tm = time.time()
        while (testExec.getCmdPid() == None and tm + 15 > time.time()):
            pass
        assert testExec.getCmdPid() != None

        tm = time.time()
        while (int(testExec.getStatus()['httpStatus']) != 500 and tm + 20 > time.time()):
            pass

        self.printStatus(testExec.getStatus())

        assert int(testExec.getStatus()['httpStatus']) == 500
        assert testExec.getStatus()['error'] == Errors.AGENT_THREAD_TIMEDOUT

    def test_random_script(self):
        cmd = ['ls', '/tmp']
        LOG.debug('cmd = %s' % cmd)

        testExec = ExecThread(self.threadMgr, cmd)
        testExec.setTimeout(10)
        testExec.setProgressTimeout(10)
        testExec.start()

        tm = time.time()
        while (int(testExec.getStatus()['progress']) != 100 and tm + 20 > time.time()):
            pass

        self.printStatus(testExec.getStatus())

        assert int(testExec.getStatus()['httpStatus']) == 200
        assert testExec.getStatus()['result'] == None
        assert testExec.getStatus()['error'] == None
        assert testExec.getStatus()['errorMsg'] == None

#    def test_bad_script(self):
#        cmd = ['ls', '-z']
#        LOG.debug('cmd = %s' % cmd)
#
#       testExec = ExecThread(self.threadMgr, cmd, 10, 10)
#        testExec.start()
#
#        tm = time.time()
#        while (int(testExec.getStatus()['progress']) != 100 and tm + 20 > time.time()):
#            pass
#
#        self.printStatus(testExec.getStatus())
#
#        assert testExec.getStatus()['httpStatus'] == 500
#        assert testExec.getStatus()['result'] == None
#        assert testExec.getStatus()['error'] >= Errors.CLIENT_SCRIPT_ERROR
#        result = re.search("ExecThreads \(\[.*'ls', '-z'\]\) err with code\(", testExec.getStatus()['errorMsg'])
#
#        assert result != None
        #assert testExec.getStatus()['errorMsg'].startswith("Exec Threads (['ls', '-z']) error code(")

#    def test_bad_code_no_msg_script(self):
#        cmd = [os.path.join(self.scriptDir, 'test2.sh'), 'bad_code_no_msg']
#        LOG.debug('cmd = %s' % cmd)
#
#        testExec = ExecThread(self.threadMgr, cmd, 10, 10)
#        testExec.start()

#        tm = time.time()
#        while (int(testExec.getStatus()['progress']) != 100 and tm + 20 > time.time()):
#            pass

#        self.printStatus(testExec.getStatus())

#        assert int(testExec.getStatus()['httpStatus']) == 500
#        assert testExec.getStatus()['result'] == None
#        assert testExec.getStatus()['error'] >= Errors.CLIENT_SCRIPT_ERROR
#        result = re.search("ExecThreads \(\['.*scripts[\\\/]*test2.sh', 'bad_code_no_msg'\]\) error with code\(255\)",
#                           testExec.getStatus()['errorMsg'])
#        assert result != None

    def test_good_code_no_msg_script(self):
        cmd = [os.path.join(self.scriptDir, 'test2.sh'), 'good_code_no_msg']
        LOG.debug('cmd = %s' % cmd)

        testExec = ExecThread(self.threadMgr, cmd)
        testExec.setTimeout(10)
        testExec.setProgressTimeout(10)
        testExec.start()

        tm = time.time()
        while (int(testExec.getStatus()['progress']) != 100 and tm + 20 > time.time()):
            pass

        self.printStatus(testExec.getStatus())

        assert int(testExec.getStatus()['httpStatus']) == 200
        assert testExec.getStatus()['result'] == None
        assert testExec.getStatus()['error'] == None
        assert testExec.getStatus()['errorMsg'] == None

#    def test_bad_code_bad_msg_script(self):
#        cmd = [os.path.join(self.scriptDir, 'test2.sh'), 'bad_code_bad_msg']
#        LOG.debug('cmd = %s' % cmd)

#        testExec = ExecThread(self.threadMgr, cmd, 10, 10)
#        testExec.start()

#        tm = time.time()
#        while (int(testExec.getStatus()['progress']) != 100 and tm + 20 > time.time()):
#            pass

#        self.printStatus(testExec.getStatus())

#        assert int(testExec.getStatus()['httpStatus']) == 500
#        assert testExec.getStatus()['result'] == None

#        assert int(testExec.getStatus()['error']) == 10243
#        result = re.search("User script error \(\['sh', '*scripts[\\\/]*test2.sh', 'bad_code_bad_msg'\]\) error with code\(243\)\ error mesg",
#                           testExec.getStatus()['errorMsg'])
#        assert result != None


#    def test_bad_code_invalid_msg_script(self):
#        cmd = [os.path.join(self.scriptDir, 'test2.sh'), 'bad_code_invalid_msg']
#        LOG.debug('cmd = %s' % cmd)

#        testExec = ExecThread(self.threadMgr, cmd, 10, 10)
#        testExec.start()

#        tm = time.time()
#        while (int(testExec.getStatus()['progress']) != 100 and tm + 20 > time.time()):
#            pass

#        self.printStatus(testExec.getStatus())

#        assert int(testExec.getStatus()['httpStatus']) == 500
#        assert testExec.getStatus()['result'] == None
#        assert int(testExec.getStatus()['error']) == (Errors.CLIENT_SCRIPT_ERROR + 255)

#        result = re.search("User script error \(\['.*scripts[\\\/]*test2.sh', 'bad_code_invalid_msg'\]\) error with code\(255\)",
#                           testExec.getStatus()['errorMsg'])
#        assert result != None

    def test_good_code_invalid_msg_script(self):
        cmd = [os.path.join(self.scriptDir, 'test2.sh'), 'good_code_invalid_msg']
        LOG.debug('cmd = %s' % cmd)

        testExec = ExecThread(self.threadMgr, cmd)
        testExec.setTimeout(10)
        testExec.setProgressTimeout(10)
        testExec.start()

        tm = time.time()
        while (int(testExec.getStatus()['progress']) != 100 and tm + 20 > time.time()):
            pass

        self.printStatus(testExec.getStatus())

        assert int(testExec.getStatus()['httpStatus']) == 200
        assert testExec.getStatus()['result'] == None
        assert testExec.getStatus()['error'] == None
        assert testExec.getStatus()['errorMsg'] == None




