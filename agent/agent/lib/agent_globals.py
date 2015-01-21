#pylint: disable=R0915, W0603, R0914, E1101, W0703, R0912,W0105
""" agent initialization, global values """
import pylons
from agent.lib.agent_thread.threadmgr import ThreadMgr
from agent.lib.packagemgr import PackageMgr

import logging
import os
from agent.lib import agenthealth, configutil
import threading
import signal
import uuid
from agent.lib.security import agentauth
from agent.controllers import validate_internals
from agent.controllers.module import ModuleController


LOG = logging.getLogger(__name__)

AGENT_HEALTH_VI_KEY = 'Health'
AGENT_HEALTH_FACTOR_VI_KEY = 'HealthFactor'
AGENT_INFO_KEY = 'AgentInfo'
OS_INFO_KEY = 'OSInfo'

def startAgentGlobals(startThreadMgr = True, startPackageMgr = True, startAgentMonitor = True):
    """
    Create and start the global objects
    """
    # cleanup incomplete manifests
    from agent.controllers.service import ServiceController
    ServiceController.cleanupServices()

    # stop the existing agents
    stopAgentGlobals()
    
    appGlobal = pylons.config['pylons.app_globals']

    # load config override from agent .metadata.json
    configutil.loadPylonConfig(pylons.config)
    configutil.loadConfigOverrides()
    configutil.loadSecureConfigOverrides()
    LOG.info("Complete loading config overrides")

    # build in memory security token cache
    appGlobal.authztoken = str(uuid.uuid4())
    appGlobal.encryptedtokens = {}
    agentauth.buildTokenCache(appGlobal.authztoken)
    LOG.info("Complete building security token cache")

    # agent health
    appGlobal.agentHealth = 'True'
    appGlobal.agentHealthFactor = None
    from datetime import datetime
    appGlobal.agentInfo = {'version': agenthealth.loadVersion(),
                           'startup': str(datetime.now())}

    appGlobal.osInfo = agenthealth.getOsInfo()
    appGlobal.diskOk = True
    LOG.info("Agent health initialized")

    # start thread mgr
    appGlobal.threadMgr = ThreadMgr(garbageFreq = pylons.config['threadMgr_garbage_freq'],
                                    maxThreadAge = pylons.config['threadMgr_thread_age'])
    if startThreadMgr:
        appGlobal.threadMgr.start()
    LOG.info("Agent thread manager started")

    # start package mgr
    appGlobal.packageMgr = PackageMgr(garbageFreq = pylons.config['packageMgr_garbage_freq'],
                                      maxPackageAge = pylons.config['packageMgr_package_age'])
    if startPackageMgr:
        appGlobal.packageMgr.start()
    LOG.info("Agent package manager started")

    #start monitor manager
    from agent.lib.monitors.monitor import AgentMonitor
    appGlobal.agentMonitor = AgentMonitor()
    if startAgentMonitor:
        appGlobal.agentMonitor.start()
    LOG.info("Agent monitor started")
    
    # Declare dictionary for storing dynamic controllers
    appGlobal.dynacontrollers = dict()

    # metrix manager initialization
    from agent.lib.monitors.metrix_manager import MetrixManager
    from agent.lib.monitors.system_monitor import SystemMonitor
    appGlobal.metrixManager = MetrixManager()
    appGlobal.systemMonitor = SystemMonitor()

    appGlobal.metrixManager.register('Configuration', validate_internals.getConfigFileFiltered, 6)
    appGlobal.metrixManager.register('Configuration Overrides', configutil.getConfigOverrides, 7)
    appGlobal.metrixManager.register(AGENT_HEALTH_VI_KEY, lambda : appGlobal.agentHealth, 1)
    appGlobal.metrixManager.register(AGENT_HEALTH_FACTOR_VI_KEY, lambda : appGlobal.agentHealthFactor, 1)
    appGlobal.metrixManager.register(OS_INFO_KEY, lambda : appGlobal.osInfo, 3)
    appGlobal.metrixManager.register(AGENT_INFO_KEY, lambda : appGlobal.agentInfo, 2)
    LOG.info("Agent health metrics registered")
    
    # start all agent modules
    modulestartthread = threading.Thread(target = ModuleController.loadModuleOnAgentStartup)
    modulestartthread.start()
    LOG.info("Local modules started")

    # start all services with active manifest, and load dynamic controllers
    servicestartthread = threading.Thread(target = ServiceController.startServicesOnAgentStartup)
    servicestartthread.start()
    LOG.info("Local services started")

    appGlobal.sdutil = shutdownAgent

def stopAgentGlobals():
    """
    stop the global objects
    """
    appGlobal = pylons.config['pylons.app_globals']

    if (hasattr(appGlobal, 'threadMgr') and appGlobal.threadMgr != None):
        appGlobal.threadMgr.stop()
    if (hasattr(appGlobal, 'packageMgr') and appGlobal.packageMgr != None):
        appGlobal.packageMgr.stop()
    if (hasattr(appGlobal, 'agentMonitor') and appGlobal.agentMonitor != None):
        appGlobal.agentMonitor.stop()
    if (hasattr(appGlobal, 'seederMgr') and appGlobal.seederMgr != None):
        appGlobal.seederMgr.stop()
    if (hasattr(appGlobal, 'graphited') and appGlobal.graphited != None):
        appGlobal.graphited.stop()

def shutdownAgent():
    ''' shutdown agent '''
    stopAgentGlobals()
    pid = os.getpid()
    if (hasattr(signal, 'SIGKILL')):
        os.kill(pid, signal.SIGKILL)
    else:
        os.kill(pid, signal.SIGTERM)

def dummy():
    """ return a dummy value for unsupported function """
    return 0
