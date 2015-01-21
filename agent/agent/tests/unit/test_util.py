from agent.tests import *

import json
import pylons
import os
import shutil
import logging
import time

from agent.lib.agent_globals import stopAgentGlobals
from agent.lib.agent_globals import startAgentGlobals
from agent.lib.utils import readlink, islink

from agent.controllers.service import ServiceController
from agent.lib import utils
from agent.lib.package import PackageUtil

LOG = logging.getLogger(__name__)


def removeAgentRoot():
    agentRoot = pylons.config['agent_root']
    assert (agentRoot != None and pylons.config['agent_root'] != '/')
    file_stat = os.stat(agentRoot)
    assert file_stat.st_uid == os.getuid(), 'Agent root dir %s owner mismatch ' % os.path.abspath(agentRoot)
    cmd = utils.sudoCmd('rm -r %s' % pylons.config['agent_root'])
    os.system(cmd)
    return True


def commonSetup():
    stopAgentGlobals()

    if removeAgentRoot() and not os.path.exists(pylons.config['agent_root']):
        os.mkdir(pylons.config['agent_root'])

    assert os.path.exists(pylons.config['agent_root'])
    startAgentGlobals(startAgentMonitor = False, startPackageMgr = False)

def commonTearDown():
    stopAgentGlobals()

    if removeAgentRoot() and not os.path.exists(pylons.config['agent_root']):
        os.mkdir(pylons.config['agent_root'])
        
def mockDownloadPkg(pkgUri):
    """ mock download a cronus package """
    pkgDict = PackageUtil.parseUri(pkgUri)
    pkgName = pkgDict['package']
    localPkgRoot = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'packages')
    src = os.path.join(localPkgRoot, pkgName)
    shutil.copy(src, pkgDict['packagePath'])
    #propPkgName = pkgDict['propName']
    #propSrc = os.path.join(localPkgRoot, propPkgName)
    #shutil.copy(propSrc, pkgDict['propPath'])

def createManifest(testController,
                   packages = ['http://github.com/yubin154/cronusagent/blob/master/agent/agent/tests/unit/packages/perlserver-1.0.0.unix.cronus'],
                   manifest = 'bar', service = 'foo', createDirs = True):
    try:
        path = ServiceController.servicePath(service)
        os.makedirs(os.path.join(path, 'manifests'))
        os.makedirs(os.path.join(path, 'modules'))
        os.makedirs(os.path.join(path, '.appdata'))
        os.makedirs(os.path.join(path, '.data'))
        
        path = ServiceController.installedPkgPath(service)
        os.makedirs(path)
    except Exception as excep:
        LOG.warning('got an OS Exception - %s' % str(excep))


    try:
        for pkgUri in packages:
            mockDownloadPkg(pkgUri)
#             pkgDict = PackageUtil.parseUri(pkgUri)
#             pkgName = pkgDict['package']
#             localPkgRoot = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'packages')
#             src = os.path.join(localPkgRoot, pkgName)
#             shutil.copy(src, pkgDict['packagePath'])
#             propPkgName = pkgDict['propName']
#             propSrc = os.path.join(localPkgRoot, propPkgName)
#             shutil.copy(propSrc, pkgDict['propPath'])
    except Exception as excep:
        LOG.warning('got an OS Exception - %s' % str(excep))
        
    body = json.dumps({'package' : packages})
    response = testController.app.post(url(controller = 'manifest', action = 'post', service = service, manifest = manifest),
                             headers = {'Content-Type' : 'application/json'},
                             params = body)
    assert response.status_int == 200, 'Manifest Post assert'

    LOG.debug('response body = %s' % response.body)

    body = json.loads(response.body)

    # wait until the status is done
    tm = time.time()
    now = tm
    while (tm + 120 > now):
        response = testController.app.get(body['status'])
        body = json.loads(response.body)

        LOG.debug("createManifest  ********** progress = %s" % body['progress'])
        if (int(body['progress']) == 100):
            break
        time.sleep(0.1)
        now = time.time()

    assert tm + 120 >= now, 'Create manifest timed out'
    LOG.debug('status = ' + str(response.status_int))
    assert response.status_int == 200, "HTTP response != 200"
    LOG.debug ('Status response body = %s' % str(body))
    assert int(body['progress']) == 100

def activateManifest(testController, manifest = 'bar', service = 'foo'):

    body = json.dumps({'manifest':manifest})

    response = testController.app.post(url(controller = 'manifest', action = 'activate', service = service, manifest = manifest),
                                       headers = {'Content-Type' : 'application/json'},
                                       params = body)

    assert response.status_int == 200, 'Action get assert'

    body = json.loads(response.body)

    tm = time.time()
    while (tm + 120 > time.time()):
        response = testController.app.get(body['status'])
        body = json.loads(response.body)

        LOG.debug("activateManifest ********** progress = %s" % body['progress'])
        if (int(body['progress']) == 100):
            break
        time.sleep(0.1)

    LOG.debug('status = ' + str(response.status_int))
    assert response.status_int == 200, "HTTP response != 200"
    LOG.debug ('Status response body = %s' % str(body))
    assert body['progress'] == 100

    # let's make sure the link is there correctly
    activePath = os.path.join(ServiceController.manifestPath(service), 'active')
    LOG.debug ('active path = ' + activePath)
    assert islink(activePath)

    link = readlink(activePath)
    LOG.debug ('link = ' + link)
    assert link == manifest

