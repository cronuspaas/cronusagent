#pylint: disable=W0703,W0105
""" status controller """

import json
import logging
import traceback

from pylons import request, response, config

from agent.lib import manifestutil, utils
from agent.lib.agent_thread.cancel_agentthread import AgentThreadCancel
from agent.lib.base import BaseController
from agent.lib.errors import Errors, AgentException
from agent.lib.result import doneResult, statusResultRaw, errorResult, \
    statusResult
from agent.lib.security.agentauth import authorize
from agent.lib.utils import trackable


LOG = logging.getLogger(__name__)

class StatusController(BaseController):
    """ Status Controller.
    Used to return the status of a long running action

    Url looks like http://<host>/status/{uuid}
    The response is there an error or a progress
    """

    @trackable()
    def get(self, uuid):
        """ Get the status of this particular thread.
        Use the uuid to grab the correct thread.
        return the progress and status of the thread. """

        try:
            appGlobal = config['pylons.app_globals']

            thread = appGlobal.threadMgr.getThreadByUuid(uuid)
            if (thread == None):
                script = manifestutil.getPackageScriptPath('agent', 'active', 'agent', 'uuid')
                tmp = [script, uuid]
                cmds = []
                for cmd in tmp:
                    cmds.append(cmd.encode('ascii', 'ignore'))
                cmdout = utils.runsyscmdwstdout(cmds)
                if cmdout:
                    # make sure it's a valid json
                    result = json.loads(cmdout) 
                    # return status as raw
                    return statusResultRaw(request, response, result)
                else:
                    return errorResult(request, response, Errors.STATUS_UUID_NOT_FOUND,
                                       'Unable to find thread with uuid(%s)' % uuid,
                                       controller = self)
            
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for get status(%s) - %s, %s' %
                               (uuid, str(excep), traceback.format_exc()),
                               controller = self)
            
        return statusResult(request, response, thread, controller = self, maxProgress = 99 if thread.isAlive() else 100)
    
    @trackable()
    def getUuidOutput(self, uuid):
        """ get script output with an uuid """
        LOG.info('get ouput for %s' % uuid)
        try:
            script = manifestutil.getPackageScriptPath('agent', 'active', 'agent', 'execoutput')
            LOG.info('execoutput script %s' % script)
            
            if not uuid or uuid == '':
                raise AgentException(Errors.INVALID_REQUEST, 'uuid cannot be empty')
            
            tmp = [script, 'uuid', uuid]
            cmds = []
            for cmd in tmp:
                cmds.append(cmd.encode('ascii', 'ignore'))
            cmdout = utils.runsyscmdwstdout(cmds)
            response.content_type = 'text/plain'
            return cmdout
            
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Error when get execoutput %s - %s' %
                               (str(excep), traceback.format_exc(2)), controller = self)
            
    @trackable()
    def getGuidOutput(self, guid):
        """ get script output with a guid """
        LOG.info('get ouput for %s' % guid)
        try:
            script = manifestutil.getPackageScriptPath('agent', 'active', 'agent', 'execoutput')
            LOG.info('execoutput script %s' % script)
            
            if not guid or guid == '':
                raise AgentException(Errors.INVALID_REQUEST, 'guid cannot be empty')
            
            tmp = [script, 'guid', guid]
            cmds = []
            for cmd in tmp:
                cmds.append(cmd.encode('ascii', 'ignore'))
            cmdout = utils.runsyscmdwstdout(cmds)
            response.content_type = 'text/plain'
            return cmdout
            
        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Error when get execoutput %s - %s' %
                               (str(excep), traceback.format_exc(2)), controller = self)

    @authorize()
    @trackable()
    def delete(self, uuid):
        """ cancel an active thread """
        LOG.info('Cancel thread with uuid ' + uuid)
        try:
            async = False
            if request.body:
                body = json.loads(request.body)
                if 'async' in body:
                    async = True
            LOG.info('Canceling. async %s' % async)

            comment = body.get('comment')
            LOG.debug('Canceling.  comment: %s' % comment)

            appGlobal = config['pylons.app_globals']
            cancelThread = AgentThreadCancel(appGlobal.threadMgr, uuid)
            self.injectJobCtx(cancelThread)
            cancelThread.start()
            cancelThread.threadMgrEvent.wait()
            if not async:
                cancelThread.join()

            return statusResult(request, response, cancelThread, controller = self)
        except AgentException as exc:
            msg = 'Could not cancel distribution thread with uuid ' + uuid + exc.getMsg
            return errorResult(request, response, error = exc.getCode(), errorMsg = msg, controller = self)
        except Exception:
            code = Errors.UNKNOWN_ERROR
            msg = 'Could not cancel distribution thread with uuid ' + uuid + '(#' + str(code) + '). ' + traceback.format_exc(5)
            return errorResult(request, response, error = code, errorMsg = msg, controller = self)
        

    @trackable()
    def done(self):
        """ just return a good result """
        return doneResult(request, response, controller = self)


