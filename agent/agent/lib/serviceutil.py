'''
Created on Jun 26, 2014

@author: binyu
'''
from agent.lib import utils, manifestutil, configutil
import logging
import os
from agent.lib.errors import AgentException, Errors
from agent.lib.manifestutil import readNestedServiceMeta
import json

LOG = logging.getLogger(__name__)

LCM_META = 'lcm_meta'
KEY_DAEMON = 'daemon'
KEY_ENV = 'env'
KEY_ACTIVATEDMANIFESTS = 'activated_manifests'

DAEMON_UPSTART = 'upstart'
DAEMON_SYSTEMD = 'systemd'

def createServiceIfNeeded(service):
    """ check service existence and create service if not alrady exist """
    spath = manifestutil.servicePath(service)
    if not os.path.exists(spath):
        os.makedirs(spath)
        os.makedirs(os.path.join(spath, 'manifests'))
        os.makedirs(os.path.join(spath, 'installed-packages'))
        os.makedirs(os.path.join(spath, 'modules'))
        os.makedirs(os.path.join(spath, 'downloaded-packages'))
        os.makedirs(os.path.join(spath, '.appdata'))
        os.makedirs(os.path.join(spath, '.data'))
        
        uname = configutil.getAppUser()
        uid, gid = utils.getUidGid(uname)
        utils.rchown(os.path.join(spath, '.appdata'), uid, gid)

    # verify that the path exists
    if (not os.path.isdir(spath)):
        raise AgentException(Errors.UNKNOWN_ERROR, "Service(%s) was not created" % service)

def isDaemonServiceWisb(service):
    """ this service is requested to be run as deamon """
    daemonService = readNestedServiceMeta(service, '%s.%s' % (LCM_META, KEY_DAEMON), None)
    return (daemonService!=None, daemonService)

def isDaemonServiceWiri(service):
    """ this service has an daemon service defined (upstart or systemd)
    """
    daemonWisb, daemonService = isDaemonServiceWisb(service)
    if daemonWisb:
        if (daemonService==DAEMON_UPSTART and 
            os.path.exists(os.path.join('/etc/init/%s.conf' % service))):
            return (True, DAEMON_UPSTART)
        elif (daemonService==DAEMON_SYSTEMD and 
              os.path.exists(os.path.join('/etc/systemd/system/multi-user.target.wants/%s.service' % service))):
            return (True, DAEMON_SYSTEMD)
    
    return (False, None)
    
def setDaemonServiceWisb(service, daemonType):
    """ set upstart service name to .metadata.json """
    manifestutil.updateServiceCatMeta(service, LCM_META, {KEY_DAEMON: daemonType})

def getEnv(service):
    """ read env value from .metadata.json, 
        the value is set by create service post request 
    """
    return manifestutil.readNestedServiceMeta(service, '%s.%s' % (LCM_META, KEY_ENV))

def setEnv(service, env):
    """ set env value from post request to .metadata.json """
    manifestutil.updateServiceCatMeta(service, LCM_META, {KEY_ENV: env})
    
def updateLcmMeta(service, metas):
    """ save lcm metas to .metadata.json """
    manifestutil.updateServiceCatMeta(service, LCM_META, metas)
    
def getLcmMetas(service):
    """ all lcm metas as dict """
    lcmMetas = manifestutil.readJsonServiceMeta(service, [LCM_META])
    if lcmMetas and lcmMetas[LCM_META] and type(lcmMetas[LCM_META])==dict:
        return lcmMetas[LCM_META]    

def addActivatedManifestList(service, activated_manifest):
    """ update .metadata.json for past activated manifest list
        called after a manifest is activated
    """
    activated_manifests = readNestedServiceMeta(service, KEY_ACTIVATEDMANIFESTS, [])
    if activated_manifest in activated_manifests:
        activated_manifests.remove(activated_manifest)
    activated_manifests.insert(0, activated_manifest)
    manifestutil.updateServiceCatMeta(service, KEY_ACTIVATEDMANIFESTS, activated_manifests)
    
def removeActivatedManifestList(service, manifest):
    """ remove manifest from past activated manifest list
        called when manifest is deleted
    """
    activated_manifests = readNestedServiceMeta(service, KEY_ACTIVATEDMANIFESTS, [])
    if manifest in activated_manifests:
        activated_manifests.remove(manifest)
    manifestutil.updateServiceCatMeta(service, KEY_ACTIVATEDMANIFESTS, activated_manifests)

def getActivatedManifestList(service):
    """ retrieve activated manifest list """
    return readNestedServiceMeta(service, KEY_ACTIVATEDMANIFESTS, [])

def getPastManifest(service, idx):
    """ retrieve past active manifest of idx """
    pastManifests = getActivatedManifestList(service)
    activeManifest = manifestutil.getActiveManifest(service)
    if pastManifests and pastManifests[idx] and pastManifests[idx] != activeManifest:
        return pastManifests[idx]
    else:
        return None

def getServiceSummary():
    """ service summary """
    services_data = []
    for service in manifestutil.getServices():
        service_data = {}
        service_data['serviceName'] = service
        service_data['manifests'] = ','.join(manifestutil.getManifests(service))
        if manifestutil.hasActiveManifest(service):
            service_data['activeManifest'] = manifestutil.getActiveManifest(service)
            service_data['activePackages'] = ','.join(manifestutil.packagesInManifest(service))
        else:
            service_data['activeManifest'] = 'n/a'
            service_data['activePackages'] = 'n/a'            
        service_data['serviceMeta'] = json.dumps(manifestutil.readJsonServiceMeta(service))
        services_data.append(service_data)
    return services_data
        

    