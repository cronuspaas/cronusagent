#pylint: disable=R0911,W0105
""" access application logs """
from agent.lib.utils import trackable
try:
    import json
except ImportError:
    import simplejson as json
from pylons import request, response
from pylons import tmpl_context as c
from agent.lib.base import BaseController
from agent.lib.filehelper import viewFile, downloadFile
from agent.lib.manifestutil import PkgInitConfig, serviceRootPath, packagePath, packagesInManifest, getServices, manifestPath, getManifests, manifestRootPath
from agent.lib.errors import Errors
from pylons.templating import render_mako as render
import os, time
import logging

LOG = logging.getLogger(__name__)

class ApplogController(BaseController):
    """ Controlling display of application logs """
    
    def __init__(self):
        """ constructor  """
        super(ApplogController, self).__init__()

    @trackable()
    def listServices(self):
        """ list services """
        packageList = getServices()
        return ApplogController.prepareOutput(
                        packageList, 
                        "/applog/packages?service=", 
                        serviceRootPath(), 
                        "List Of Services")

    @trackable()
    def listManifests(self):
        """ list manifests """
        service = request.params.get('service', '')

        if (service == ''):
            c.errorMsg = 'missing service or package parameter from request'
            c.errorCode = Errors.LOG_PARAM_REQUIRED
            return render('/derived/error.html')

        packageList = getManifests(service)
        return ApplogController.prepareOutput(
                        packageList, 
                        "/applog/packages?service=" + service + "&manifest=", 
                        manifestRootPath(service), 
                        "List Of Manifests")


    @trackable()
    def listPackages(self):
        """ list packages """
        service = request.params.get('service', '')
        package = request.params.get('package', '')
        manifest = request.params.get('manifest', 'active')
        
        if (service == ''):
            c.errorMsg = 'missing service parameter from request'
            c.errorCode = Errors.LOG_PARAM_REQUIRED
            return render('/derived/error.html')
        
        if (package != ''):
            return ApplogController.doAppLogFile()
        
        if (not os.path.isdir(manifestPath(service, manifest))):
            return self.listManifests()
        
        packageList = packagesInManifest(service, manifest)
        return ApplogController.prepareOutput(
                        packageList, 
                        "/applog/applog?service=%s&manifest=%s&package=" % (service, manifest), 
                        manifestPath(service, manifest), 
                        "List Of Packages")


    @trackable()
    def listAppLog(self):
        """ listAppLog """
        return ApplogController.doAppLogFile()

    @staticmethod
    def prepareOutput(fileList, urlPath, absolutePath, message):
        """ prepareOutput """
        fullLogList = []
        for fileName in fileList:
            logList = []
            logList.append(urlPath + fileName)
            logList.append(fileName)
            logList.append("/images/folder.png")
            logList.append(time.ctime(os.path.getmtime(os.path.join(absolutePath, fileName))))
            fileSize = os.path.getsize(os.path.join(absolutePath, fileName))
            logList.append("" + str(fileSize / 1024) + " KB")
            fullLogList.append(logList)
            
        LOG.info("fullLogLis %s" % fullLogList)
        c.status = fullLogList
        c.message = message
        c.absolutePath = absolutePath
        c.menuTab = 'MENU_TAB_APPLOGS'
        return render('/derived/appLogDirectory.html')

    @staticmethod
    def doAppLogFile():
        """ listAppLog """
        service = request.params.get('service', '')
        package = request.params.get('package', '')
        manifest = request.params.get('manifest', 'active')

        if (service == '' or package == ''):
            c.errorMsg = 'Missing service or package from request'
            c.errorCode = Errors.LOG_PARAM_REQUIRED
            return render('/derived/error.html')
        
        packagePathStr = packagePath(service, manifest, package)
        if (not os.path.isdir(packagePathStr)):
            c.errorMsg = 'Invalid service, manifest, or package from request'
            c.errorCode = Errors.LOG_PARAM_REQUIRED
            return render('/derived/error.html')
        
        LOG.debug('In ApplogController doAppLogFile ' + packagePathStr)
        pkgPath = packagePath(service, manifest, package)
        pkgInit = PkgInitConfig(pkgPath)
        logDirList = pkgInit.getConfig(PkgInitConfig.KEY_LOGDIRS)
        if not logDirList:
            c.errorMsg = 'No cronus.ini in package, please check your cronus package to make sure cronus.ini exist and have property logDirs'
            c.errorCode = Errors.CRONUS_INI_EMPTY_NOT_FOUND
            return render('/derived/error.html')
        
        dirName = request.params.get('dirName', '')
        fileName = request.params.get('fileName', '')

        if (fileName != '' and dirName != ''):
            dirName = os.path.join(dirName, fileName)

        if (dirName != ''):
            return ApplogController.listAppLogDir(service, 
                                                     manifest, 
                                                     package, 
                                                     dirName, 
                                                     os.path.join(packagePathStr, dirName))
        
        else:
            return ApplogController.listAllAppLogDir(service, 
                                                        manifest, 
                                                        package, 
                                                        dirName, 
                                                        packagePathStr, 
                                                        logDirList)

    @staticmethod
    def listAppLogDir(service, manifest, package, shortDirName, dirName):
        """ listAppLogDir """
        LOG.debug('In ApplogController dirName ' + dirName)
        contentType = request.environ['CONTENT_TYPE']
        if (not os.path.exists(dirName)):
            c.errorMsg = 'App Log directory (%s) missing' % (dirName)
            c.errorCode = Errors.LOG_APP_DIR_NOT_FOUND
            return render('/derived/error.html')

        if (os.path.isfile(dirName)):
            if contentType == 'text/plain':
                return downloadFile(dirName)
            else:
                return viewFile(dirName)
        
        if (os.path.isdir(dirName)):
            logList = os.listdir(dirName)
            if contentType == 'application/json':
                return ApplogController.doJSonStr(logList)
            else:
                fullLogList = []
                for fileName in logList:
                    logList = ApplogController.getAppLogEntryHtml(
                                    service, manifest, package, shortDirName, dirName, fileName)
                    fullLogList.append(logList)
                
                c.status = fullLogList
                c.message = "List Of Files/Directories" + ""
                c.absolutePath = dirName
                c.menuTab = 'MENU_TAB_APPLOGS'

                return render('/derived/appLogDirectory.html')

    @staticmethod
    def listAllAppLogDir(service, manifest, package, shortDirName, packagePathStr, appLogDirList):
        """ listAllAppLogDir """
        if (len(appLogDirList) < 1):
            c.errorMsg = 'Could not find logDirs config values in config file %s' % (appLogDirList)
            c.errorCode = Errors.LOG_APP_DIR_CONFIG_MISSING
            return render('/derived/error.html')
        
        for fileName in appLogDirList:
            if (not os.path.exists(os.path.join(packagePathStr, fileName))):
                c.errorMsg = 'App Log directory (%s) missing' % (fileName)
                c.errorCode = Errors.LOG_APP_DIR_NOT_FOUND
                return render('/derived/error.html')
        
        if (request.environ['CONTENT_TYPE'] == 'application/json'):
            return ApplogController.doJSonStr(appLogDirList)
        
        else:
            fullLogList = []
            for fileName in appLogDirList:
                logList = ApplogController.getAppLogEntryHtml(
                            service, manifest, package, shortDirName, packagePathStr, fileName)
                fullLogList.append(logList)
            
            c.status = fullLogList
            c.message = "List Of Files/Directories"
            c.absolutePath = packagePathStr
            c.menuTab = 'MENU_TAB_APPLOGS'
            
            return render('/derived/appLogDirectory.html')

    @staticmethod
    def getAppLogEntryHtml(service, manifest, package, shortDirName, dirName, fileName=None):
        """ generate html for one log entry """
        fileStr = ''
        fileImg = ''
        logList = []
        if (os.path.isdir(os.path.join(dirName, fileName))):
            fileStr = ("?service=%s&manifest=%s&package=%s&dirName=%s" % 
                       (service, manifest, package, os.path.join(shortDirName, fileName)))
            fileImg = "/images/folder.png"
        else:
            fileStr = ("?service=%s&manifest=%s&package=%s&dirName=%s&fileName=%s" % 
                       (service, manifest, package, shortDirName, fileName))
            fileImg = "/images/notepad.bmp"
                        
        logList.append(fileStr)
        logList.append(fileName)
        logList.append(fileImg)
        logList.append(time.ctime(os.path.getmtime(os.path.join(dirName, fileName))))
        fileSize = os.path.getsize(os.path.join(dirName, fileName))
        logList.append("" + str(fileSize / 1024) + " KB")
        return logList
    
    
    @staticmethod
    def doJSonStr(fileList):
        """ doJSonStr """
        response.content_type = 'application/json'
        fileHash = []
        dirHash = []
        appHash = {}
        mainHash = {}
        appHash['FileLogEntries'] = fileHash
        appHash['DirLogEntries'] = dirHash
        mainHash['ApplicationLog'] = appHash
        for fileName in fileList:
            if (os.path.isdir(fileName)):
                fileHash.append(fileName)
            else:
                dirHash.append(fileName)
        return json.dumps(mainHash)

