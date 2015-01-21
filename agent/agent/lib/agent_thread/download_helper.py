#pylint: disable=W0703,R0915,R0912,R0914,R0904,W0223,W0105
""" Base class for package download and manifest create operations """

import pylons
import os
import time
from agent.lib.errors import Errors, AgentException
from agent.lib.utils import calcProgress, rchown, rchmod, isHigherPrivilegeService, \
    chmod, getuserofpath, rmrf
from agent.lib.agent_thread.agent_thread import AgentThread
from agent.lib.package import PackageUtil
from agent.lib.packagemgr import PackageMgr
from agent.lib.agent_thread.download_thread import DownloadThread
from agent.lib import contextutils, configutil, utils, manifestutil

import logging
from agent.lib.agent_thread.exec_thread import ExecThread

LOG = logging.getLogger(__name__)

class DownloadHelper(AgentThread):
    """ This thread will attempt to help creating packages for createManifest and createPackages APIs.
    This means creating the directory.
    Downloading the packages, if necessary.
    Verifying the package.
    Untaring the package.
    """

    inProgressExt = '.inprogress'

    def __init__(self, threadMgr, cat = None, name = 'agent_thread', parentId = None):
        """ Constructor """
        AgentThread.__init__(self, threadMgr, cat = cat, name = name, parentId = parentId)

    def _findPackagesToDownload(self, packages, packageRootPath):
        ''' check which packages exist and which need to be downloaded '''
        # figure out which of the packages are already there
        remainingPackages = {}
        for one_package in packages:
            one_package_dict = PackageUtil.parseUri(one_package)
            one_package_path = os.path.join(packageRootPath, one_package_dict['packageName'], one_package_dict['packageVersion'])
            if (not os.path.exists(one_package_path)):
                remainingPackages[one_package] = one_package_dict
        return remainingPackages
    
    def _downloadPackages(self, packages, isFailedFatal = True):
        """
        download all the packages
        update progress
        check for timeout

        @params packages = list of package uri's
        @throws AgentException
        """
        try:
            appGlobal = pylons.config['pylons.app_globals']

            # globals all the remaining packages, download the packages
            pkgObjs = []
            for pkg in packages:
                packageKey = PackageUtil.getPackageKey(pkg)
                matchDlThreads = appGlobal.threadMgr.getThreadByCat(packageKey)
                if matchDlThreads:
                    # found an inprogress download thread
                    dlThread = matchDlThreads[0]
                else:
                    dlThread = DownloadThread(self._threadMgr, pkg, category=[packageKey], packageloc=None, parentId = self.getUuid())
                    contextutils.copyJobContexts(self, dlThread)
                    dlThread.start()

                if (dlThread.getStatus().get('progress') != 100):
                    pkgObjs.append(dlThread)

                self._checkStop()

            # check that we have packages to download
            if (len(pkgObjs) == 0):
                return [] # nothing to download, so no failed packages

            # now wait for all the packages to finish
            liveThreadCount = len(pkgObjs)
            timeoutNotSet = True
            create_sleep_time = float(pylons.config['exec_thread_sleep_time']) * liveThreadCount
            failed_packages = []
            
            while (liveThreadCount > 0):
                self._checkStop()
                LOG.info('%s packages still downloading' % liveThreadCount)
                time.sleep(create_sleep_time)

                # go through all the packages and
                # calculated average progress
                # check that all packages are alive
                totalProgress = 0
                liveThreadCount = 0

                timeouts = (0.0, 0.0)
                for dlThread in pkgObjs:
                    
                    # we are not done yet
                    if dlThread.isAlive():
                        liveThreadCount += 1
                        
                    # if one package failed, then we have to fail the entire manifest
                    threadStatus = dlThread.getStatus()
                    if (not dlThread.isAlive() and threadStatus.get('progress') != 100):
                        if isFailedFatal:
                            raise AgentException(Errors.DC_FAILED_DOWNLOAD,
                                             'failed downloading package (%s) - %s'
                                             % (dlThread.getUriDict().get('uri'), threadStatus.get('errorMsg')))
                        failed_packages.append(dlThread.getUriDict().get('uri'))
                        
                    progressTimeout = dlThread.getProgressTimeouts()
                    if (progressTimeout and timeouts):
                        timeouts = (timeouts[0] + progressTimeout[0], timeouts[1] + progressTimeout[1])
                    else:
                        timeouts = None
                    pkgProgress = threadStatus.get('progress')
                    totalProgress += pkgProgress
                    
                if (timeouts and timeoutNotSet):
                    # Setting the timeout once as it is absolute time.  Doing this after the timeout for each
                    # package is available
                    self.extendTimeout(timeouts[0])
                    timeoutNotSet = False
                    LOG.debug('Using overall timeout=%s and progress timeout=%s' % (timeouts[0], timeouts[1]))

                # calculate the new progress
                # I'm allocating 80 of the progress to be the download
                newProgress = calcProgress(1, 79, float(totalProgress) / (100 * len(pkgObjs)))

                # now update the pgoress
                self._updateProgress(newProgress)


            return failed_packages

        finally:
            # now update the pgoress
            self._updateProgress(79)


    def untar(self, packagePath, untarPath, nicelevel):
        ''' do real untar '''
        cmd = ['tar', '-C', untarPath, '-x', '-f', packagePath]
        # timeout 60 minute
        execThread = ExecThread(None, cmd, None, self.getUuid())
        execThread.setTimeout(3600)
        execThread.run()

        status = execThread.getStatus()
        if (status['error'] != None):
            msg = 'untar cmd (%s) failed (%s - %s)' % (' '.join(cmd), status['error'], status['errorMsg'])
            LOG.error(msg)
            raise AgentException(Errors.PACKAGE_UNTAR_FAILURE, msg)
        
    def _untarPackages(self, packages, service, untarRootPath, nicelevel=None, pgksNeedSuffix=None, pathSuffix=''):
        """
        untar all the packages

        @params packages - list of dictionary of parsed packages uri
        @throws AgentException
        """
        self._updateProgress(80)
        count = 0
        for pkgDict in packages.itervalues():
            count += 1

            # check if package path exists already
            # if the package is already untarred, move on
            # else create the package path
            pkgName = pkgDict['packageName']
            untarPath = os.path.join(untarRootPath,
                                    pkgName,
                                    '%s%s' % (pkgDict['packageVersion'], pathSuffix if ((pgksNeedSuffix is not None) and pkgName in pgksNeedSuffix) else ''))

            if os.path.exists(untarPath):
                # perhaps another thread has finished extraction, continue with next package
                continue
            
            os.makedirs(untarPath)

            try:
                self.untar(pkgDict['packagePath'], untarPath, nicelevel)

            except AgentException:
                rmrf(untarPath)

            # Note: i. atleast self should have 'rx' so that we can proceed setting 'rx' for group and others
            # if both belong to same group in future, then just self, group should be enough
            # ensure all parent dir of scripts dir have 'rx' so that we can really navigate to scripts dir and execute
            uname = getuserofpath(untarPath)
            chmod(untarPath, '+rx', sudoUser = uname)
            cronusPath = os.path.join(untarPath, 'cronus')
            if os.path.exists(cronusPath):
                uname = getuserofpath(cronusPath)
                chmod(cronusPath, '+rx', sudoUser = uname)
                # now give all scripts 'rx' permission
                scriptsPath = os.path.join(cronusPath, 'scripts')
                if os.path.exists(scriptsPath):
                    uname = getuserofpath(scriptsPath)
                    rchmod(scriptsPath, '+rx', sudoUser = uname)

            # issue #16, now add symlink to .appdata for easy access
            appdata_path = manifestutil.appDataPath(service)
            link_path = os.path.join(untarPath, '.appdata')
            LOG.info('Create .appdata symlink from %s to %s' % (link_path, appdata_path))
            utils.symlink(appdata_path, link_path)

            
            #Running as cronus user when higher privilege service (i.e. not chown all the package into the application user)
            if (not isHigherPrivilegeService(service)):
                uname = configutil.getAppUser()
                uid, gid = utils.getUidGid(uname)
                rchown(untarPath, uid, gid)

            self._updateProgress(calcProgress(80, 99, float(count) / len(packages)))

    def _classfiy_packages(self, packages):
        """ verify that all packages that need to be downloaded exist """
        non_existent_packages = []
        filtered_packages = []
        packagePath = PackageMgr.packagePath()
        for one_package in packages:
            path = os.path.join(packagePath, one_package + '.cronus')
            if not os.path.exists(path):
                non_existent_packages.append(one_package)
            else:
                filtered_packages.append(one_package)
        return non_existent_packages, filtered_packages
