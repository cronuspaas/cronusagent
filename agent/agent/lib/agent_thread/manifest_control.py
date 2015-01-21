#pylint: disable=W0703,E0102,E1101,R0912,R0904,W0223,W0105,R0914
""" base thread for manifest related work """
import pylons
import os
import time

from agent.lib.agent_thread.agent_thread import AgentThread
from agent.lib.agent_thread.exec_thread import ExecThread
from agent.lib.utils import isHigherPrivilegeService, calcProgress
import logging
from agent.lib import manifestutil, utils, contextutils, configutil, serviceutil
from agent.lib.manifestutil import PkgInitConfig, ACTIVE_MANIFEST, \
    packagesInManifest, packagePath

LOG = logging.getLogger(__name__)

class ManifestControl(AgentThread):
    """ This thread will attempt to activate a manifest
    This means going throuh each package
    call the stop
    call the deactivate
    delete the active link
    call the activate
    create the active link
    call start
    """

    REC_MAP = {"activate": "deactivate", "startup": "shutdown"}
    PKG_REVERSED_SET = ['shutdown', 'deactivate']

    def __init__(self, threadMgr, service, manifest, name = 'agent_thread', parentId = None):
        """ Constructor """
        AgentThread.__init__(self, threadMgr, cat = [manifestutil.serviceCat(service)], name = name, parentId = parentId)
        self.__manifest = manifest
        self.__service = service
        contextutils.injectcontext(self, {'service':service})
        self._LOG = manifestutil.getServiceLogger(self, logging.getLogger(__name__))

    @property
    def _manifest(self):
        """ manifest property """
        return self.__manifest

    @_manifest.setter
    def _manifest(self, value):
        """ manifest property """
        self.__manifest = value

    @property
    def _service(self):
        """ service property """
        return self.__service

    @_service.setter
    def _service(self, value):
        """ service property """
        self.__service = value

    def _skipCleanupOnFailure(self):
        """ skip cleanup on app lifecycle failure
        """
        return configutil.getConfigAsBool('skip_cleanup_on_failure')

    def _obtainCmdExecThreads(self, exeName, service, manifest):
        """start the threads to execute cmd in each package in the service/manifest"""

        execThreads = []
        packages = packagesInManifest(service, os.path.basename(manifest))
        
        # Executing the deactivate in reversed order where the last package is first deactivated.
        if (exeName in ManifestControl.PKG_REVERSED_SET):
            packages.reverse()

        # make sure there's something to do, otherwise just return here
        if (len(packages) == 0):
            return execThreads
        
        for package in packages:

            execThread = self._getBuiltThread(service, manifest, package, exeName)
            if execThread:
                execThreads.append(execThread)
                
        return execThreads
    

    def _getBuiltThread(self, service, manifest, package, exeName):
        """ here """
        # figure out the path to the cronus scripts
        uname = configutil.getAppUser()
        execPath = os.path.join(manifestutil.manifestPath(service, manifest), package, 'cronus', 'scripts', exeName)
        if (isHigherPrivilegeService(service)) or not uname:
            cmd = execPath
        else:
            cmd = utils.sudoCmd([execPath], uname)

        dummy = not os.path.exists(execPath)
        if not dummy:
            execThread = ExecThread(self._threadMgr, cmd, parentId = self.getUuid())
            contextutils.copyJobContexts(self, execThread)
            
            # issue 17, not inject ctx for startup and shutdown script
            if exeName == 'startup' or exeName == 'shutdown':
                execThread.setInjectctx(False)
                
            return execThread
        else:
            return None

    def _execPackages(self, exeName, service, manifest, minProgress, maxProgress):
        """ execPackages.  Execute the executible for all packages under the service/manifest.
        calculate and update progress.  This will not return until all executibles have finished with status 0.
        If one executible fails, this function will thow an exception.

        @param exeName - name of the executible
        @param service - service of manifest
        @param manifest - manifest
        @param minProgress - minimum progress for executing these packages
        @param maxProgress - maximum progress for executing these packages
        @param activateFlow (default true) - whether part of activation flow (False means it is de-active).  This affects the order of execution
        @throws AgentException - will throw an exception if an error occurred
        """
        execThreads = self._obtainCmdExecThreads(exeName, service, manifest)
        self._runExecThreads(execThreads, minProgress, maxProgress)

    def _runExecThreads(self, execThreads, minProgress, maxProgress):
        """ run exec threads """
        if (len(execThreads) == 0):
            self._updateProgress(maxProgress)
            return
        
        # start with min progress
        self._updateProgress(minProgress)

        # now wait for the threads to complete and update progress
        while (True):
            self._checkStop()

            progress = 0
            running = False

            for execThread in execThreads:
                
                self.extendTimeout(execThread.getTimeout())
                status = AgentThread._runExeThread(self, execThread)

                progress += status['progress']

            if (not running):
                break

            # update the progress
            percent = progress / len(execThreads)

            self._updateProgress(calcProgress(minProgress, maxProgress, float(percent) / 100))

            time.sleep(float(pylons.config['exec_thread_sleep_time']))

        self._updateProgress(maxProgress)

    def _shutdownManifest(self, service, manifest, minProg, maxProg):
        """ shutdown a manifest.  This means calling shutdown script on manifest packages
        @param service - service of manifest to deactivate
        """
        self._LOG.info("Shutdown active Manifest %s" % (service))
        hasDaemon = serviceutil.isDaemonServiceWiri(service)[0]
        if hasDaemon:
            self.__stopServiceDaemon(minProg)
        else:
            self._execPackages('shutdown', service, manifest, minProg, maxProg)
            
    def _startupManifest(self, service, manifest, minProg, maxProg):
        """ startup a manifest.  This means calling startup script on manifest packages
        @param service - service of manifest to activate
        """
        self._LOG.info("Startup active Manifest %s" % (service))
        incProg = (maxProg-minProg)/2
        if serviceutil.isDaemonServiceWiri(service)[0]:
            self.__startupServiceDaemon(minProg)
        else:    
            self._execPackages('startup', service, manifest, minProg, minProg+incProg)
        
        # if app has ready script to check for readiness, run it
        self._execPackages('ready', service, manifest, minProg+incProg, maxProg)

    def _restartManifest(self, service, manifest, minProg, maxProg):
        """ startup a manifest.  This means calling startup script on manifest packages
        @param service - service of manifest to activate
        """
        self._LOG.info("Startup active Manifest %s" % (service))
        incProg = (maxProg - minProg) / 2
        self._shutdownManifest(service, manifest, minProg, minProg+incProg)
        self._startupManifest(service, manifest, minProg+incProg, maxProg)

    def _deactivateManifest(self, service, manifest, minProg, maxProg):
        """ deactive a manifest.  This means calling stop then deactive on the manifest
        @param service - service of manifest to deactivate
        @param manifest - manifest to deactivate
        @param stack - stack for recovery
        """
        self._LOG.debug("Deactivate Manifest %s-%s" % (service, manifest))
        if (manifest == None):
            return
        
        incProg = (maxProg-minProg)/3
        self._shutdownManifest(service, manifest, minProg, minProg+incProg)
        self.__preDeactivation(service, manifest, minProg+incProg)
        self._execPackages('deactivate', service, manifest, maxProg-incProg, maxProg)

    def _activateManifest(self, service, manifest, minProg, maxProg):
        """ deactive a manifest.  This means calling stop then deactive on the manifest
        @param service - service of manifest to activate
        @param manifest - manifest to activate
        @param stack - stack for recovery
        """
        self._LOG.debug("Activate Manifest %s-%s" % (service, manifest))
        if (manifest == None):
            return

        incProg = (maxProg-minProg)/3
        self._execPackages('activate', service, manifest, minProg, minProg+incProg)
        self.__postActivation(service, manifest, minProg+incProg)
        self._startupManifest(service, manifest, maxProg-incProg, maxProg)
        serviceutil.addActivatedManifestList(service, manifest)

    def __postActivation(self, service, manifest, curProg):
        """ place to run post activation operations
            1. customize application configuration files based on metadata
            2. install upstart service
        """
        
        # replace application config files based on lcm_meta.env, "env" valeu set in post request
        for package in packagesInManifest(service, manifest):
            self._LOG.info('check map config files in %s' % (package))
            pkgRoot = packagePath(service, ACTIVE_MANIFEST, package)
            pkgCfg = PkgInitConfig(pkgRoot)
            
            # read cfgfilemap from cronus.ini
            env = serviceutil.getEnv(service)
            if env:
                cfgFiles = pkgCfg.getConfig(PkgInitConfig.KEY_CFGFILES, [])
                for cfgFile in cfgFiles:
                    srcFile = os.path.join(pkgRoot, '%s.%s' % (cfgFile, env.lower()))
                    destFile = os.path.join(pkgRoot, cfgFile)
                    if os.path.exists(srcFile):
                        self._LOG.info('copy cfg file %s to %s' % (srcFile, destFile))
                        cmd = utils.sudoCmd(['cp', '-f', srcFile, destFile], configutil.getAppUser())
                        execThread = ExecThread(self._threadMgr, cmd, None, self.getUuid())
                        self._runExecThreads([execThread], curProg, curProg+1)


        # install daemon based on metadata.lcm_meta.daemon
        isDaemon, daemonType = serviceutil.isDaemonServiceWisb(service)  
        if isDaemon:
            installed = False
            self._LOG.info('daemon enabled, setup service in %s' % daemonType)
            
            for package in packagesInManifest(service, manifest):
                pkgRoot = packagePath(service, ACTIVE_MANIFEST, package)
                appUser = configutil.getAppUser()
                if (os.path.exists(os.path.join(pkgRoot, 'cronus', 'upstart.conf')) or 
                    os.path.exists(os.path.join(pkgRoot, 'cronus', 'systemd.service'))):
                    self._LOG.info('found daemon config in %s' % (package))
                    script = manifestutil.getActiveScriptPath('agent', 'agent', 'setupserviced')
                    cmd = utils.sudoCmd([script, pkgRoot, appUser, service, daemonType])
                    execThread = ExecThread(self._threadMgr, cmd, None, self.getUuid())
                    self._runExecThreads([execThread], curProg+1, curProg+2)
                    installed = True
                    break

            if not installed:
                self._LOG.info('daemon config not found, service not installed')
                serviceutil.setDaemonServiceWisb(service, None)
        

    def __preDeactivation(self, service, manifest, curProg):
        """ additional operations post deactivation script
            1. uninstall upstart config
        """
        isDaemon, daemonType = serviceutil.isDaemonServiceWisb(service)        
        if isDaemon:
            self._LOG.info('daemon enabled, teardown service in %s' % daemonType)
            
            script = manifestutil.getActiveScriptPath('agent', 'agent', 'teardownserviced')
            teardownCmd = utils.sudoCmd([script, service])
            teardownThread = ExecThread(self._threadMgr, teardownCmd, None, self.getUuid())
            self._runExecThreads([teardownThread], curProg, curProg+1)
            self._LOG.info('uninstalled upstart service %s' % (daemonType))
            
    def __startupServiceDaemon(self, curProg):
        """ start upstart service
        """
        script = manifestutil.getActiveScriptPath('agent', 'agent', 'startupserviced')
        startupCmd = utils.sudoCmd([script, self.__service])
        teardownThread = ExecThread(self._threadMgr, startupCmd, None, self.getUuid())
        self._runExecThreads([teardownThread], curProg, curProg+1)
        self._LOG.info('start daemon service %s' % (self.__service))
       
        
    def __stopServiceDaemon(self, curProg):
        """ stop upstart service 
        """
        script = manifestutil.getActiveScriptPath('agent', 'agent', 'shutdownserviced')
        startupCmd = utils.sudoCmd([script, self.__service])
        teardownThread = ExecThread(self._threadMgr, startupCmd, None, self.getUuid())
        self._runExecThreads([teardownThread], curProg, curProg+1)
        self._LOG.info('stop daemon service %s' % (self.__service))

