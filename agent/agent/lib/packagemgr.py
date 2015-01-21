#pylint: disable=W0511,C0103,W0621,E1101,W0212,W0703,R0912,W0611,W0105
"""
Package Manager

This class is responsible for maintaining the packages in the <agent_root>/packages directory.
It will download packages
Give progress of downloading packages
Garbage collect packages

The state is stored on the filesystem
all in progress (denoted with a .inprogress files will be deleted at startup)
"""

import pylons
import glob
import threading
import time
import os
import traceback

import logging
from agent.lib import agenthealth, manifestutil, configutil, serviceutil, utils
from agent.lib.errors import Errors
from agent.lib.agent_thread.service_delete import ServiceDelete
from agent.lib.agent_thread.manifest_delete import ManifestDelete
from agent.lib.package import PackageUtil

GCLOG = logging.getLogger('gc')

class PackageMgr(threading.Thread):
    """ Package Manager Class """

    def __init__(self, garbageFreq, maxPackageAge):
        """ Initialize the Package Mgr """
        threading.Thread.__init__(self)

        self.__stop = False

        self.__garbageFreq = float(garbageFreq)
        self.__maxPackageAge = float(maxPackageAge)
        
        PackageMgr.runOnceOnStartup()

    @staticmethod
    def packagePath():
        """ compute the path to the packages """
        return os.path.realpath(os.path.join(pylons.config['agent_root'], 'packages'))
    
    @staticmethod
    def runOnceOnStartup():
        """ one time check at startup """
        try:
            # if the packages directory isn't there create it
            if (not os.path.isdir(PackageMgr.packagePath())):
                try:
                    os.remove(PackageMgr.packagePath())
                except OSError:
                    pass
                os.makedirs(PackageMgr.packagePath())
        except Exception as exc:
            GCLOG.error('Unable to create packages directory %s' % str(exc))


    #####################################################
    # Garbage collection
    #####################################################

    def stop(self):
        """
        stop(self)

        stop the garbage collection thread
        """

        self.__stop = True

    def run(self):
        """
        the garbage collection thread body
        go through the list of packages and delete packages over a certain threshold
        two variables affect operation
        packageMgr_gc_freq = how GCLOG GC sleeps for between checks
        pacageMgr_package_age = how old a package can get to before it's deleted

        go through the list of inprogress threads and remove all threads that are done
        """
        #pylint:disable=R0914, R0912, R0915
        while (self.__stop == False):
            time.sleep(self.__garbageFreq)

            try: 
                if not self.__stop:
                    PackageMgr.runAgentGc()
                
            except Exception:
                code = Errors.UNKNOWN_ERROR
                msg = 'Failed to Garbage Collection ' + '(#' + str(code) + '). ' + traceback.format_exc(5)
                GCLOG.error(msg)
                
    @staticmethod
    def runAgentGc():
        """ agent gc """
        # go through all the packages and see if they are older than the threshold
        GCLOG.info('Run agent GC')
        for filename in glob.glob(os.path.join(PackageMgr.packagePath(), '*.cronus.inprogress')):
            if (time.time() > os.path.getatime(filename) + float(pylons.config['packageMgr_package_age'])):
                try:
                    GCLOG.info('Garbage collecting package(%s)' % filename)
                    os.remove(filename)
                except OSError, osErr:
                    GCLOG.error('Unable to garbage collect %s - %s' % (filename, osErr))
                        
        # clean old packages
        for filename in glob.glob(os.path.join(PackageMgr.packagePath(), '*.cronus')):
            GCLOG.debug('garbage collection check in progress for filename %s' % filename)
            try:
                if (time.time() > os.path.getatime(filename) + float(pylons.config['packageMgr_package_age'])):
                    GCLOG.info('Garbage collecting package(%s)' % filename)
                    os.remove(filename)
                    if os.path.exists(filename + '.prop'):
                        os.remove(filename + '.prop')
                    if os.path.exists(filename + '.inprogress'):
                        os.remove(filename + '.inprogress')
            except OSError, osErr:
                GCLOG.error('Unable to garbage collect %s - %s' % (filename, osErr))

        #import pdb;pdb.set_trace();
        PackageMgr.cleanupOrphanedPackages(False)
    
        # force cleanup more in aggressive GC
        packageMount = pylons.config['agent_root']
        if(agenthealth.needAggressiveGC(packageMount)):
            PackageMgr.forceCleanUpDownloadedPkgs()
                    
        # validate all services and remove rogue services
        PackageMgr.cleanRogueService()
        
        # remove not needed past manifests
        PackageMgr.cleanPastActivatedManifests()
        
    
    @staticmethod
    def cleanupOrphanedPackages(checkAge = False):
        '''  API to cleanup Orphaned Packages For All Services '''
        #services = os.listdir(service_nodes)
        #import pdb;pdb.set_trace()
        services = manifestutil.getServices()
        service_nodes = manifestutil.serviceRootPath()

        linkedPaths = []
        sysServices = ['agent']
        GCLOG.debug('Garbage collecting orphaned installed packages')
        for service in services:
            try:
                if service in sysServices:
                    GCLOG.debug('system services cannot be garbage collected')
                else:
                    servicePath = os.path.join(service_nodes, service)
                    installedPkgPath = os.path.join(servicePath, 'installed-packages')
                    linkedPaths.extend(manifestutil.getAllSymLinks(service))
                    linkedPaths.extend(manifestutil.getModuleSymLinks(service))
                    GCLOG.debug('symLinks returned %s' % linkedPaths)
                    installedPkgPaths = PackageUtil.getAllInstalledPackages(installedPkgPath)
                    GCLOG.debug('installedPkgPaths returned for the service %s' % installedPkgPaths)
                    if len(installedPkgPaths) > 0:
                        orphanPkgs = set(installedPkgPaths) - set(linkedPaths)
                        GCLOG.debug('orphanPkgs returned %s' % orphanPkgs)
                        PackageUtil.cleanupInstalledPkgs(installedPkgPath, orphanPkgs)
            except BaseException as excep:
                GCLOG.error('Failed to proceed with garbage collection %s' % str(excep))
                # agent-804, manifests only contains folders, need to delete if file is in manifests
                servicePath = os.path.join(service_nodes, service)
                if not os.path.isdir(servicePath):
                    utils.runsyscmd('rm -f %s' % servicePath)
        GCLOG.debug('Garbage collecting orphaned installed packages completed')

    @staticmethod
    def forceCleanUpDownloadedPkgs():
        ''' tries to cleanup packages from oldest date to latest ignoring packages downloaded in the last hour'''
        import operator

        GCLOG.debug('Force garbage collecting downloaded packages')
        packageMount = pylons.config['agent_root']
        lower_age_bound = float(pylons.config['packageMgr_package_min_age'])
        cronus_pkgs = glob.glob(os.path.join(PackageMgr.packagePath(), '*.cronus'))
        file_list = []
        for filename in cronus_pkgs:
            try:
                date_file_tuple = os.path.getatime(filename), os.path.getsize(filename), filename
                file_list.append(date_file_tuple)
            except OSError, osErr:
                GCLOG.error('Unable to get access time %s - %s' % (filename, osErr))

        file_list.sort(key = operator.itemgetter(0))
        #file_list.sort(key=operator.itemgetter(1))

        for (filedate, filesize, filename) in file_list:
            GCLOG.debug('garbage collection in progress for filename %s ' % filename)
            GCLOG.debug('filedate is %s ' % filedate)
            GCLOG.debug('filesize for current file is %s ' % filesize)

            if not agenthealth.canStopAggressiveGC(packageMount):
                if (time.time() > filedate + lower_age_bound):
                    try:
                        GCLOG.info('Force garbage collecting package(%s)' % filename)
                        os.remove(filename)
                        if os.path.exists(filename + '.prop'):
                            os.remove(filename + '.prop')
                        if os.path.exists(filename + '.torrent'):
                            os.remove(filename + '.torrent')
                        if os.path.exists(filename + '.inprogress'):
                            os.remove(filename + '.inprogress')
                    except OSError, osErr:
                        GCLOG.error('Unable to garbage collect %s - %s' % (filename, osErr))
        GCLOG.debug('Force garbage collecting downloaded packages completed')

    @staticmethod
    def cleanRogueService():
        """ delete rogue services """
        GCLOG.debug('cleanRogueServices')
        try:
            services = manifestutil.getServices()
            for service in services:
                path = manifestutil.servicePath(service)
                for idx in range(3):
                    if os.path.exists(os.path.join(path, 'manifests')):
                        break
                    time.sleep(2)
                    if idx == 2:
                        appGlobal = pylons.config['pylons.app_globals']
                        GCLOG.info('service %s does not have manifests folder, cleanup the rogue service' % service)
                        deleteThread = ServiceDelete(appGlobal.threadMgr, service, path)
                        deleteThread.run()
                        GCLOG.info('Rogue service %s cleaned up' % service)
                        break
        except Exception:
            GCLOG.error('failed to check and cleanup rogue service' + traceback.format_exc(5))            


    @staticmethod
    def cleanPastActivatedManifests():
        """ delete past activated manifests not needed any more """
        GCLOG.debug('cleanPastActivatedManifest')
        manifest_keep = configutil.getConfigAsInt('keep_past_manifests')
        for service in manifestutil.getServices():
            past_manifests = serviceutil.getActivatedManifestList(service)
            if len(past_manifests) > manifest_keep:
                manifests_to_delete = past_manifests[manifest_keep:]
                for manifest_to_delete in manifests_to_delete:
                    appGlobal = pylons.config['pylons.app_globals']
                    dThread = ManifestDelete(appGlobal.threadMgr, service, manifest_to_delete) 
                    dThread.run()
                    GCLOG.info('Past manifest %s - %s cleaned up' % (service, manifest_to_delete))
