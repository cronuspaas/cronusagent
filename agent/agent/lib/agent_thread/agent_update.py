#pylint: disable=W0703,R0912,R0904,E1101,R0904,E1124,W0105
""" thread to upgrade agent """
import traceback

from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.lib.agent_thread.agent_thread import AgentThread
import logging
import pylons
from agent.lib import manifestutil, contextutils
import os
from agent.lib.utils import readlink
import re
import json

LOG = logging.getLogger(__name__)
UUIDLOG = logging.getLogger('uuid')

class AgentUpdate(AgentThread):
    """ This thread will attempt to update agent
    """
    THREAD_NAME = 'agent_update'
    CAT = 'agent_blocking'

    def __init__(self, threadMgr, wisbVersion, wisbSource = None):
        """ Constructor """
        AgentThread.__init__(self, threadMgr, cat = [AgentUpdate.CAT], name = AgentUpdate.THREAD_NAME)
        self.__wisbVersion = wisbVersion
        self.__wisbSource = wisbSource
        self.__packages = []
        self.__service = 'agent'
        self.__manifest = ('agent_selfupdate-%s' % self.__wisbVersion)

    def doRun(self):
        """ Main body of the thread """
        errorMsg = ""
        errorCode = None
        failed = False
        appGlobal = pylons.config['pylons.app_globals']
        appGlobal.agentInfo['update_inprogress'] = True
        try:
            self._checkStop()
            self.__prepManifest()
            self._checkStop()
            self.__createManifest()
            self._checkStop()
            self.__activateManifest()

        except AgentException as exc:
            failed = True
            errorMsg = 'Agent update - Agent Exception - %s' % exc.getMsg()
            errorCode = exc.getCode()

        except Exception as exc:
            failed = True
            errorMsg = 'Agent update - Unknown error - (%s/%s) - %s - %s' \
                        % ('agent', self.__manifest, str(exc), traceback.format_exc(5))
            errorCode = Errors.UNKNOWN_ERROR

        finally:
            if failed:
                LOG.error(errorMsg)
                self._updateStatus(httpStatus = 500, error = errorCode, errorMsg = errorMsg)

            self._updateStatus(progress = 100)
            appGlobal.agentInfo['update_inprogress'] = False

    def __prepManifest(self):
        """ prepare data for manifest
        """
        try:
            if not self.__wisbVersion:
                raise AgentException(Errors.MANIFEST_NOT_FOUND, 'wisb version not found')

            agtPkg = AgentUpdate.getAgentPkgs(self.__wisbSource, self.__wisbVersion)
            pyPkg = AgentUpdate.getLocalPyPkg()
            LOG.info('Agent update using local python package %s' % pyPkg)
            self.__packages = [agtPkg, pyPkg]

        except AgentException as exc:
            errorMsg = 'Agent update - prepManifest - Agent exception - %s - %s' \
                        % (str(exc), traceback.format_exc(2))
            raise exc
        
        except Exception as exc:
            errorMsg = 'Agent update - prepManifest - Unknown error - %s - %s' \
                        % (str(exc), traceback.format_exc(2))
            error = Errors.UNKNOWN_ERROR
            raise AgentException(error, errorMsg)

    def __createManifest(self):
        """ create a manifest
        """
        service = 'agent'
        LOG.info("Create Manifest %s - %s - %s" % (service, self.__manifest, str(self.__packages)))
        path = manifestutil.manifestPath(service, self.__manifest)
        # check to see if the manifest already exists
        if (os.path.isdir(path)):
            LOG.info('Manifest %s already exist, skip creating' % self.__manifest)
            return

        from agent.lib.agent_thread.manifest_create import ManifestCreate
        manThread = ManifestCreate(self._threadMgr, service, self.__manifest, self.__packages, parentId = self.getUuid())
        contextutils.copycontexts(self, manThread, contextutils.CTX_NAMES)
        manThread.run()
        
        self._addChildExeThreadId(manThread.getChildExeThreadIds())
        
        status = manThread.getStatus()
        if (status.has_key('error') and status['error']):
            raise AgentException(status['error'], status['errorMsg'])

    def __activateManifest(self):
        """ activate a manifest
        """
        
        LOG.info("Activate Manifest %s - %s" % (self.__service, self.__manifest))
        # make sure manifest to be activated exist
        manifestPath = manifestutil.manifestPath(self.__service, self.__manifest)
        if (not os.path.exists(manifestPath)):
            LOG.error('Manifest %s does not exist, fail activation' % self.__manifest)
            raise AgentException(Errors.MANIFEST_NOT_FOUND, 'Manifest %s does not exist' % self.__manifest)

        # check to see if the manifest already active
        activeManifest = manifestutil.activeManifestPath(self.__service)
        
        if activeManifest == self.__manifest:
            LOG.info('Manifest %s already active, skip activation' % self.__manifest)
            return
        
        # activating new agent is going to kill agent process, update progress to 100% and flush all progress now
        self._updateProgress(100)
        status = self.status2msg()
        msg = json.dumps(status)
        UUIDLOG.info('%s output start %s %s output end' % (self.getUuid(), msg, self.getUuid()))
        
        from agent.lib.agent_thread.activate_manifest import ActivateManifest
        activateThread = ActivateManifest(self._threadMgr, self.__service, self.__manifest, parentId = self.getUuid())
        contextutils.copycontexts(self, activateThread, contextutils.CTX_NAMES)
        activateThread.run()
        
        self._addChildExeThreadId(activateThread.getChildExeThreadIds())
        
        status = activateThread.getStatus()
        if (status.has_key('error') and status['error']):
            raise AgentException(status['error'], status['errorMsg'])

    nameRe = re.compile('^[a-zA-Z0-9_]+-[0-9]+\.[0-9]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+?')

    @staticmethod
    def getAgentPkgs(wisbSource, wisbVersion):
        """ generate agent packages location
        """
        agtPkg = '%s/agent-%s.unix.cronus' % (wisbSource, wisbVersion)
#         agtcfgPkg = '%s/agent_config-%sprod.unix.cronus' % (wisbSource, wisbVersion)
        return agtPkg

    @staticmethod
    def getLocalPyPkg():
        """
        reuse of local python package instead of download it again from source of truth,
        this should be the common use case for selfupdate without needing to update the python package
        """
        activeManifest = manifestutil.getActiveManifest('agent')
        activePyLink = os.path.join(manifestutil.manifestPath('agent', activeManifest), 'python_package')
        if (os.path.exists(activePyLink)):
            activePyPath = readlink(activePyLink)
            pyVersion = os.path.basename(activePyPath)
            pyPkgName = ('python_package-%s' % pyVersion)
            port = pylons.config['port']
            if AgentUpdate.nameRe.match(pyPkgName):
                return ('http://localhost:%s/%s.cronus' % (port, pyPkgName))
            else: 
                raise AgentException(Errors.PACKAGE_SCHEME_ERROR, 'package name %s is not valid' % pyPkgName)

