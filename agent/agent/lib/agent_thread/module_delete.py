#pylint: disable=W0703,R0904,W0105
""" Thread to perform __service deletes """

import os
import logging
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.lib.agent_thread.agent_thread import AgentThread
from agent.lib import utils, manifestutil

LOG = logging.getLogger(__name__)

class ModuleDelete(AgentThread):
    """ All threads used by the agent should be of type agent thread.
    This thread will be used to generate ids, provide categories for the thread mgr. """

    def __init__(self, threadMgr, module, parentId = None):
        """ Constructor """
        AgentThread.__init__(self, threadMgr, cat = [manifestutil.serviceCat('agent')], name = 'delete_module', parentId = parentId)
        self.__module = module
        self.__service = 'agent'

    def doRun(self):
        """ Main body of the thread """
        try:
            deleted = True
            path = manifestutil.modulePath(self.__service, self.__module)

            try:
                manifestutil.processModule(self.__service, self.__module, False)
                utils.rmlink(path)

            except AgentException as excep:
                LOG.warning('Delete Module Exception - %s', excep.getMsg())
                self._updateStatus(httpStatus = 500, error = excep.getCode(),
                                   errorMsg = excep.getMsg())
            except OSError as excep:
                LOG.warning('Delete Module Exception - %s', excep.getMsg())
                self._updateStatus(httpStatus = 500, error = Errors.SERVICE_DELETE_FAILED,
                                   errorMsg = 'Path (%s) failed to be deleted' % path)
                deleted = False

            # verify that the path does not exist
            if (os.path.exists(path) and deleted):
                self._updateStatus(httpStatus = 500, error = 1,
                                    errorMsg = 'Path (%s) still exists even after delete attempt' % path)

            self._updateStatus(progress = 100)
            
        except Exception as exc:
            msg = 'Unknown error when deleting module %s - %s' % (self.__service, str(exc))
            errCode = Errors.UNKNOWN_ERROR
            self._updateStatus(httpStatus = 500, error = errCode, errorMsg = msg)

