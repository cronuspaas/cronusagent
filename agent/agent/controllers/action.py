#pylint: disable=W0703,E1101,R0904,R0914,W0105
""" service actions """
from pylons import request, response, config
import logging
import json
import traceback
import os

from agent.lib.base import BaseController
from agent.lib.errors import Errors, AgentException
from agent.lib.result import errorResult, doneResult
from agent.lib.result import statusResult
from agent.lib.utils import trackable
from agent.lib import manifestutil, serviceutil
from agent.lib.agent_thread.startstop_service import StartStopService
from agent.lib.security.agentauth import authorize
from agent.lib.agent_thread.deploy_service import DeployService
from agent.lib.agent_thread.useraction_service import UserActionService
from agent.lib.agent_thread.activate_manifest import ActivateManifest
from agent.lib.agent_thread.cleanup_service import CleanupService
from agent.lib.package import PackageUtil

LOG = logging.getLogger(__name__)

class ActionController(BaseController):
    """ Action Controller class.  Responsible for all actions of a service/agent """

    @authorize()
    @trackable()
    def rollbackservice(self, service):
        """ rollback an existing service """
        LOG.info('rollback to last active manifest for service(%s) ', service)
        manifest = None
        try:
            appGlobal = config['pylons.app_globals']
            manifest = serviceutil.getPastManifest(service, 1)
            
            if manifest:
                activateThread = ActivateManifest(appGlobal.threadMgr, service, manifest,
                                                  action=ActivateManifest.ACTION_ACTIVATION)
                self.injectJobCtx(activateThread)
                activateThread.start()
                activateThread.threadMgrEvent.wait()
            else:
                raise AgentException(Errors.MANIFEST_NOT_FOUND, "No rollback manifest found")

            return statusResult(request, response, activateThread, controller=self)

        except AgentException as excep:
            return errorResult(request, response, error=excep.getCode(), errorMsg=excep.getMsg(), controller=self)

        except Exception as excep:
            msg = 'Unknown error for rollback service(%s) - %s - %s' % (service, str(excep), traceback.format_exc(2))
            return errorResult(request, response, error=Errors.UNKNOWN_ERROR,
                               errorMsg=msg, controller=self)

    @authorize()
    @trackable()
    def cleanupservice(self, service):
        """ cleanup an existing service """
        LOG.info('cleanup service for service(%s) ', service)
        manifest = None
        try:
            appGlobal = config['pylons.app_globals']

            # cleanup
            cleanupServiceThread = CleanupService(appGlobal.threadMgr, service)
            self.injectJobCtx(cleanupServiceThread)
            cleanupServiceThread.start()
            cleanupServiceThread.threadMgrEvent.wait()

            return statusResult(request, response, cleanupServiceThread, controller = self)

        except Exception as excep:
            msg = 'Unknown error for deployService(%s/%s) - %s - %s' % (service, manifest, str(excep), traceback.format_exc(2))
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = msg, controller = self)


    @authorize()
    @trackable()
    def deployservice(self, service):
        """ activate manifest, if already active then skip """
        LOG.info('deploy service for service(%s) with body: %s', service, request.body)
        manifest = None
        try:
            appGlobal = config['pylons.app_globals']

            # parse the body
            if (request.body == ""):
                return errorResult(request, response, Errors.INVALID_REQUEST,
                                   'No body found in post command',
                                   controller = self)

            requestjson = json.loads(request.body)
            packages = requestjson['package']
            if 'manifest' in requestjson:
                manifest = requestjson['manifest']
            else:
                manifest = PackageUtil.getPackageVersion(packages[-1])
            
            serviceutil.createServiceIfNeeded(service)
                        
            # activate manifest if not already activated
            if manifestutil.getActiveManifest(service) == manifest:
                return doneResult(request, response, controller=self)
            else:
                # save metadata from payload
                pushedData = {}
                pushedData.update(requestjson)
                for key in ['manifest', 'package']:
                    if key in pushedData:
                        del pushedData[key]
                serviceutil.updateLcmMeta(service, pushedData)
                
                # deploy
                deployServiceThread = DeployService(appGlobal.threadMgr, service, manifest, packages)
                self.injectJobCtx(deployServiceThread)
                deployServiceThread.start()
                deployServiceThread.threadMgrEvent.wait()

                return statusResult(request, response, deployServiceThread, controller = self)

        except Exception as excep:
            msg = 'Unknown error for deployService(%s/%s) - %s - %s' % (service, manifest, str(excep), traceback.format_exc(2))
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = msg, controller = self)


    @authorize()
    @trackable()
    def restart(self, service):
        ''' Controller to restart service '''
        LOG.info('restart for service(%s)', service)

        try:
            appGlobal = config['pylons.app_globals']

            if not os.path.exists(manifestutil.manifestPath(service, 'active')):
                return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Active Manifest(%s) path missing' % (service),
                                   controller = self)
            restartThread = StartStopService(appGlobal.threadMgr, service, StartStopService.ACTION_RESTART)
            self.injectJobCtx(restartThread)
            restartThread.start()
            restartThread.threadMgrEvent.wait()

            return statusResult(request, response, restartThread, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for restart service(%s) - %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def reset(self, service):
        ''' Controller to reset service '''
        LOG.info('reset for service(%s)', service)

        try:
            appGlobal = config['pylons.app_globals']

            if not os.path.exists(manifestutil.manifestPath(service, 'active')):
                return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Active Manifest(%s) path missing' % (service),
                                   controller = self)
            resetThread = ActivateManifest(appGlobal.threadMgr, service, 
                                           manifestutil.ACTIVE_MANIFEST,
                                           action = ActivateManifest.ACTION_RESET)
            self.injectJobCtx(resetThread)
            resetThread.start()
            resetThread.threadMgrEvent.wait()

            return statusResult(request, response, resetThread, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for restart service(%s) - %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def startup(self, service):
        ''' Controller to startup service '''
        LOG.info('startup for service(%s)', service)

        try:
            appGlobal = config['pylons.app_globals']

            if not os.path.exists(manifestutil.manifestPath(service, 'active')):
                return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Active Manifest(%s) path missing' % (service),
                                   controller = self)
            startupThread = StartStopService(appGlobal.threadMgr, service, StartStopService.ACTION_STARTUP)
            self.injectJobCtx(startupThread)
            startupThread.start()
            startupThread.threadMgrEvent.wait()

            return statusResult(request, response, startupThread, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for start service(%s) - %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def useraction(self, service, useraction):
        ''' Controller to run lcm action on service '''
        LOG.info('%s for service(%s)', useraction, service)

        try:
            appGlobal = config['pylons.app_globals']

            if not os.path.exists(manifestutil.manifestPath(service, 'active')):
                return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Active Manifest(%s) path missing' % (service),
                                   controller = self)
            userActionThread = UserActionService(appGlobal.threadMgr, service, useraction)
            self.injectJobCtx(userActionThread)
            userActionThread.start()
            userActionThread.threadMgrEvent.wait()

            return statusResult(request, response, userActionThread, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for start service(%s) - %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def shutdown(self, service):
        ''' Controller to shutdown service '''
        LOG.info('shutdown for service(%s)', service)

        try:
            appGlobal = config['pylons.app_globals']

            if not os.path.exists(manifestutil.manifestPath(service, 'active')):
                return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Active Manifest(%s) path missing' % (service),
                                   controller = self)
            shutdownThread = StartStopService(appGlobal.threadMgr, service, StartStopService.ACTION_SHUTDOWN)
            self.injectJobCtx(shutdownThread)
            shutdownThread.start()
            shutdownThread.threadMgrEvent.wait()

            return statusResult(request, response, shutdownThread, controller = self)

        except Exception as excep:
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = 'Unknown error for shutdown service(%s) - %s - %s' %
                               (service, str(excep), traceback.format_exc(2)),
                               controller = self)

    @authorize()
    @trackable()
    def deactivatemanifest(self, service):
        """ deactivate a manifest """
        LOG.info('activateManifest for service(%s) with body: %s', service, request.body)
        try:
            appGlobal = config['pylons.app_globals']
            if not os.path.exists(manifestutil.manifestPath(service, 'active')):
                return errorResult(request, response, Errors.ACTIVEMANIFEST_MANIFEST_MISSING,
                                   'Deactivate Manifest(%s) path missing' % (service),
                                   controller = self)

            deactivateThread = ActivateManifest(appGlobal.threadMgr, service,
                                                manifestutil.ACTIVE_MANIFEST,
                                                action=ActivateManifest.ACTION_DEACTIVATION)
            self.injectJobCtx(deactivateThread)
            deactivateThread.start()
            deactivateThread.threadMgrEvent.wait()

            return statusResult(request, response, deactivateThread, controller = self)

        except Exception as excep:
            msg = 'Unknown error for deactivateManifest(%s) - %s - %s' % (service, str(excep), traceback.format_exc(2))
            return errorResult(request, response, error = Errors.UNKNOWN_ERROR,
                               errorMsg = msg, controller = self)


    @trackable()
    def sendMetrics(self, service="agent", resSec="60", monitorgroup="default"):
        ''' send data to external monitoring system EVPS '''
        appGlobal = config['pylons.app_globals']
    
        if request.body:
            collectdTextResult = request.body
            outputMapArray = json.loads(collectdTextResult)
            appGlobal.agentMonitor.runExtMonitor(service, 'http', resSec, outputMapArray, monitorgroup)
        
        return
