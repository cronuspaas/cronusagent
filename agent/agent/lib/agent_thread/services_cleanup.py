#pylint: disable=W0141, W0511, W0703, W0612,R0904,W0105
""" Thread to perform service deletes """

import os
import logging
import time
import traceback

from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.lib.agent_thread.exec_thread import ExecThread
from agent.lib.agent_thread.agent_thread import AgentThread
from agent.lib.agent_thread.service_delete import ServiceDelete
from agent.controllers.service import ServiceController
from agent.lib.packagemgr import PackageMgr
from agent.lib import utils, configutil, manifestutil

LOG = logging.getLogger(__name__)

class ServicesCleanup(AgentThread):
    """ All threads used by the agent should be of type agent thread.
    This thread will be used to generate ids, provide categories for the thread mgr. """

    CAT = "cleanup"

    def __init__(self, threadMgr, stopOnly=False):
        """ Constructor """
        AgentThread.__init__(self, threadMgr, cat = [ServicesCleanup.CAT], name = 'cleanup_service')
        self.__killTimeout = configutil.getConfigAsInt('agent_thread_timeout') #kill -9 should take no time
        self.__stopOnly = stopOnly
        
    def __stopProcesses(self):
        """ stop all processes that run as app_user_account
            refers to http://stackoverflow.com/questions/4669754/python-kill-all-processes-owned-by-user
        """
        self._updateStatus(progress = 10)
        uname = configutil.getAppUser()
        uid, _ = utils.getUidGid(uname)
        pids = filter(lambda pid: pid.isdigit(), os.listdir('/proc'))
        execThreads = []

        # test if PID is owned by user
        for pid in pids:
            # check if PID still exist
            if not os.path.exists(os.path.join('/proc', pid)):
                LOG.debug("pid doesn't exist any more: %s" % pid)
                continue

            puid = os.stat(os.path.join('/proc', pid)).st_uid
            if puid == uid:
                cmd = utils.sudoCmd(['kill', '-9', pid], uname)
                execThread = ExecThread(self._threadMgr, cmd)
                execThread.setTimeout(self.__killTimeout)
                execThread.start()
                execThreads.append(execThread)
                self._addChildExeThreadId(execThread.getUuid())

        while(True):
            self._checkStop()

            running = False
            for execThread in execThreads:
                status = execThread.getStatus()
                if (status['error'] != None):
                    raise AgentException(status['error'], status['errorMsg'])

                if (execThread.isAlive()):
                    LOG.debug("process is still alive: %s" % execThread.getCmd())
                    running = True

            if (not running):
                LOG.debug("stop processes finished: %s" % [execThread.getCmd()[-1] for execThread in execThreads])
                break

            time.sleep(0.1)

        self._updateStatus(progress = 50)

    def __deleteServices(self):
        """ delete all services except agent itself; clear all manifests in 'agent' itself except current active"""
        self._updateStatus(progress = 60)
        services = ServiceController.getServices()

        #kill all service threads
        self._threadMgr.stopServiceThread()

        #remove folder
        for service in services:
            if 'agent' == service:
                self.__delAllExceptActiveManifests(service)
                continue

            path = ServiceController.servicePath(service)
            # retry service cleanup
            for _ in range(3):
                if not os.path.exists(path):
                    break
                ServiceDelete.deleteFolderContents(path)
                # sleep here a bit to ensure delete is complete
                time.sleep(1)

            if os.path.exists(path):
                msg = 'Could not delete service %s completely even after 3 retries.' % service
                LOG.error(msg)
                raise Exception(msg)

        self._updateStatus(progress = 90)

    def __delAllExceptActiveManifests(self, service):
        '''
        Delete all manifests in the given service except active link and corresponding manifest (if one exists).
        Doesn't delete the corresponding dir in installed-packages (similar to 'delete manifest')
        '''
        manifests = manifestutil.getManifests(service)
        active = manifestutil.getActiveManifest(service)
        if active and len(active) != 0: # 'active' can be none
            manifests.remove(active)
        for mft in manifests:
            mf_path = manifestutil.manifestPath(service, mft)
            ServiceDelete.deleteFolderContents(mf_path)

    def __deletePackages(self):
        """ delete all packages from pakcage directory """
        package_path = PackageMgr.packagePath()
        ServiceDelete.deleteFolderContents(package_path, onlyChildren = True)

    def doRun(self):
        """ Main body of the thread """
        try:
            cleaned = True

            try:
                self.__stopProcesses()
                if not self.__stopOnly:
                    self.__deleteServices()
                    self.__deletePackages()

            except BaseException:
                errorMsg = 'Service Cleanup Exception - %s' % traceback.format_exc(5)
                LOG.warning(errorMsg)
                self._updateStatus(httpStatus = 500, error = Errors.SERVICES_CLEANUP_FAIL,
                                   errorMsg = errorMsg)
                cleaned = False

            if cleaned:
                self._updateStatus(progress = 100)

        except Exception as exc:
            msg = 'Unknown error when cleaning up services on agent - %s' % (str(exc))
            errCode = Errors.UNKNOWN_ERROR
            self._updateStatus(httpStatus = 500, error = errCode, errorMsg = msg)
