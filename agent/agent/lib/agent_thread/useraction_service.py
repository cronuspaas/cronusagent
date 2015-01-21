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

class UserActionService(ManifestControl):
    """ This thread will attempt to restart a service
    This means going through each package in ACTIVE manifest
    call the shutdown
    call start
    """
    THREAD_NAME = 'service_lifecycle'

    def __init__(self, threadMgr, service, action, parentId = None):
        """ Constructor """
        ManifestControl.__init__(self, threadMgr, service, manifest = None, parentId = parentId)
        self.setName(UserActionService.THREAD_NAME)
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
                raise AgentException(error = Errors.ACTIVEMANIFEST_MANIFEST_MISSING, errorMsg = 'No active manifest - cannot restart service')

            activeManifest = os.path.basename(readlink(activePath))

            self.__lcmActionManifest(self._service, activeManifest, self.__action)

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

                self._updateStatus(httpStatus = 500, error = errorCode, errorMsg = errorMsg)

    def __lcmActionManifest(self, service, manifest, action):
        """ shutdown a manifest.  This means calling shutdown script on manifest packages
        @param service - service of manifest to deactivate
        """
        self._LOG.info("%s active Manifest %s" % (action, service))
        self._execPackages(action, service, manifest, 50, 90)


