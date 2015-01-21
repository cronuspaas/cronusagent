#pylint: disable=W0703,R0912,R0915,R0904,W0105
""" Thread to perform creation of a service """

import os
import traceback

from agent.lib.utils import islink
from agent.lib.utils import readlink
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.lib.agent_thread.manifest_control import ManifestControl
from agent.lib import manifestutil


class StartStopService(ManifestControl):
    """ This thread will attempt to restart a service
    This means going through each package in ACTIVE manifest
    call the shutdown
    call start
    """
    ACTION_STARTUP = 'Startup'
    ACTION_SHUTDOWN = 'Shutdown'
    ACTION_RESTART = 'Restart'

    THREAD_NAME = 'service_lifecycle'

    def __init__(self, threadMgr, service, action, parentId = None):
        """ Constructor """
        ManifestControl.__init__(self, threadMgr, service, manifest = None, parentId = parentId)
        self.setName(StartStopService.THREAD_NAME)
        self.__action = action

    def doRun(self):
        """ Main body of the thread """
        errorMsg = ""
        errorCode = None
        failed = False
        activeManifest = None

        try:
            activePath = manifestutil.manifestPath(self._service, 'active')
            
            # make sure that the active path exists and it is a link
            # Should we check this again since we already have a check in action controller
            if not os.path.exists(activePath) or not islink(activePath):
                raise AgentException(error = Errors.ACTIVEMANIFEST_MANIFEST_MISSING, 
                                     errorMsg = 'Service %s has no active manifest' % self._service)

            activeManifest = os.path.basename(readlink(activePath))

            if self.__action == StartStopService.ACTION_SHUTDOWN:
                self._shutdownManifest(self._service, activeManifest, 50, 90)
            elif self.__action == StartStopService.ACTION_STARTUP:
                self._startupManifest(self._service, activeManifest, 50, 90)
            elif self.__action == StartStopService.ACTION_RESTART:
                self._restartManifest(self._service, activeManifest, 10, 90)
            else:
                raise AgentException(error = Errors.INVALID_LIFECYCLE_ACTION, 
                                     errorMsg = 'Invalid life cycle action - %s' % self.__action)

            self._LOG.info('Done: %s service for (%s/%s)' % (self.__action, self._service, activeManifest))
            self._updateStatus(progress = 100)

        except AgentException as exc:
            failed = True
            errorMsg = '%s Service - Agent Exception - %s' % (self.__action, exc.getMsg())
            errorCode = exc.getCode()
            
        except Exception as exc:
            failed = True
            errorMsg = '%s Service - Unknown error - (%s/%s) - %s - %s' \
                        % (self.__action, self._service, self._manifest, str(exc), traceback.format_exc(5))
            errorCode = Errors.UNKNOWN_ERROR
            
        finally:
            if failed:
                self._LOG.error(errorMsg)

                if not self._skipCleanupOnFailure() and self.__action != StartStopService.ACTION_SHUTDOWN and self._service and activeManifest:
                    try:
                        self._LOG.info('%s Service %s failed, shutdown to cleanup' % (self.__action, self._service))
                        self._shutdownManifest(self._service, activeManifest, 91, 99)
                    except BaseException as excep:
                        self._LOG.error('Cleanup failed - %s' % str(excep))

                self._updateStatus(httpStatus = 500, error = errorCode, errorMsg = errorMsg)

