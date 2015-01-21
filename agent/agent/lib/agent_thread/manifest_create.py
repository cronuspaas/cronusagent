#pylint: disable=W0703,R0915,R0912,R0904,E0102,E1101,E0202,R0914,W0105
""" Thread to perform creation of a service """

import os
import shutil
import traceback
from agent.lib.errors import Errors
from agent.lib.errors import AgentException
from agent.lib.utils import symlink
from agent.lib.agent_thread.download_helper import DownloadHelper
from agent.lib.package import PackageUtil

import logging
from agent.lib import utils, manifestutil

LOG = logging.getLogger(__name__)

class ManifestCreate(DownloadHelper):
    """ This thread will attempt to create new manifests.
    This means creating the directory.
    Downloading the packages, if necessary.
    Verifying the package.
    Untaring the package.
    verifying the untar'd package.
    """

    inProgressExt = '.inprogress'

    def __init__(self, threadMgr, service, manifest, packages, forcePackages = None, parentId = None):
        """ Constructor """
        DownloadHelper.__init__(self, threadMgr, cat = [manifestutil.serviceCat(service)], name = 'create_manifest', parentId = parentId)
        self.__manifest = manifest
        self.__service = service
        self.__packages = packages
        self.__forcePackages = forcePackages

    def doRun(self):
        """ Main body of the thread

        Progress Info:
        Look at the list of packages this manifest has and figure out the progress of this manifest
        Progress 1 = manifest directory created
        Progress 2-80 = all packages downloaded
        Progress 81-99 = all packages untarred
        Progress 100 = all links done
        """
        inProgressPath = ManifestCreate.inProgress(manifestutil.manifestPath(self.__service, self.__manifest))
        try:
            if self.__service != 'agent':
                utils.checkDiskFull()

            installedPkgPath = manifestutil.installedPkgRootPath(self.__service)

            # This should not happen but make sure there isn'trn already a manifest directory in progress
            if (os.path.isdir(inProgressPath)):
                # probably another manifest create thread died out half way.
                # Cleanup and reattempt manifest creation
                LOG.debug('Manifest inprogress found for service/manifest (%s/%s). Will cleanup and retry' % (self.__service, self.__manifest))
                shutil.rmtree(inProgressPath)

            # make sure that the service path and installed package path exists
            if (not os.path.isdir(manifestutil.manifestRootPath(self.__service)) or
                not os.path.isdir(manifestutil.installedPkgRootPath(self.__service))):
                errCode = Errors.SERVICE_NOT_FOUND
                msg = 'Service (%s) for manifest (%s) not found' % (self.__service, self.__manifest)
                self._updateStatus(httpStatus = 500, error = errCode, errorMsg = msg)
                return

            # ok create the manifest path
            os.mkdir(inProgressPath)

            self._updateProgress(1)

            # figure out which of the packages are already there
            remainingPackages = {}
            for pkgUri in self.__packages:
                pkgDict = PackageUtil.parseUri(pkgUri)
                pkgPath = os.path.join(installedPkgPath, pkgDict['packageName'], pkgDict['packageVersion'])
                pkgName = pkgDict['packageName']
                if (not os.path.exists(pkgPath)) or ((self.__forcePackages is not None) and pkgName in self.__forcePackages):
                    remainingPackages[pkgUri] = pkgDict
                else:
                    symlink(pkgPath, os.path.join(inProgressPath, pkgDict['packageName']))

            if len(remainingPackages) > 0:
                # now make sure all the packages are downloaded
                try:
                    self._downloadPackages(remainingPackages.keys())
                except AgentException as exc:
                    # check if it is download error, then modify exception appropriately
                    if exc.getCode() == Errors.DC_FAILED_DOWNLOAD:
                        exc = AgentException(Errors.MANIFEST_PACKAGE_DOWNLOAD_FAILED,
                                            'Manifest (%s/%s) failed downloading package - %s'
                                            % (self.__service, self.__manifest, exc.getMsg()))
                    raise exc

            LOG.info('Completed download all packages for (%s/%s)' % (self.__service, self.__manifest))

            # now untar the packages
            import re
            pkgSuffix = '.%s' % re.sub(r"\W", "", self.__manifest)
            self._untarPackages(remainingPackages, self.__service, 
                                manifestutil.installedPkgRootPath(self.__service), 0, self.__forcePackages, pkgSuffix)
            LOG.info('Completed untar all packages for (%s/%s)' % (self.__service, self.__manifest))

            # now create the links
            for pkgDict in remainingPackages.itervalues():
                pkgPath = os.path.join(installedPkgPath, pkgDict['packageName'], pkgDict['packageVersion'])
                linkPath = os.path.join(inProgressPath, pkgDict['packageName'])
                # validate target folder does exist
                if not os.path.exists(pkgPath):
                    raise AgentException(Errors.PACKAGE_PATH_ERROR, 'invalid untarred package at %s' % pkgPath)
                symlink(pkgPath, linkPath)

            # now move the inProgressPath to the final path
            manifestContentPath = manifestutil.manifestContentPath(self.__service, self.__manifest)

            os.rename(inProgressPath, manifestutil.manifestPath(self.__service, self.__manifest))

            mfContentsFile = file(manifestContentPath, 'w')
            for pkgUri in self.__packages:
                mfContentsFile.write(('%s%s') % (pkgUri, os.linesep))
            mfContentsFile.close()
            LOG.info('Completed create manifest for (%s/%s)' % (self.__service, self.__manifest))

            self._updateStatus(progress = 100)

        except AgentException as exc:
            LOG.info(exc.getMsg())
            self._updateStatus(httpStatus = 500, error = exc.getCode(), errorMsg = exc.getMsg())
            
        except Exception as exc:
            errCode = Errors.UNKNOWN_ERROR
            msg = 'Unknown error for (%s/%s) - %s - %s' % (self.__service, self.__manifest,
                                                           str(exc), traceback.format_exc(2))
            LOG.info(msg)
            self._updateStatus(httpStatus = 500, error = errCode, errorMsg = msg)
        finally:
            # clean up intermediate progress
            try:
                shutil.rmtree(inProgressPath)
            except OSError:
                pass

    @staticmethod
    def inProgress(filename):
        """ return the inprogress version of the method """
        return filename + ManifestCreate.inProgressExt

    @staticmethod
    def isInProgress(filename):
        """ return True if object is in progress """
        return filename.endswith(ManifestCreate.inProgressExt)



