#pylint: disable=W0703,W0105
""" admin controller """
import re
from agent.lib.security import authutil
from agent.lib import manifestutil, utils, contextutils, configutil
from agent.lib.agent_thread.exec_thread import ExecThread
from agent.lib.base import BaseController
from agent.lib.errors import Errors
from agent.lib.result import errorResult, statusResult, doneResult
from agent.lib.security.agentauth import authorize
from agent.lib.utils import trackable
from pylons import request, response, config
import json
import logging
import os
import pylons
import traceback

LOG = logging.getLogger(__name__)

class AdminController(BaseController):
    """ admin controller """

    def __init__(self):
        """ constructor """
        BaseController.__init__(self)
        self.__timeout = float(pylons.config['exec_thread_timeout'])
        self.__progressTimeout = float(pylons.config['exec_thread_progress_timeout'])
        
    @authorize()
    @trackable()
    def addKey(self, key):
        """ adding a new public key to agent"""
        try:
            pubKeyDir = os.path.join(manifestutil.appDataPath('agent'), 'secure')
            pubKeyFiles = [f for f in os.listdir(pubKeyDir) if re.match(r'.*\.pub', f)]

            if not key.endswith('.pub'):
                return errorResult(request, response, Errors.INVALID_REQUEST, 'Key %s must end with .pub' % key, controller = self)
                
            if key in pubKeyFiles:
                return errorResult(request, response, Errors.INVALID_REQUEST, 'Key %s already exist' % key, controller = self)
                
            if (not request.body or request.body == ""):
                LOG.error('invalid body found in post command')
                return errorResult(request, response, 10001, 'No body found', controller = self)

            body = json.loads(request.body)
            
            if 'content' not in body:
                return errorResult(request, response, Errors.INVALID_REQUEST, 'No key content found', controller = self)
            
            keycontent = body['content']
            filepath = os.path.join(pubKeyDir, key)
            utils.writeFile(filepath, keycontent)
            
            return doneResult(request, response, controller = self)

        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error adding key %s, %s - %s' %
                               (key, str(excp), traceback.format_exc(2)),
                               controller = self)
    
    def removeKey(self, key):
        """ remove a key from agent """
        try:
            pubKeyDir = os.path.join(manifestutil.appDataPath('agent'), 'secure')
            pubKeyFiles = [f for f in os.listdir(pubKeyDir) if re.match(r'.*\.pub', f)]
        
            if key in pubKeyFiles: 
                if len(pubKeyFiles) == 1:
                    return errorResult(request, response, Errors.INVALID_REQUEST, "Cannot delete the last key", controller = self)
        
                utils.rmrf(os.path.join(pubKeyDir, key))
            else:
                return errorResult(request, response, Errors.INVALID_REQUEST, "Invalid key %s to delete" % key, controller = self)
            return doneResult(request, response, controller = self)

        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error removing key %s,  %s - %s' %
                               (key, str(excp), traceback.format_exc(2)),
                               controller = self)
    
    def listKeys(self):
        """ list existing keys in agent """
        try:
            pubKeyDir = os.path.join(manifestutil.appDataPath('agent'), 'secure')
            pubKeyFiles = [f for f in os.listdir(pubKeyDir) if re.match(r'.*\.pub', f)]
            return doneResult(request, response, result = pubKeyFiles, controller = self)

        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error listing key %s - %s' %
                               (str(excp), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def validateToken(self):
        """ validate token """
        return doneResult(request, response, result = "success", controller = self)
    
    @authorize()
    @trackable()
    def updateAgentCert(self):
        """ update agent server cert, this requires an agent restart to take effect """
        try:
            # parse the body
            if not request.body:
                LOG.error('invalid body found in post command')
                return errorResult(request, response, Errors.INVALID_REQUEST, 
                                   'No body found', controller = self)

            body = json.loads(request.body)
            if 'cert' in body:
                cert = body['cert']
            serverCert = os.path.join(manifestutil.appDataPath('agent'), 'secure', 'server.pem')
            if cert:
                utils.writeFile(serverCert, cert)
            
            return doneResult(request, response, controller=self)

        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when update agent password %s - %s' %
                               (str(excp), traceback.format_exc(2)),
                               controller = self)
        
        
    @authorize()
    @trackable()
    def updateAgentPwd(self):
        """ update agent password, the password is used in simple authn mode for authentication """
        try:
            # parse the body
            if not request.body:
                LOG.error('invalid body found in post command')
                return errorResult(request, response, Errors.INVALID_REQUEST, 
                                   'No body found', controller = self)

            body = json.loads(request.body.encode('ascii', 'ignore'))

            override = {}
            if 'password' in body:
                override['password.local'] = body['password']       
            authutil.updateSecureMeta(override)
            return doneResult(request, response, controller=self)

        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when update agent password %s - %s' %
                               (str(excp), traceback.format_exc(2)),
                               controller = self)
        finally:
            configutil.loadSecureConfigOverrides()

    @authorize()
    @trackable()
    def executeCmd(self):
        """ execute a command synchronously """
        try:
            # parse the body
            if not request.body:
                LOG.error('invalid body found in post command')
                return errorResult(request, response, Errors.INVALID_REQUEST, 'No body found', controller = self)

            body = json.loads(request.body.encode('ascii', 'ignore'))

            if 'cmd' not in body:
                return errorResult(request, response, Errors.INVALID_REQUEST, 'No cmd found', controller = self)
            
            cmd0 = body['cmd']
            hasSudo = ('sudoUser' in body and body['sudoUser'])
            sudoUser = body['sudoUser'] if ('sudoUser' in body and body['sudoUser'] != 'root') else None
            LOG.info('%s %s %s' % (cmd0, hasSudo, sudoUser))

            cmd = cmd0.split()
            if hasSudo:
                cmd.insert(0, 'sudo')
                if sudoUser is not None:
                    cmd.insert(1, sudoUser)
                    cmd.insert(1, '-u')

            appGlobal = config['pylons.app_globals']
            execThread = ExecThread(appGlobal.threadMgr, cmd)
            execThread.setLogLevel('info')
            contextutils.copyJobContexts(self, execThread)
            execThread.start()

            return statusResult(request, response, execThread, controller = self)

        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when executing cmd %s,  %s - %s' %
                               (cmd, str(excp), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def executeScript(self):
        """ execute a script from remote location"""
        scriptpath = None

        try:
            # parse the body
            if (not request.body or request.body == ""):
                LOG.error('invalid body found in post command')
                return errorResult(request, response, 10001, 'No body found in post command', controller = self)

            body = json.loads(request.body.encode('ascii', 'ignore'))
            
            scriptloc = body['scriptLocation'] if 'scriptLocation' in body else None
            scriptname = body['scriptName'] if 'scriptName' in body else None
            
            hasSudo = ('sudoUser' in body and body['sudoUser'])
            sudoUser = body['sudoUser'] if ('sudoUser' in body and body['sudoUser'] != 'root') else None
            
            paramobj = body['params'] if 'params' in body else []
            params = paramobj if type(paramobj) == list else paramobj.split()

            LOG.info('%s %s %s %s %s' % (scriptloc, scriptname, hasSudo, sudoUser, params))

            if not scriptloc:
                return errorResult(request, response, Errors.INVALID_REQUEST, 'Script location not found', controller = self)
            
            if not scriptname:
                return errorResult(request, response, Errors.INVALID_REQUEST, 'Script name not found', controller = self)

            scriptpath = os.path.join(self.dataPath(), scriptname)
            LOG.info('scriptpath = %s' % scriptpath)

            utils.runsyscmd('wget %s -O %s' % (scriptloc, scriptpath))

            if not os.path.exists(scriptpath):
                return errorResult(request, response, Errors.FILE_NOT_FOUND_ERROR, 'Failed to get script %s' % scriptpath, controller = self)

            utils.rchmod(scriptpath, '+rx')

            cmd = [scriptpath]
            if hasSudo:
                cmd.insert(0, 'sudo')
                if sudoUser:
                    cmd.insert(1, sudoUser)
                    cmd.insert(1, '-u')

            for param in params:
                cmd.append(param)

            LOG.info('cmd = %s' % cmd)

            appGlobal = config['pylons.app_globals']
            execThread = ExecThread(appGlobal.threadMgr, cmd)
            execThread.setLogLevel('info')
            contextutils.copyJobContexts(self, execThread)
            execThread.start()
            execThread.threadMgrEvent.wait()

            return statusResult(request, response, execThread, controller = self)

        except Exception as excp:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error when executing cmd %s,  %s - %s' %
                               (scriptpath, str(excp), traceback.format_exc(2)),
                               controller = self)

    def dataPath(self):
        """ compute the path to the packages """
        datapath = os.path.realpath(os.path.join(manifestutil.servicePath('agent'), '.data'))
        if not os.path.exists(datapath):
            os.system('mkdir %s' % datapath)
        return datapath
