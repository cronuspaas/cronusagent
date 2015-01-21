#pylint: disable=E1101,W0703,W0212,W0232, R0914,R0915,W0105
"""
Package.py

Class to handle the downloading of the package
"""

import urlparse
import re
import json
import os
import fnmatch
from agent.lib.utils import md5sum
from agent.lib.errors import Errors, PackagePathError, PackageScriptNotFound
from agent.lib.errors import AgentException

import logging
import pylons
from agent.lib.agent_thread.exec_thread import ExecThread
from agent.lib.contextutils import copycontexts
from agent.lib import utils, configutil

LOG = logging.getLogger("gc")

class PackageControl:
    '''
    abstraction for package that allows interaction with the package
    '''
    SCRIPT_PATH = os.path.join('cronus', 'scripts')

    def __init__(self, packagePath, threadMgr):
        '''
        constructor
        @param packagePath:    path to package
        @param threadMgr:      thread manager to execute package scripts
        '''
        if not os.path.isdir(packagePath):
            raise PackagePathError("package path '%s' not found" % packagePath)

        self.__packagePath = packagePath
        self.__threadMgr = threadMgr

        self.__userName = configutil.getAppUser()

    def __scriptPath(self, script):
        '''
        @param script: script name
        @return: path to script
        '''
        return os.path.join(self.__packagePath, PackageControl.SCRIPT_PATH, script)

    def hasScript(self, script):
        '''
        @param script: script name
        @return: True iff packagePath/cronus/scripts/script exists and is a file
        '''
        return os.path.isfile(self.__scriptPath(script))

    def runScript(self, script, timeout, progressTimeout):
        '''
        @param script: script name
        @param timeout: total script timeout
        @param progressTimeout: progress timeout
        @return: ExecThread instance
        @throws PackageScriptNotFound: if script does not exist
        '''
        if not self.hasScript(script):
            raise PackageScriptNotFound('missing package script: ' + self.__scriptPath(script))

        cmd = utils.sudoCmd([], self.__userName) if self.__userName else []
        cmd.append(self.__scriptPath(script))
        execThread = ExecThread(self.__threadMgr, cmd)
        execThread.setTimeout(timeout)
        execThread.setProgressTimeout(progressTimeout)
        copycontexts(self, execThread, ['guid', 'service'])
        execThread.start()

        return execThread

