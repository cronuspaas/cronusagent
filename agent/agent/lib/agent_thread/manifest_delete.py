#pylint: disable=W0703,R0904,W0105
""" Thread to perform service deletes """

import shutil
from agent.lib.errors import Errors
from agent.lib.agent_thread.agent_thread import AgentThread
import logging
from agent.lib import manifestutil, serviceutil

LOG = logging.getLogger(__name__)

class ManifestDelete(AgentThread):
    """ All threads used by the agent should be of type agent thread.
    This thread will be used to generate ids, provide categories for the thread mgr. """

    def __init__(self, threadMgr, service, manifest, parentId = None):
        """ Constructor """
        AgentThread.__init__(self, threadMgr, cat = [manifestutil.serviceCat(service)], name = 'delete_manifest', parentId = parentId)
        self.service = service
        self.manifest = manifest

    def doRun(self):
        """ Main body of the thread """
        try:
            # now try to delete the manifest directory
            shutil.rmtree(manifestutil.manifestPath(self.service, self.manifest))
            serviceutil.removeActivatedManifestList(self.service, self.manifest)
            self._updateStatus(progress = 100)
        except OSError as excp:
            msg = 'Manifest(%s, %s) path error: %s' % (self.service, self.manifest, str(excp))
            self._updateStatus(httpStatus = 500, error = Errors.MANIFEST_PATH_ERROR, errorMsg = msg)
        except Exception as exc:
            msg = 'Unknown error when deleting service %s - %s' % (self.service, str(exc))
            errCode = Errors.UNKNOWN_ERROR
            self._updateStatus(httpStatus = 500, error = errCode, errorMsg = msg)

