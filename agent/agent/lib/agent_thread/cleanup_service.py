#pylint: disable=W0703,R0912,R0915,E0102,E1101,E0202,R0904,R0914,W0105
""" thread to cleanup service """
from agent.lib.agent_thread.service_delete import ServiceDelete
import logging
import time
import os
import traceback
            
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.lib import manifestutil
from agent.lib.agent_thread.manifest_control import ManifestControl

LOG = logging.getLogger(__name__)

class CleanupService(ManifestControl):
    """ This thread will attempt 
    1. stop service if running
    2. deactivate manifest
    3. remove service
    """

    THREAD_NAME = 'cleanup_service'

    def __init__(self, threadMgr, service):
        """ Constructor """
        ManifestControl.__init__(self, threadMgr, service, None)
        self.setName(CleanupService.THREAD_NAME)

    def doRun(self):
        """ Main body of the thread """
        self._updateProgress(1)

        errorMsg = ""
        errorCode = None
        failed = False
        
        try:
            
            if manifestutil.hasActiveManifest(self._service):

                manifest = manifestutil.getActiveManifest(self._service)

                self.__shutdownSuppressError(self._service, manifest)

                self.__deactivateSuppressError(self._service, manifest)
                
            self.__deleteService(self._service)   

        except SystemExit as exc:
            failed = True
            if (len(exc.args) == 2):
                # ok we got {err code, err msg}
                errorCode = exc.args[0]
                errorMsg = exc.args[1]
        
        except AgentException as exc:
            failed = True
            errorMsg = 'Cleanup Service - Agent Exception - %s' % exc.getMsg()
            errorCode = exc.getCode()
        
        except Exception as exc:
            failed = True
            errorMsg = 'Cleanup Service - Unknown error - (%s/%s) - %s - %s' \
                        % (self._service, self._manifest, str(exc), traceback.format_exc(5))
            errorCode = Errors.UNKNOWN_ERROR
            
        finally:

            if failed: 
                self._LOG.warning(errorMsg)
                self._updateStatus(httpStatus = 500, error = errorCode, errorMsg = errorMsg)
            else:
                self._updateProgress(100)

    def __shutdownSuppressError(self, service, manifest):
        """ shutdown active manifest suppress all errors """
        try:
            # shutdown service
            self._shutdownManifest(self._service, manifest, 1, 30)

        except Exception as exc:
            errorMsg = 'Cleanup Service - Agent Exception - %s' % exc.getMsg()
            self._LOG.warning(errorMsg)
        
    def __deactivateSuppressError(self, service, manifest):
        """ deactivate active manifest suppress all errors """
        try:
            # remove active manfiest
            self._deactivateManifest(self._service, manifest, 31, 60)

        except Exception as exc:
            errorMsg = 'Cleanup Service - Agent Exception - %s' % exc.getMsg()
            self._LOG.warning(errorMsg)

    def __deleteService(self, service):
        """ delete all services except agent itself; clear all manifests in 'agent' itself except current active"""
        self._updateStatus(progress = 60)
        #remove folder
        path = manifestutil.servicePath(service)
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