class PackageUtil:
    ''' Util functions '''

    nameRe = re.compile('((([a-zA-Z0-9_]+)-(([0-9]+)\.([0-9]+)\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)))\.cronus)')
    inProgressExt = '.inprogress'

    @staticmethod
    def validateDownload(obj, *args, **kwargs):
        """ used by urlgrabber to check the files """

        if (obj.filename.rpartition('.')[2] == 'prop'):
            if (PackageUtil.validateProp(obj.filename) == False):
                raise AgentException(Errors.INVALID_PACKAGE, 'Package prop (%s) not valid' % obj.filename)
            return

        # figure the prop file name from the filename
        if (obj.filename.rpartition('.')[2] == 'inprogress'):
            propFilename = obj.filename.rpartition('.')[0] + '.prop'
        else:
            propFilename = obj.filename + '.prop'

        if (PackageUtil.validatePackage(obj.filename, propFilename) == False):
            raise AgentException(Errors.INVALID_PACKAGE, 'Package (%s) not valid' % obj.filename)

    @staticmethod
    def validateProp(filename):
        """ checks that the properties file is correct
        return a boolean"""

        # does the file exists
        if (not os.path.exists(filename)):
            LOG.warning('Prop file (%s) does not exist' % (filename))
            return False

        # can I read it
        try:
            propFile = open(filename, 'r')
            prop = json.load(propFile)
            propFile.close()
        except (ValueError, OSError):
            LOG.warning('Prop file (%s) unable to read or did not parse' % (filename))
            return False

        # does the prop have the correct value
        for key in ('name', 'md5', 'description', 'size', 'contact'):
            if (key not in prop):
                LOG.warning('Prop file (%s) missing key (%s)' % (filename, key))
                return False

        return True


    @staticmethod
    def validatePackage(filename, propFilename = None):
        """ validate the package
        returns True or False """

        if (propFilename == None):
            propFilename = filename + '.prop'

        if (not PackageUtil.validateProp(propFilename)):
            return False

        try:
            # check that the file exists
            if (not os.path.exists(filename)):
                LOG.warning('Package (%s) does not exists' % (filename))
                return False

            # load in the prop file
            propFile = open(propFilename, 'r')
            prop = json.load(propFile)
            propFile.close()

            size = os.path.getsize(filename)
            if (size != int(prop['size'])):
                LOG.warning('package size = %s : %s' % (str(size), str(prop['size'])))
                return False

            md5Sum = md5sum(filename)
            propmd5 = prop['md5']
            if (md5Sum != propmd5):
                LOG.warning('package md5 = %s : %s' % (md5Sum, prop['md5']))
                return False

            # make sure the tar file has the expected structure
            # TPY to do after we fix the cronus-deploy

        except Exception, excep:
            LOG.error('validatePackage exception %s' % excep)
            return False

        return True
    
    @staticmethod
    def getPackageKey(packageUri):
        """ parse uri and get uniquely identifier of the package """
        uriDict = PackageUtil.parseUri(packageUri)
        return uriDict['package']
    
    @staticmethod
    def getPackageVersion(packageUri):
        """ parse uri and get version number """
        uriDict = PackageUtil.parseUri(packageUri)
        return uriDict['packageVersion']

    @staticmethod
    def parseUri(packageUri, path = None, packageloc = None):
        """ static method to parse the uri
        @throws - AgentException
        """

        if (path == None):
            from agent.lib.packagemgr import PackageMgr
            path = PackageMgr.packagePath()

        uri = urlparse.urlparse(packageUri)

        if (uri.scheme != 'http'):
            raise AgentException(Errors.PACKAGE_SCHEME_ERROR,
                                 'uri (%s) scheme(%s) not supported' % (packageUri, uri.scheme))

        if (uri.path == ''):
            raise AgentException(Errors.PACKAGE_PATH_ERROR,
                                 'uri (%s) path is empty' % (packageUri))

        # now parse the path.  get the name and then verify that it matches the convention
        if packageloc is not None:
            packName = packageloc
        else:
            packName = uri.path.rpartition('/')[2]

        match = PackageUtil.nameRe.match(packName)
        if (match == None or match.group(0) != packName):
            raise AgentException(Errors.PACKAGE_PATH_ERROR,
                                 'cannot find package name in path %s' % (uri.path))

        # ok now we can fill out the dictionary
        uriDict = {}
        uriDict['uri'] = packageUri
        uriDict['scheme'] = uri.scheme
        uriDict['uripath'] = uri.path
        uriDict['package'] = match.group(1)
        uriDict['packageNameVersion'] = match.group(2)
        uriDict['inProgressPackage'] = PackageUtil.inProgressPath(uriDict['package'])
        uriDict['packageName'] = match.group(3)
        uriDict['propName'] = uriDict['package'] + '.prop'
        uriDict['packageVersion'] = match.group(4)
        uriDict['packageVersionMajor'] = match.group(5)
        uriDict['packageVersionMinor'] = match.group(6)
        uriDict['packageVersionBuild'] = match.group(7)
        uriDict['packagePlat'] = match.group(8)

        # path specific attributes
        uriDict['packagePath'] = os.path.join(path, uriDict['package'])
        uriDict['inProgressPackagePath'] = os.path.join(path, uriDict['inProgressPackage'])
        uriDict['propPath'] = os.path.join(path, uriDict['propName'])

        # calculate prop url
        # append path with .prop - mons: leaving the below code in place in case we support other protocols in future
        uriScheme = uri.scheme
        if (uriScheme != "http"): #only use http to download .prop and .torrent files
            uriScheme = "http"

        uripath = uri.path

        propParseResult = urlparse.ParseResult(uriScheme, uri.netloc, uripath + '.prop',
                                               uri.params, uri.query, uri.fragment)
        propUri = urlparse.urlunparse(propParseResult)
        uriDict['propUri'] = propUri

        return uriDict

    @staticmethod
    def inProgressPath(packagePath):
        """ return the path to the inprogress name """
        return packagePath + PackageUtil.inProgressExt

    @staticmethod
    def isInProgressPath(packagePath):
        """ return whether a package in in progress or not """
        return packagePath.endswith(PackageUtil.inProgressExt)

    @staticmethod
    def cleanUpPackage(inProgressFilename, packageFilename, propFilename):
        """ attempt to remove all traces of this package """
        try:
            for filename in (inProgressFilename, packageFilename, propFilename):
                if (filename is not None and os.path.exists(filename)):
                    os.remove(filename)

        except OSError, osErr :
            LOG.error('Unable to cleanup Package (%s)' % osErr)

    @staticmethod
    def getAllInstalledPackages(installedPkgPath):
        """returns the list of paths of all the packages in installed-packages folder
           expanding till the version level. e.g. pkgA-0.6.0.unix.cronus will have a
           pkgA and 0.6.0.unix as its child. This method returns paths till the version
           as a pkgA can have many versions as its children.
        """
        allPkgVers = []
        if os.path.exists(installedPkgPath):
            for pkg in os.listdir(installedPkgPath):
                pkgVersions = os.listdir(os.path.join(installedPkgPath, pkg))
                for pkgVersion in pkgVersions:
                    pkgPath = os.path.join(installedPkgPath, pkg)
                    if not fnmatch.fnmatch(pkgVersion, '*.inprogress'):
                        allPkgVers.append(os.path.join(pkgPath, pkgVersion))
        return allPkgVers

    @staticmethod
    def cleanupInstalledPkgs(installedPkgPath, orphanPkgs):
        '''removes folders under installed-packages which does not have
           any manifest reference'''
        from agent.lib.agent_thread.service_delete import ServiceDelete
        import time
        #import pdb; pdb.set_trace()
        for pkg in orphanPkgs:
            if (os.path.exists(pkg) and (time.time() > (os.path.getctime(pkg) + float(pylons.config['packageMgr_install_package_min_age'])))):
                parentPkg = os.path.dirname(pkg)
                try :
                    LOG.info('Garbage collecting folder contents of package %s' % pkg)
                    ServiceDelete.deleteFolderContents(pkg)
                    if os.listdir(parentPkg).__len__() <= 0:
                        ServiceDelete.deleteFolderContents(parentPkg)
                        LOG.info('attempting to delete folder contents of package %s' % parentPkg)
                except Exception as ex:
                    LOG.error('Unable to garbage collect %s - %s' % (pkg, ex))
            LOG.info('Completed cleanup Installed pkg %s' % pkg)

    @staticmethod
    def cleanupPackages(orphanpkgs):
        '''removes folders under installed-packages which does not have
           any manifest reference. Age is not a factor for cleanup. All orphans are cleaned-up


           Need to check for packages of interest(packages for which create is going on etc.
           '''
        from agent.lib.agent_thread.service_delete import ServiceDelete
        import time
        for pkg in orphanpkgs:
            LOG.debug('attempting to cleanup Installed pkg %s' % pkg)
            if (os.path.exists(pkg) and (time.time() > (os.path.getctime(pkg) + float(pylons.config['packageMgr_install_package_min_age'])))):
                parentPkg = os.path.dirname(pkg)
                try :
                    LOG.debug('attempting to delete folder contents of package %s' % pkg)
                    ServiceDelete.deleteFolderContents(pkg)
                    if os.listdir(parentPkg).__len__() <= 0:
                        ServiceDelete.deleteFolderContents(parentPkg)
                        LOG.debug('attempting to delete folder contents of package %s' % parentPkg)
                except Exception as ex:
                    LOG.error('Unable to garbage collect %s - %s' % (pkg, ex))

