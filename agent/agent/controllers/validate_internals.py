# pylint: disable=R0914,R0912,R0904,C0103,W0105
""" agent validate internals """
from agent.lib.packagemgr import PackageMgr
from agent.lib.base import BaseController
from pylons import config, response, tmpl_context as c
from pylons.templating import render_mako as render
import httplib
import json
import logging
import os
from agent.lib.filehelper import plaintext2html

LOG = logging.getLogger(__name__)


def getConfigFile():
    """ get config """
    return config['app_conf']

def getConfigFileFiltered():
    """ get filtered config """
    sanitized_configs = {}
    sanitized_configs.update(config['app_conf'])
    import re
    for k, v in sanitized_configs.items():
        if not re.search('^(-?[0-9]+|true|false)$', v, re.IGNORECASE):
            del sanitized_configs[k]
    return sanitized_configs
    

class ValidateInternalsController(BaseController):
    """ ValidateInternal Controller Class """
    def __init__(self):
        """ constructor  """
        super(ValidateInternalsController, self).__init__()
        
    @staticmethod
    def sendHttpRequest( httpRequest ):
        """ get http content """
        connection = None
        
        #host, port, protocol, url, httpMethod 
        if (httpRequest == None):
            print "NullPointer of httpRequest is null"
        status, error, errorMessage, httpResponse, httpResponseMessage = None, None, None, None, None
        
        try:
            #print "Now send HTTP request with URL: " + httpRequest.url
            if 'https' == httpRequest.protocol:
                connection = httplib.HTTPSConnection(httpRequest.host, httpRequest.port)
            else:
                connection = httplib.HTTPConnection(httpRequest.host, httpRequest.port)
            
            if httpRequest.headers is None:
                connection.request(httpRequest.httpMethod, httpRequest.urlPostfix)
            else:
                connection.request(httpRequest.httpMethod, httpRequest.urlPostfix, httpRequest.body, httpRequest.headers)
            httpResponse = connection.getresponse()
            status = httpResponse.status
            if status >= 200 and status < 300:
                httpResponseMessage = httpResponse.read()
            else:
                errorMessage = httpResponse.reason
        except IOError, exception:
            errorMessage = 'Error during sendHttpRequest - %s' % (str(exception))
        finally:
            if connection is not None:
                connection.close()
                
        return status, httpResponseMessage, error, errorMessage
    
    def getInfo(self, isHtml):
        """ generate info """
        appGlobal = config['pylons.app_globals']
        if 'True' == isHtml:
            c.status = appGlobal.metrixManager.getStatus()
            menuTab = "MENU_TAB_VI"
            c.menuTab = menuTab
            for _, vval in c.status:
                if not vval:
                    continue
                
            return render('/derived/validateInternals.html')
        else:
            response.content_type = 'application/json'
            return appGlobal.metrixManager.getJsonStatus()
    
    def getLogDirectory(self):
        """ show log directory """
        logList = os.listdir('logs')
        for fileName in logList:
            if '.log' not in fileName:
                logList.remove(fileName)
        c.content = logList
        
        menuTab = "MENU_TAB_LOGS"
        c.menuTab = menuTab        
        return render('/derived/logDirectory.html')

    def getPkgUploadPage(self):
        """ show existing packages in packages folder """
        pkgs = [ os.path.basename(packageDir) for packageDir in os.listdir(PackageMgr.packagePath()) ]
        c.content = pkgs
        
        menuTab = "MENU_TAB_PKGS"
        c.menuTab = menuTab        
        return render('/derived/pkgUpload.html')

    def getLogFile(self, fileName):
        """ show log file """
        logFile = open('logs/' + fileName, 'r')
        logData = logFile.read()
        logFile.close()
        return plaintext2html(logData)

    def getAgentHealth(self):
        """ generate agent health REST response """
        appGlobal = config['pylons.app_globals']
        status = appGlobal.metrixManager.getStatus()
        result = []
        for key, value in status:
            if 'Health' == key:
                result.append({'key': 'health', 'value': value})
            elif 'HealthFactor' == key and type(value) is dict:
                subres = []
                for key1, value1 in value.items():
                    subres.append('%s=%s' % (key1, value1))
                result.append({'key': 'healthFactor', 'value': ','.join(subres)})                    

        response.content_type = 'application/json'
        return json.dumps(result)

    def getMonitors(self):
        """ show all monitor values available """
        appGlobal = config['pylons.app_globals']
        response.content_type = 'application/json'
        result = appGlobal.agentMonitor.dumpMonitorValues() if appGlobal is not None else {}
        return json.dumps(result)


    def getThreads(self):
        """ show all threads """
        appGlobal = config['pylons.app_globals']
        response.content_type = 'application/json'
        result = appGlobal.threadMgr.getInfo() if appGlobal is not None else {}
        return json.dumps(result)

    
