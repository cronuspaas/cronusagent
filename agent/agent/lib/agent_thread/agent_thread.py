#pylint: disable=R0904,R0912,R0915,W0105,W0621
""" base agent thread """
import uuid
import threading
import thread
import time
from copy import deepcopy
import traceback

from agent.lib.errors import Errors, ConcurrentActivityException
from agent.lib.errors import AgentException

import logging
from agent.lib import contextutils, configutil
import json
import math

LOG = logging.getLogger(__name__)
UUIDLOG = logging.getLogger('uuid')
OUTPUTLOG = logging.getLogger('execoutput')

class AgentThread(threading.Thread):
    """ All threads used by the agent should be of type agent thread.
    This thread will be used to generate ids, provide categories for the thread mgr. """

    def __init__(self, threadMgr, cat = None, name = 'agent_thread', parentId = None):
        """ Constructor.
        Creates the uuid.
        Sets the category of this thread """
        threading.Thread.__init__(self)
        self.__lock = threading.Lock()
        self.__stop = False
        
        self._timeout = configutil.getConfigAsInt('agent_thread_timeout')
        self._progressTimeout = 0
        
        self.__lastProgress = None
        self.__timeoutAt = 0

        # thread event to mark when the thread has been added to threadMgr
        self.threadMgrEvent = threading.Event()
        self.threadMgrEvent.clear()

        # thread manager
#         from agent.lib.agent_thread import threadmgr
        self._threadMgr = threadMgr
        self._parentId = parentId

        # used by status
        self.__uuid = str(uuid.uuid4())
        self.__cat = cat if parentId is None else None
        self.__name = name
        self.__executionMsec = None
        
        self._mergeOnFound = False

        # status
        self.__status = {'httpStatus': 200, 
                         'progress': 0, 
                         'fprogress': 0.0, 
                         'result': None, 
                         'error': None, 
                         'errorMsg': None, 
                         'startTime': None,
                         'executionMsec': None,
                         'correlationId': None,
                         'requrl': None,
                         'type': self.__class__.__name__}
        
        # keep track of all child exec thread id
        self.__childExecThreadIds = []

    ##############################################################
    # Thread Running Methods
    ##############################################################

    def run(self):
        """ run - register self with threadmgr """

        # start timer
        self.__executionMsec = time.time() * 1000
        self.__status['startTime'] = time.strftime('%Y-%m-%d %X %Z')

        self.__status['correlationId'] = contextutils.getcontext(self, 'guid', None)
        self.__status['requrl'] = contextutils.getcontext(self, 'requrl', None)
        
        self.beforeRun()
        
        self.__timeoutAt += (time.time() + self._timeout)
        guid = contextutils.getcontext(self, 'guid', None)

        try:
            if not self._parentId and guid:
                OUTPUTLOG.info('%s guid start ' % guid)
            
            if self._threadMgr:    
                self._threadMgr.addThread(self)
                
            self.threadMgrEvent.set()
            self.doRun()
            
        except ConcurrentActivityException as excep:
            # found existing, and merge with it if needed
            conflictUuid = excep.getConflictUuid() 
            
            errorMsg = excep.getMsg()
            isMerged = False
            # merge with existing thread
            if self._threadMgr and self._mergeOnFound:
                conflictThread = self._threadMgr.getThreadByUuid(conflictUuid)
                if (conflictThread and isinstance(conflictThread, AgentThread)  
                        and conflictThread.getReqChecksum() == self.getReqChecksum()):
                    
                    errorMsg = 'Thread(%s / %s) merged with existing thread %s' % (self.__name, self.__uuid, excep.getConflictUuid())
                    self.__uuid = excep.getConflictUuid()
                    isMerged = True

            self._updateStatus(httpStatus = 500, progress = 100,
                               error = excep.getCode(), errorMsg = errorMsg)
            if not isMerged:
                LOG.error('Thread(%s / %s) Caught ThreadMgr Exception - exiting (%s) - %s' % (self.__name, self.__uuid, excep, traceback.format_exc(5)))
            thread.exit()
                
        except AgentException, excep:
            self._updateStatus(httpStatus = 500, progress = 100,
                              error = excep.getCode(), errorMsg = excep.getMsg())
            LOG.error('Thread(%s / %s) Caught ThreadMgr Exception - exiting (%s) - %s' % (self.__name, self.__uuid, excep, traceback.format_exc(5)))
            thread.exit()

        except Exception, excep:
            LOG.error('Thread(%s / %s) Caught ThreadMgr Exception - exiting (%s) - %s' % (self.__name, self.__uuid, excep, traceback.format_exc(5)))
            thread.exit()
        
        finally:
            # doesn't hurt set twice since this event is telling whether it's registered by threadMgr
            self.threadMgrEvent.set()
            # closing guid marker in execoutput.log
            if not self._parentId and guid:
                OUTPUTLOG.info('%s guid end' % guid)
            # calculate execution time
            executionMsec = time.time() * 1000 - self.__executionMsec
            self.__status['executionMsec'] = int(executionMsec)
            
            # log to uuid, only for user facing threads
            if self.__cat is not None or (self._parentId is None and self._threadMgr):
                status = self.status2msg()