def checkStatus(testController, cmd, response, timeout = 20):
    try:
        body = json.loads(response.body)
    except Exception:
        raise
    tm = time.time()
    while (tm + timeout > time.time()):
        response = testController.app.get(body['status'])
        body = json.loads(response.body)

        LOG.debug("%s ********** progress = %s" % (cmd, body['progress']))
        if (int(body['progress']) == 100):
            break
        time.sleep(0.1)
        LOG.debug("=======123==========")
        """
        when this is uncommented - the exception msg does not appear for urlgrabber! which is weird!
        try:
            response = testController.app.get(body['status'])
            body = json.loads(response.body)

            LOG.debug("%s ********** progress = %s" % (cmd, body['progress']))
            if (int(body['progress']) == 100):
                break
    except Exception as excp:
        LOG.debug('error')
        LOG.debug(excp)
        """

    LOG.debug('status = ' + str(response.status_int))
    assert response.status_int == 200, "HTTP response != 200"
    LOG.debug ('Status response body = %s' % str(body))
    testController.assertEquals(body['progress'], 100)

def ensureCompletion(testController, cmd, response, timeout = 20, expect_errors = False, err_code = None):
    try:
        body = json.loads(response.body)
    except Exception:
        raise
    tm = time.time()
    while (tm + timeout > time.time()):
        response = testController.app.get(body['status'], expect_errors = expect_errors)
        body = json.loads(response.body)
        if expect_errors:
            if (response.status_int == 500):
                if err_code:
                    actual = int(body['error']) if body.has_key('error') else 0
                    if(actual == err_code):
                        break
                    else:
                        testController.fail('API invocation failed as expected(HTTPStatus:500) but err code absence/mismatch: expected: %s, actual: %s' % (err_code, actual))
                break
        elif (int(body['progress']) == 100):
            break
        time.sleep(0.1)
    time.sleep(0.1)
    LOG.debug('status = ' + str(response.status_int))
    LOG.debug ('Status response body = %s' % str(body))

def restartService(testController, service = 'foo'):

    response = testController.app.post(url(controller = 'action', action = 'restart', service = service),
                                       headers = {'Content-Type' : 'application/json'})

    assert response.status_int == 200, 'Action get assert'

    body = json.loads(response.body)

    tm = time.time()
    while (tm + 120 > time.time()):
        response = testController.app.get(body['status'])
        body = json.loads(response.body)

        LOG.debug("service restart ********** progress = %s" % body['progress'])
        if (int(body['progress']) == 100):
            break
        time.sleep(0.1)

    LOG.debug('status = ' + str(response.status_int))
    assert response.status_int == 200, "HTTP response != 200"
    LOG.debug ('Status response body = %s' % str(body))
    assert body['progress'] == 100

def startService(testController, service = 'foo'):

    response = testController.app.post('/services/%s/action/startup' % service,
                                       headers = {'Content-Type' : 'application/json'})

    assert response.status_int == 200, 'Action get assert'

    body = json.loads(response.body)

    tm = time.time()
    while (tm + 120 > time.time()):
        response = testController.app.get(body['status'])
        body = json.loads(response.body)

        LOG.debug("service restart ********** progress = %s" % body['progress'])
        if (int(body['progress']) == 100):
            break
        time.sleep(0.1)

    LOG.debug('status = ' + str(response.status_int))
    assert response.status_int == 200, "HTTP response != 200"
    LOG.debug ('Status response body = %s' % str(body))
    assert body['progress'] == 100

def shutdownService(testController, service = 'foo'):

    response = testController.app.post('/services/%s/action/shutdown' % service,
                                       headers = {'Content-Type' : 'application/json'})

    assert response.status_int == 200, 'Action get assert'

    body = json.loads(response.body)

    tm = time.time()
    while (tm + 120 > time.time()):
        response = testController.app.get(body['status'])
        body = json.loads(response.body)

        LOG.debug("service restart ********** progress = %s" % body['progress'])
        if (int(body['progress']) == 100):
            break
        time.sleep(0.1)

    LOG.debug('status = ' + str(response.status_int))
    assert response.status_int == 200, "HTTP response != 200"
    LOG.debug ('Status response body = %s' % str(body))
    assert body['progress'] == 100

def deactivateManifest(testController, manifest = 'bar', service = 'foo'):

    response = testController.app.post(url(controller = 'action', action = 'deactivatemanifest', service = service),
                                       headers = {'Content-Type' : 'application/json'})

    assert response.status_int == 200, 'Action get assert'

    body = json.loads(response.body)

    tm = time.time()
    while (tm + 120 > time.time()):
        response = testController.app.get(body['status'])
        body = json.loads(response.body)

        LOG.debug("service restart ********** progress = %s" % body['progress'])
        if (int(body['progress']) == 100):
            break
        time.sleep(0.1)

    LOG.debug('status = ' + str(response.status_int))
    assert response.status_int == 200, "HTTP response != 200"
    LOG.debug ('Status response body = %s' % str(body))
    assert body['progress'] == 100


def createService(testController, service = 'foo'):

    response = testController.app.post(url(controller = 'service', action = 'post', service = service),
                                       headers = {'Content-Type' : 'application/json'})

    assert response.status_int == 200, 'Action get assert'

    body = json.loads(response.body)

    tm = time.time()
    while (tm + 120 > time.time()):
        response = testController.app.get(body['status'])
        body = json.loads(response.body)

        LOG.debug("service restart ********** progress = %s" % body['progress'])
        if (int(body['progress']) == 100):
            break
        time.sleep(0.1)

    LOG.debug('status = ' + str(response.status_int))
    assert response.status_int == 200, "HTTP response != 200"
    LOG.debug ('Status response body = %s' % str(body))
    assert body['progress'] == 100
    
    
def configPoke(testController, configs):

    body = json.dumps({'configs': configs if configs else None}) 

    response = testController.app.post(url(controller = 'action', action = 'pokeConfig'),
                                       headers = {'Content-Type' : 'application/json'},
                                       params = body)

    assert response.status_int == 200, 'Action get assert'
    

