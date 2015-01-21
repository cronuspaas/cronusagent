#pylint: disable=W0703,R0915,R0912,R0904,E0102,E1101,E0202,R0914,W0105
""" Thread to perform download packages """

import traceback
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.lib.agent_thread.download_helper import DownloadHelper

import logging
from agent.lib import utils

LOG = logging.getLogger(__name__)

class PackageDownload(DownloadHelper):
    """ This thread will attempt to download packages    """

    inProgressExt = '.inprogress'

    def __init__(self, threadMgr, packages, parentId = None):
        """ Constructor """
        DownloadHelper.__init__(self, threadMgr, cat = None, name = 'download_package', parentId = parentId)
        self.__packages = packages

    def doRun(self):
        """ Main body of the thread
        """
        try:
            utils.checkDiskFull()

            # now make sure all the packages are downloaded
            self._downloadPackages(self.__packages)
            self._updateStatus(progress = 100)
            LOG.info('Completed download all packages for %s' % self.__packages)

        except AgentException as exc:
            LOG.info(exc.getMsg())
            self._updateStatus(httpStatus = 500, error = exc.getCode(), errorMsg = exc.getMsg())
            
        except Exception as exc:
            errCode = Errors.UNKNOWN_ERROR
            msg = 'Unknown error for downloading %s - %s - %s' % (self.__packages, str(exc), traceback.format_exc(2))
            LOG.info(msg)
            self._updateStatus(httpStatus = 500, error = errCode, errorMsg = msg)