#                 status['type'] = thtype = self.__class__.__name__
                msg = json.dumps(status)
                UUIDLOG.info('%s output start %s %s output end' % (self.__uuid, msg, self.__uuid))
        
    def status2msg(self):
        """ status to msg for logging """
        res = {}
        
        res['startTime'] = self.__status['startTime']
        if (self.__status['executionMsec'] != None):
            res['executionMsec'] = self.__status['executionMsec']

        if (self.__status['result'] != None):
            res['result'] = self.__status['result']

        # check if the result is an error not not
        if (self.__status['error'] == None):
            res['progress'] = self.__status['progress']
            
        else:
            res['errorMsg'] = self.__status['errorMsg']
            res['error'] = self.__status['error']

        res['type'] = self.__status['type']
        if self.__status['correlationId']:
            res['correlationId'] = self.__status['correlationId']
        
        if self.__status['requrl']:
            res['requrl'] = self.__status['requrl']
        
        if self.__childExecThreadIds:
            res['execThreads'] = self.__childExecThreadIds
        
        if self._parentId:
            res['parent'] = self._parentId
            
        return res
    
    def beforeRun(self):
        """ subclass override for logic before doRun, before timeout values applies"""
        pass

    def doRun(self):
        """ function for subclass override """
        raise NotImplementedError("doRun function not implemented")

    def setName(self, name):
        self.__name = name

    def getName(self):
        return self.__name if self.__name else threading.Thread.getName(self)
    
    def getReqChecksum(self):
        """ get request checksum """
        return contextutils.getcontext(self, "reqstr", None)
    
    def isMergeOnFound(self):
        """ get merge on found flag """
        return self._mergeOnFound
    
    def setMergeOnFound(self, mergeOnFound):
        """ set merge on found flag """
        self._mergeOnFound = mergeOnFound

    def setTimeout(self, timeout):
        """ set the timeout of this thread
        timeout is the amount of seconds from now that you want the thread to timeout
        """
        self._timeout = timeout
        
    def getTimeout(self):
        """ get timeout value """
        return self._timeout
        
    def setProgressTimeout(self, timeout):
        """ set the progress timeout of this thread
        timeout is the amount of seconds you allow progress stay the same
        """
        self._progressTimeout = timeout
        
    def getProgressTimeout(self):
        """ get progress timeout value """
        return self._progressTimeout
        
    def extendTimeout(self, delta):
        """ extend timeoutAt by delta """
        self.__timeoutAt += delta
        self._timeout += delta

    def stop(self):
        """ stop this thread from running at the next check """
        self.__stop = True

    def isStopped(self):
        """ if thread is stopped or being stopped"""
        return self.__stop

    def _checkStop(self, triggerException = True, threadName = None):
        """ check if this thread should stop.  If so exit by throwing exception or return boolean value to indicate whether to stop """
        if threadName is None:
            threadName = self.getName()
        
        if (self.__stop):
            msg = 'Stopping %s(%s) as requested' % (threadName, self.__uuid)
            LOG.warning(msg)
            self._updateStatus(httpStatus = 500, error = Errors.AGENT_THREAD_STOPPED,
                              errorMsg = msg)
            if (triggerException):
                raise SystemExit(Errors.AGENT_THREAD_STOPPED, msg)
            else:
                return msg

        if (time.time() > self.__timeoutAt):
            msg = 'Timeout (%d) reached: stopping %s(%s)' % (self._timeout, threadName, self.__uuid)
            LOG.warning(msg)
            self._updateStatus(httpStatus = 500, error = Errors.AGENT_THREAD_TIMEDOUT,
                              errorMsg = msg)
            if (triggerException):
                raise SystemExit(Errors.AGENT_THREAD_TIMEDOUT, msg)
            else:
                return msg

        if (self._progressTimeout and self._progressTimeout > 0):
            if (self.__lastProgress == None or self.__status['fprogress'] > self.__lastProgress[0]):
                self.__lastProgress = (self.__status['fprogress'], time.time())
            if (self.__lastProgress[0] >= self.__status['fprogress'] and
                time.time() > self.__lastProgress[1] + self._progressTimeout):
                msg = 'Progress timeout (%d) second reached: stopping %s(%s)' % (self._progressTimeout, threadName, self.__uuid)
                LOG.warning(msg)
                self._updateStatus(httpStatus = 500, error = Errors.AGENT_THREAD_PROGRESS_TIMEDOUT,
                                  errorMsg = msg)
                if (triggerException):
                    raise SystemExit(Errors.AGENT_THREAD_PROGRESS_TIMEDOUT, msg)
                else:
                    return msg
        return None


    ##############################################################
    # Http Status Update Methods
    ##############################################################

    def getUuid(self):
        """ get uuid of this thread """
        return self.__uuid

    def getProgress(self):
        """ get uuid of this thread """
        return self.__status['progress']

    def getCat(self):
        """ get cat of this thread """
        return self.__cat

    def getStatus(self):
        """ get status of this thread """
        with self.__lock:
            status = deepcopy(self.__status)
        
        return status
    
    def _setUuid(self, uuid):
        """ override generated uuid """
        self.__uuid = uuid
        
    def _setStatus(self, status):
        """ override status """
        self.__status.update(status)

    def _updateProgress(self, fprog, maxp=100):
        """ set fprog as floating point, 
        ensure that the fprog does not decrease
        @param fprog - new fprog to update to
        """
        fprog = min(fprog, maxp)
        if (fprog < self.__status['fprogress']):
            # make sure we don't go down in fprog
            LOG.warning('Progress reduced from %s to %s' % (str(self.__status['fprogress']),
                                                            str(fprog)))
            return
        
        self.__status['fprogress'] = float(fprog)
        self.__status['progress'] = int(self.__status['fprogress'])
        
    def _incProgress(self, fprogDelta, maxp=100):
        """ increment progress by a fp
        @param fprogDelta: delta to increment  
        """
        prog = self.__status['fprogress'] + math.fabs(fprogDelta)
        self._updateProgress(prog, maxp)
            
    def _updateStatus(self, httpStatus = None, progress = None, result = None, error = None, errorMsg = None):
        """ update status of this thread """
        with self.__lock:
            if (httpStatus != None):
                self.__status['httpStatus'] = int(httpStatus)
            if (progress != None):
                self._updateProgress(progress)
            if (result != None):
                self.__status['result'] = result
            if (error != None):
                self.__status['error'] = int(error)
            if (errorMsg != None):
                self.__status['errorMsg'] = errorMsg

    def _runExeThread(self, execThread):
        ''' run an execution thread, throw agent exception if it fails '''
        if execThread is None:
            return
        
        try:
        
            execThread.run()

            status = execThread.getStatus()
            if (status['error'] != None):
                raise AgentException(status['error'], status['errorMsg'])
        
            return status
        
        finally:
            self._addChildExeThreadId(execThread.getUuid())
    
    def getChildExeThreadIds(self):
        """ get all children exec_thread uuids """
        # base implementation returns empty
        return self.__childExecThreadIds
    
    def _addChildExeThreadId(self, threadId):
        """ add a child thread id """
        if type(threadId) == list:
            self.__childExecThreadIds = self.__childExecThreadIds + threadId
        else:
            self.__childExecThreadIds.append(threadId)

class DummyThread(AgentThread):
    ''' dummy thread used to recover persisted thread status '''
    def __init__(self, threadMgr, auuid, status):
        ''' constructor '''
        AgentThread.__init__(self, threadMgr, None, 'dummy_thread')
        self._setUuid(auuid)
        self._setStatus(status)

    def doRun(self):
        self._updateProgress(100)




